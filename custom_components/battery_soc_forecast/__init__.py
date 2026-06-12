"""Battery SoC Forecast integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery SoC Forecast from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Trigger initial sensor update after setup completes
    hass.async_create_task(async_trigger_sensor_update(hass))
    return True


async def async_trigger_sensor_update(hass: HomeAssistant) -> None:
    """Trigger an immediate sensor update after a short delay."""
    import asyncio
    # Wait for the sensor to be fully initialized
    await asyncio.sleep(0.5)

    state = hass.states.get("sensor.battery_soc_forecast")
    if state:
        # Trigger state update by calling update_entity service
        await hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": "sensor.battery_soc_forecast"},
            blocking=True,
        )


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
