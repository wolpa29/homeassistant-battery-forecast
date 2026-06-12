"""Config flow for Battery SoC Forecast integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

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
    CONF_UPDATE_INTERVAL,
    CONF_USE_ADVANCED_MODE,
    DEFAULT_BATTERY_MAX_KWH,
    DEFAULT_MAX_FORECAST_H,
    DEFAULT_MAX_SOC,
    DEFAULT_MIN_SOC,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_USE_ADVANCED_MODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class BatterySoCForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery SoC Forecast."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                return self.async_create_entry(
                    title="Battery SoC Forecast",
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.error("Error creating config entry: %s", e)
                errors["base"] = "unknown"
        else:
            user_input = {}

        schema = vol.Schema({
            vol.Required(
                CONF_BATTERY_SOC_ENTITY,
                default=user_input.get(CONF_BATTERY_SOC_ENTITY, ""),
            ): str,
            vol.Required(
                CONF_DISCHARGE_W_ENTITY,
                default=user_input.get(CONF_DISCHARGE_W_ENTITY, ""),
            ): str,
            vol.Required(
                CONF_CHARGE_W_ENTITY,
                default=user_input.get(CONF_CHARGE_W_ENTITY, ""),
            ): str,
            vol.Required(
                CONF_BATTERY_MAX_KWH,
                default=user_input.get(CONF_BATTERY_MAX_KWH, DEFAULT_BATTERY_MAX_KWH),
            ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=1000.0)),
            vol.Required(
                CONF_MIN_SOC,
                default=user_input.get(CONF_MIN_SOC, DEFAULT_MIN_SOC),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Required(
                CONF_MAX_SOC,
                default=user_input.get(CONF_MAX_SOC, DEFAULT_MAX_SOC),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Required(
                CONF_MAX_FORECAST_H,
                default=user_input.get(CONF_MAX_FORECAST_H, DEFAULT_MAX_FORECAST_H),
            ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=168.0)),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            vol.Required(
                CONF_USE_ADVANCED_MODE,
                default=user_input.get(CONF_USE_ADVANCED_MODE, DEFAULT_USE_ADVANCED_MODE),
            ): bool,
            vol.Optional(
                CONF_PV_FORECAST_ENTITY,
                default=user_input.get(CONF_PV_FORECAST_ENTITY, ""),
            ): str,
            vol.Optional(
                CONF_LOAD_ENTITY,
                default=user_input.get(CONF_LOAD_ENTITY, ""),
            ): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the init step."""
        return await self.async_step_user(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            try:
                return self.async_update_reload_abort(
                    entry=config_entry,
                    data_updates=user_input,
                )
            except Exception as e:
                _LOGGER.error("Error updating config entry: %s", e)
                errors["base"] = "unknown"
        else:
            user_input = {
                CONF_BATTERY_SOC_ENTITY: config_entry.data.get(CONF_BATTERY_SOC_ENTITY, ""),
                CONF_DISCHARGE_W_ENTITY: config_entry.data.get(CONF_DISCHARGE_W_ENTITY, ""),
                CONF_CHARGE_W_ENTITY: config_entry.data.get(CONF_CHARGE_W_ENTITY, ""),
                CONF_BATTERY_MAX_KWH: config_entry.data.get(CONF_BATTERY_MAX_KWH, DEFAULT_BATTERY_MAX_KWH),
                CONF_MIN_SOC: config_entry.data.get(CONF_MIN_SOC, DEFAULT_MIN_SOC),
                CONF_MAX_SOC: config_entry.data.get(CONF_MAX_SOC, DEFAULT_MAX_SOC),
                CONF_MAX_FORECAST_H: config_entry.data.get(CONF_MAX_FORECAST_H, DEFAULT_MAX_FORECAST_H),
                CONF_UPDATE_INTERVAL: config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                CONF_USE_ADVANCED_MODE: config_entry.data.get(CONF_USE_ADVANCED_MODE, DEFAULT_USE_ADVANCED_MODE),
                CONF_PV_FORECAST_ENTITY: config_entry.data.get(CONF_PV_FORECAST_ENTITY, ""),
                CONF_LOAD_ENTITY: config_entry.data.get(CONF_LOAD_ENTITY, ""),
            }

        schema = vol.Schema({
            vol.Required(
                CONF_BATTERY_SOC_ENTITY,
                default=user_input.get(CONF_BATTERY_SOC_ENTITY, ""),
            ): str,
            vol.Required(
                CONF_DISCHARGE_W_ENTITY,
                default=user_input.get(CONF_DISCHARGE_W_ENTITY, ""),
            ): str,
            vol.Required(
                CONF_CHARGE_W_ENTITY,
                default=user_input.get(CONF_CHARGE_W_ENTITY, ""),
            ): str,
            vol.Required(
                CONF_BATTERY_MAX_KWH,
                default=user_input.get(CONF_BATTERY_MAX_KWH, DEFAULT_BATTERY_MAX_KWH),
            ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=1000.0)),
            vol.Required(
                CONF_MIN_SOC,
                default=user_input.get(CONF_MIN_SOC, DEFAULT_MIN_SOC),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Required(
                CONF_MAX_SOC,
                default=user_input.get(CONF_MAX_SOC, DEFAULT_MAX_SOC),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
            vol.Required(
                CONF_MAX_FORECAST_H,
                default=user_input.get(CONF_MAX_FORECAST_H, DEFAULT_MAX_FORECAST_H),
            ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=168.0)),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            vol.Required(
                CONF_USE_ADVANCED_MODE,
                default=user_input.get(CONF_USE_ADVANCED_MODE, DEFAULT_USE_ADVANCED_MODE),
            ): bool,
            vol.Optional(
                CONF_PV_FORECAST_ENTITY,
                default=user_input.get(CONF_PV_FORECAST_ENTITY, ""),
            ): str,
            vol.Optional(
                CONF_LOAD_ENTITY,
                default=user_input.get(CONF_LOAD_ENTITY, ""),
            ): str,
        })

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
