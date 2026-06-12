"""Constants for Battery SoC Forecast integration."""

from __future__ import annotations

DOMAIN = "battery_soc_forecast"
PLATFORMS = ["sensor"]

# Config entry keys
CONF_BATTERY_SOC_ENTITY = "battery_soc_entity"
CONF_DISCHARGE_W_ENTITY = "discharge_w_entity"
CONF_CHARGE_W_ENTITY = "charge_w_entity"
CONF_LOAD_ENTITY = "load_entity"
CONF_PV_FORECAST_ENTITY = "pv_forecast_entity"
CONF_BATTERY_MAX_KWH = "battery_max_kwh"
CONF_MIN_SOC = "min_soc"
CONF_MAX_SOC = "max_soc"
CONF_MAX_FORECAST_H = "max_forecast_h"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_USE_ADVANCED_MODE = "use_advanced_mode"

# Default values
DEFAULT_BATTERY_MAX_KWH = 22.0
DEFAULT_MIN_SOC = 10.0
DEFAULT_MAX_SOC = 100.0
DEFAULT_MAX_FORECAST_H = 24.0
DEFAULT_UPDATE_INTERVAL = 300
DEFAULT_USE_ADVANCED_MODE = False
