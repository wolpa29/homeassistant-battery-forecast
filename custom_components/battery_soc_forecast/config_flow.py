"""Config flow for Battery SoC Forecast integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from .const import (
    CONF_BATTERY_MAX_KWH,
    CONF_BATTERY_SOC_ENTITY,
    CONF_CHARGE_W_ENTITY,
    CONF_DISCHARGE_W_ENTITY,
    CONF_LOAD_ENTITY,
    CONF_MAX_SOC,
    CONF_MIN_SOC,
    CONF_PV_FORECAST_ENTITY,
    CONF_USE_ADVANCED_MODE,
    DEFAULT_BATTERY_MAX_KWH,
    DEFAULT_MAX_SOC,
    DEFAULT_MIN_SOC,
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
        """Handle the user step - base config."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_USE_ADVANCED_MODE] = user_input.get(CONF_USE_ADVANCED_MODE, DEFAULT_USE_ADVANCED_MODE)
            # If advanced mode is enabled, go to the advanced step
            if user_input[CONF_USE_ADVANCED_MODE]:
                self._base_data = user_input
                return await self.async_step_advanced()
            else:
                # Linear mode only, create entry directly
                return self.async_create_entry(
                    title="Battery SoC Forecast",
                    data=user_input,
                )
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
                CONF_USE_ADVANCED_MODE,
                default=user_input.get(CONF_USE_ADVANCED_MODE, DEFAULT_USE_ADVANCED_MODE),
            ): bool,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the advanced mode step - PV forecast config."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Combine base data with advanced data
            data = {**self._base_data, **user_input}
            return self.async_create_entry(
                title="Battery SoC Forecast",
                data=data,
            )
        else:
            user_input = {}

        schema = vol.Schema({
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
            step_id="advanced",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

