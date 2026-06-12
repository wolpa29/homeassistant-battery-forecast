import datetime

BATTERY_SOC_PERCENT = "sensor.sn_3015651602_battery_soc_total"
DISCHARGE_W = "sensor.sn_3015651602_battery_power_discharge_total"
CHARGE_W = "sensor.sn_3015651602_battery_power_charge_total"
TARGET_ENTITY = "sensor.battery_linear_forecast"

# Optional: Entitäten für PV-Forecast und Hausverbrauch eintragen.
# Wenn du sie deaktivieren willst, einfach auf None oder "" setzen.
PV_FORECAST_ENTITY = "sensor.pv_forecast_planner_safe_forecast_power"
LOAD_ENTITY = "sensor.sn_3015651602_grid_power"

BATTERY_MAX_KWH = 22.0
MIN_SOC = 10.0  # Minimum SoC in percent
MAX_SOC = 100.0
MAX_FORECAST_H = 24.0

@time_trigger("startup", "cron(*/5 * * * *)")
def update_battery_forecast():
    try:
        battery_soc_percent = float(state.get(BATTERY_SOC_PERCENT))
        discharge_w = float(state.get(DISCHARGE_W))
        charge_w = float(state.get(CHARGE_W))
    except (TypeError, ValueError):
        log.warning("Canceled forecast: no sensor data")
        return

    now = datetime.datetime.now()

    # WICHTIG: Nur abbrechen, wenn die Batterie leer ist UND nicht geladen wird!
    if battery_soc_percent <= MIN_SOC and charge_w <= 0:
        iso_now = now.strftime("%Y-%m-%dT%H:%M:%S")
        forecast_data = [[iso_now, round(battery_soc_percent, 1)]]
        state.set(
            TARGET_ENTITY, 
            value=round(battery_soc_percent, 1),
            new_attributes={
                "unit_of_measurement": "%",
                "device_class": "battery",
                "state_class": "measurement",
                "friendly_name": "Battery SoC Forecast",
                "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "interval_minutes": 15,
                "forecast": forecast_data,
                "empty_at": now.strftime("%H:%M"),
                "full_at": "N/A",
                "remaining_time": 0.0,
                "min_soc_limit": MIN_SOC,
                "max_soc_limit": MAX_SOC,
                "mode": "Empty"
            }
        )
        return

    usable_soc_percent = battery_soc_percent - MIN_SOC
    left_soc_percent = MAX_SOC - battery_soc_percent
    usable_kwh = (usable_soc_percent / 100.0) * BATTERY_MAX_KWH
    left_kwh = (left_soc_percent / 100.0) * BATTERY_MAX_KWH

    if discharge_w < 0 or charge_w < 0:
        log.warning("Canceled forecast: charge or discharge cannot be negative")
        return

    if discharge_w > 0 and charge_w > 0:
        log.warning("Canceled forecast: charge and discharge > 0 at the same time")
        return

    # 1. PV Forecast und Load prüfen (Optionaler Advanced Mode)
    use_pv_forecast = False
    pv_forecast_data = []
    current_load_w = 0.0
    
    if PV_FORECAST_ENTITY and LOAD_ENTITY:
        try:
            current_load_w = float(state.get(LOAD_ENTITY))
            # Lade Attribute aus Home Assistant, um die Forecast-Liste auszulesen
            attrs = state.getattr(PV_FORECAST_ENTITY)
            if attrs and "forecast" in attrs:
                pv_forecast_data = attrs["forecast"]
                if len(pv_forecast_data) > 0:
                    use_pv_forecast = True
        except Exception as e:
            log.warning(f"Could not load PV forecast or load data: {e}. Falling back to linear mode.")
            use_pv_forecast = False

    iso_now = now.strftime("%Y-%m-%dT%H:%M:%S")
    forecast_data = []
    
    minutes_to_next_slot = 15 - (now.minute % 15)
    next_slot = now + datetime.timedelta(minutes=minutes_to_next_slot)
    next_slot = next_slot.replace(second=0, microsecond=0)

    forecast_data.append([iso_now, round(battery_soc_percent, 1)])
    total_start_kwh = (battery_soc_percent / 100.0) * BATTERY_MAX_KWH
    
    time_empty = "N/A"
    time_full = "N/A"
    remaining_time_h = 0.0

    if use_pv_forecast:
        # --- ERWEITERTER MODUS (PV + aktueller Hausverbrauch) ---
        current_kwh = total_start_kwh
        future_pv = []
        
        # Datums-Parsing Helper
        def parse_iso(t_str):
            try:
                return datetime.datetime.fromisoformat(t_str)
            except:
                return datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S")
                
        # Zukünftige PV-Werte parsen
        for item in pv_forecast_data:
            dt = parse_iso(item[0])
            if dt > now:
                future_pv.append((dt, float(item[1])))
                
        future_pv.sort(key=lambda x: x[0])
        
        if not future_pv:
            use_pv_forecast = False # Fallback, falls alle Forecast-Daten in der Vergangenheit liegen
        else:
            sim_time = next_slot
            simulation_end_time = now + datetime.timedelta(hours=MAX_FORECAST_H)
            
            # Simulation im 15-Minuten Raster
            while sim_time <= simulation_end_time:
                # PV-Power für den aktuellen Zeit-Slot finden
                pv_power_w = 0.0
                for i in range(len(future_pv)):
                    if future_pv[i][0] <= sim_time:
                        pv_power_w = future_pv[i][1]
                    else:
                        break
                        
                # Netto-Leistung = PV-Erzeugung minus Verbrauch
                # Positiv -> Laden / Negativ -> Entladen
                net_power_w = pv_power_w - current_load_w
                
                # Zeit seit letztem Schritt berechnen
                if len(forecast_data) == 1:
                    time_delta_h = (sim_time - now).total_seconds() / 3600.0
                else:
                    time_delta_h = 0.25 # Exakt 15 Minuten in Stunden
                    
                energy_change_kwh = (net_power_w / 1000.0) * time_delta_h
                current_kwh += energy_change_kwh
                
                # Begrenzen auf MIN und MAX Limits
                max_kwh_allowed = BATTERY_MAX_KWH * (MAX_SOC / 100.0)
                min_kwh_allowed = BATTERY_MAX_KWH * (MIN_SOC / 100.0)
                
                if current_kwh >= max_kwh_allowed:
                    if time_full == "N/A":
                        time_full = sim_time.strftime("%H:%M")
                    current_kwh = max_kwh_allowed
                    
                if current_kwh <= min_kwh_allowed:
                    if time_empty == "N/A":
                        time_empty = sim_time.strftime("%H:%M")
                    current_kwh = min_kwh_allowed
                    
                current_soc = (current_kwh / BATTERY_MAX_KWH) * 100.0
                current_soc = max(MIN_SOC, min(MAX_SOC, current_soc))
                
                iso_key = sim_time.strftime("%Y-%m-%dT%H:%M:%S")
                forecast_data.append([iso_key, round(current_soc, 1)])
                
                sim_time += datetime.timedelta(minutes=15)
                
            remaining_time_h = MAX_FORECAST_H

    if not use_pv_forecast:
        # --- FALLBACK: LINEARER MODUS (Deine ursprüngliche Logik) ---
        kw_rate = 0.0 
        end_soc = None
        linear_end_time = None
        
        if discharge_w > 0:
            kw_rate = -(discharge_w / 1000.0)
            remaining_time_h = usable_kwh / abs(kw_rate)
            linear_end_time = now + datetime.timedelta(hours=remaining_time_h)
            end_soc = MIN_SOC
            time_empty = linear_end_time.strftime("%H:%M")
        elif charge_w > 0:
            kw_rate = charge_w / 1000.0
            remaining_time_h = left_kwh / kw_rate
            linear_end_time = now + datetime.timedelta(hours=remaining_time_h)
            end_soc = MAX_SOC
            time_full = linear_end_time.strftime("%H:%M")
        else:
            kw_rate = 0.0
            remaining_time_h = float(MAX_FORECAST_H)
            linear_end_time = now + datetime.timedelta(hours=MAX_FORECAST_H)
            end_soc = battery_soc_percent

        while next_slot < linear_end_time:
            iso_key = next_slot.strftime("%Y-%m-%dT%H:%M:%S")
            time_passed_h = (next_slot - now).total_seconds() / 3600.0
            remaining_kwh = total_start_kwh + (kw_rate * time_passed_h)
            remaining_soc = (remaining_kwh / BATTERY_MAX_KWH) * 100.0
            remaining_soc = max(MIN_SOC, min(MAX_SOC, remaining_soc))

            forecast_data.append([iso_key, round(remaining_soc, 1)])
            next_slot += datetime.timedelta(minutes=15)

        iso_end = linear_end_time.strftime("%Y-%m-%dT%H:%M:%S")
        forecast_data.append([iso_end, float(end_soc)])
        
    state.set(
        TARGET_ENTITY, 
        value=round(battery_soc_percent, 1),
        new_attributes={
            "unit_of_measurement": "%",
            "device_class": "battery",
            "state_class": "measurement",
            "friendly_name": "Battery SoC Forecast",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "interval_minutes": 15,
            "empty_at": time_empty,
            "full_at": time_full,
            "remaining_time": round(remaining_time_h, 2),
            "min_soc_limit": MIN_SOC,
            "max_soc_limit": MAX_SOC,
            "forecast": forecast_data,
            "mode": "Advanced (PV + Load)" if use_pv_forecast else "Linear (Current Power)"
        }
    )