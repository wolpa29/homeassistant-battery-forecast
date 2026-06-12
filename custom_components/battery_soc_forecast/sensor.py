"""Sensor platform for Battery SoC Forecast."""

from __future__ import annotations

import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_BATTERY_MAX_KWH,
    CONF_BATTERY_SOC_ENTITY,
    CONF_CHARGE_W_ENTITY,
    CONF_DISCHARGE_W_ENTITY,
    CONF_LOAD_ENTITY,
    CONF_MAX_FORECAST_H,
    CONF_MAX_SOC,
    CONF_MIN_SOC,
    CONF_PV_FORECAST_ENTITY,
    CONF_USE_ADVANCED_MODE,
    DEFAULT_BATTERY_MAX_KWH,
    DEFAULT_MAX_FORECAST_H,
    DEFAULT_MAX_SOC,
    DEFAULT_MIN_SOC,
    DEFAULT_USE_ADVANCED_MODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Update interval: every 5 minutes
UPDATE_INTERVAL_SECONDS = 300


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the sensor via a config entry."""
    sensor = BatterySoCForecastSensor(
        name="Battery SoC Forecast",
        battery_soc_entity=entry.data.get(CONF_BATTERY_SOC_ENTITY),
        discharge_w_entity=entry.data.get(CONF_DISCHARGE_W_ENTITY),
        charge_w_entity=entry.data.get(CONF_CHARGE_W_ENTITY),
        pv_forecast_entity=entry.data.get(CONF_PV_FORECAST_ENTITY, ""),
        load_entity=entry.data.get(CONF_LOAD_ENTITY, ""),
        battery_max_kwh=entry.data.get(CONF_BATTERY_MAX_KWH, DEFAULT_BATTERY_MAX_KWH),
        min_soc=entry.data.get(CONF_MIN_SOC, DEFAULT_MIN_SOC),
        max_soc=entry.data.get(CONF_MAX_SOC, DEFAULT_MAX_SOC),
        max_forecast_h=entry.data.get(CONF_MAX_FORECAST_H, DEFAULT_MAX_FORECAST_H),
        use_advanced_mode=entry.data.get(CONF_USE_ADVANCED_MODE, DEFAULT_USE_ADVANCED_MODE),
    )
    async_add_entities([sensor])
    
    # Schedule periodic updates
    sensor._unsub_update = async_track_time_interval(
        hass, sensor.async_update_forecast, datetime.timedelta(seconds=UPDATE_INTERVAL_SECONDS)
    )
    
    # Initial update
    await sensor.async_update_forecast()


class BatterySoCForecastSensor(SensorEntity):
    """Battery SoC Forecast sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"
    _attr_should_poll = False

    def __init__(
        self,
        name: str,
        battery_soc_entity: str,
        discharge_w_entity: str,
        charge_w_entity: str,
        pv_forecast_entity: str,
        load_entity: str,
        battery_max_kwh: float,
        min_soc: float,
        max_soc: float,
        max_forecast_h: float,
        use_advanced_mode: bool,
    ) -> None:
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_unique_id = f"{battery_soc_entity}_forecast"
        self._attr_available = False

        # Config
        self._battery_soc_entity = battery_soc_entity
        self._discharge_w_entity = discharge_w_entity
        self._charge_w_entity = charge_w_entity
        self._pv_forecast_entity = pv_forecast_entity
        self._load_entity = load_entity
        self._battery_max_kwh = battery_max_kwh
        self._min_soc = min_soc
        self._max_soc = max_soc
        self._max_forecast_h = max_forecast_h
        self._use_advanced_mode = use_advanced_mode

        # State
        self._state = None
        self._forecast_data = []
        self._time_empty = "N/A"
        self._time_full = "N/A"
        self._remaining_time = 0.0
        self._mode = "Unknown"

        # Unsubscribe handler
        self._unsub_update = None

    @property
    def native_value(self) -> float | None:
        """Return the current battery SoC."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the forecast attributes."""
        now = datetime.datetime.now()
        return {
            "unit_of_measurement": "%",
            "device_class": "battery",
            "state_class": "measurement",
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "interval_minutes": UPDATE_INTERVAL_SECONDS / 60,
            "forecast": self._forecast_data,
            "empty_at": self._time_empty,
            "full_at": self._time_full,
            "remaining_time": round(self._remaining_time, 2),
            "min_soc_limit": self._min_soc,
            "max_soc_limit": self._max_soc,
            "mode": self._mode,
        }

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self._attr_available

    async def async_update_forecast(self, _now: datetime.datetime | None = None) -> None:
        """Update the forecast based on current sensor values."""
        try:
            # Read sensor values
            battery_soc_state = self.hass.states.get(self._battery_soc_entity)
            discharge_w_state = self.hass.states.get(self._discharge_w_entity)
            charge_w_state = self.hass.states.get(self._charge_w_entity)

            if any(s is None or s.state in (STATE_UNAVAILABLE, STATE_UNKNOWN) for s in (battery_soc_state, discharge_w_state, charge_w_state)):
                _LOGGER.warning("Canceled forecast: missing sensor data")
                self._attr_available = False
                self.async_write_ha_state()
                return

            battery_soc_percent = float(battery_soc_state.state)
            discharge_w = float(discharge_w_state.state)
            charge_w = float(charge_w_state.state)

        except (TypeError, ValueError, AttributeError):
            _LOGGER.warning("Canceled forecast: invalid sensor data")
            self._attr_available = False
            self.async_write_ha_state()
            return

        now = datetime.datetime.now()

        # Early exit: battery empty and not charging
        if battery_soc_percent <= self._min_soc and charge_w <= 0:
            iso_now = now.strftime("%Y-%m-%dT%H:%M:%S")
            self._forecast_data = [[iso_now, round(battery_soc_percent, 1)]]
            self._state = round(battery_soc_percent, 1)
            self._time_empty = now.strftime("%H:%M")
            self._time_full = "N/A"
            self._remaining_time = 0.0
            self._mode = "Empty"
            self._attr_available = True
            self.async_write_ha_state()
            return

        # Validate values
        if discharge_w < 0 or charge_w < 0:
            _LOGGER.warning("Canceled forecast: charge or discharge cannot be negative")
            return

        if discharge_w > 0 and charge_w > 0:
            _LOGGER.warning("Canceled forecast: charge and discharge > 0 at the same time")
            return

        # Calculate usable energy
        usable_soc_percent = battery_soc_percent - self._min_soc
        left_soc_percent = self._max_soc - battery_soc_percent
        usable_kwh = (usable_soc_percent / 100.0) * self._battery_max_kwh
        left_kwh = (left_soc_percent / 100.0) * self._battery_max_kwh

        iso_now = now.strftime("%Y-%m-%dT%H:%M:%S")
        forecast_data = []

        minutes_to_next_slot = 15 - (now.minute % 15)
        next_slot = now + datetime.timedelta(minutes=minutes_to_next_slot)
        next_slot = next_slot.replace(second=0, microsecond=0)

        forecast_data.append([iso_now, round(battery_soc_percent, 1)])
        total_start_kwh = (battery_soc_percent / 100.0) * self._battery_max_kwh

        time_empty = "N/A"
        time_full = "N/A"
        remaining_time_h = 0.0

        # Check if advanced mode is enabled and PV forecast data is available
        use_pv_forecast = False
        pv_forecast_data = []
        current_load_w = 0.0

        if self._use_advanced_mode and self._pv_forecast_entity and self._load_entity:
            try:
                load_state = self.hass.states.get(self._load_entity)
                if load_state and load_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    current_load_w = float(load_state.state)

                pv_state = self.hass.states.get(self._pv_forecast_entity)
                if pv_state and pv_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    attrs = pv_state.attributes
                    if attrs and "forecast" in attrs:
                        pv_forecast_data = attrs["forecast"]
                        if len(pv_forecast_data) > 0:
                            use_pv_forecast = True
            except Exception as e:
                _LOGGER.warning("Could not load PV forecast or load data: %s. Falling back to linear mode.", e)
                use_pv_forecast = False

        if use_pv_forecast:
            # --- ADVANCED MODE (PV + Load) ---
            self._mode = "Advanced (PV + Load)"
            current_kwh = total_start_kwh
            future_pv = []

            def parse_iso(t_str: str) -> datetime.datetime:
                try:
                    return datetime.datetime.fromisoformat(t_str)
                except ValueError:
                    return datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S")

            # Parse future PV values
            for item in pv_forecast_data:
                dt = parse_iso(item[0])
                if dt > now:
                    future_pv.append((dt, float(item[1])))

            future_pv.sort(key=lambda x: x[0])

            if not future_pv:
                use_pv_forecast = False
            else:
                sim_time = next_slot
                simulation_end_time = now + datetime.timedelta(hours=self._max_forecast_h)

                while sim_time <= simulation_end_time:
                    # Find PV power for current time slot
                    pv_power_w = 0.0
                    for i in range(len(future_pv)):
                        if future_pv[i][0] <= sim_time:
                            pv_power_w = future_pv[i][1]
                        else:
                            break

                    # Net power = PV generation - load consumption
                    net_power_w = pv_power_w - current_load_w

                    # Calculate time delta
                    if len(forecast_data) == 1:
                        time_delta_h = (sim_time - now).total_seconds() / 3600.0
                    else:
                        time_delta_h = 0.25  # 15 minutes

                    energy_change_kwh = (net_power_w / 1000.0) * time_delta_h
                    current_kwh += energy_change_kwh

                    # Clamp to min/max limits
                    max_kwh_allowed = self._battery_max_kwh * (self._max_soc / 100.0)
                    min_kwh_allowed = self._battery_max_kwh * (self._min_soc / 100.0)

                    if current_kwh >= max_kwh_allowed:
                        if time_full == "N/A":
                            time_full = sim_time.strftime("%H:%M")
                        current_kwh = max_kwh_allowed

                    if current_kwh <= min_kwh_allowed:
                        if time_empty == "N/A":
                            time_empty = sim_time.strftime("%H:%M")
                        current_kwh = min_kwh_allowed

                    current_soc = (current_kwh / self._battery_max_kwh) * 100.0
                    current_soc = max(self._min_soc, min(self._max_soc, current_soc))

                    iso_key = sim_time.strftime("%Y-%m-%dT%H:%M:%S")
                    forecast_data.append([iso_key, round(current_soc, 1)])

                    sim_time += datetime.timedelta(minutes=15)

                remaining_time_h = self._max_forecast_h

        if not use_pv_forecast:
            # --- LINEAR MODE (Current Power) ---
            self._mode = "Linear (Current Power)"
            kw_rate = 0.0
            end_soc = None
            linear_end_time = None

            if discharge_w > 0:
                kw_rate = -(discharge_w / 1000.0)
                remaining_time_h = usable_kwh / abs(kw_rate)
                linear_end_time = now + datetime.timedelta(hours=remaining_time_h)
                end_soc = self._min_soc
                time_empty = linear_end_time.strftime("%H:%M")
            elif charge_w > 0:
                kw_rate = charge_w / 1000.0
                remaining_time_h = left_kwh / kw_rate
                linear_end_time = now + datetime.timedelta(hours=remaining_time_h)
                end_soc = self._max_soc
                time_full = linear_end_time.strftime("%H:%M")
            else:
                kw_rate = 0.0
                remaining_time_h = float(self._max_forecast_h)
                linear_end_time = now + datetime.timedelta(hours=self._max_forecast_h)
                end_soc = battery_soc_percent

            while next_slot < linear_end_time:
                iso_key = next_slot.strftime("%Y-%m-%dT%H:%M:%S")
                time_passed_h = (next_slot - now).total_seconds() / 3600.0
                remaining_kwh = total_start_kwh + (kw_rate * time_passed_h)
                remaining_soc = (remaining_kwh / self._battery_max_kwh) * 100.0
                remaining_soc = max(self._min_soc, min(self._max_soc, remaining_soc))

                forecast_data.append([iso_key, round(remaining_soc, 1)])
                next_slot += datetime.timedelta(minutes=15)

            iso_end = linear_end_time.strftime("%Y-%m-%dT%H:%M:%S")
            forecast_data.append([iso_end, float(end_soc)])

        # Update sensor state
        self._state = round(battery_soc_percent, 1)
        self._forecast_data = forecast_data
        self._time_empty = time_empty
        self._time_full = time_full
        self._remaining_time = remaining_time_h
        self._attr_available = True
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Cleanup when entity is removed."""
        if self._unsub_update:
            self._unsub_update()
