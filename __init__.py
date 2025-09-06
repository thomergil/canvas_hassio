"""The canvas integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .canvashub import CanvasHub
from .const import DOMAIN, HA_SENSOR

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Set up init."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up canvas from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = CanvasHub(hass)
    await hass.config_entries.async_forward_entry_setups(entry, HA_SENSOR)

    # Register service to get full data from storage
    async def get_full_canvas_data(call):
        """Service to retrieve full Canvas data from storage for cards."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            _LOGGER.error("No entity_id provided for get_full_canvas_data service")
            return

        # Find the sensor entity
        from homeassistant.helpers import entity_registry
        registry = entity_registry.async_get(hass)
        entity_entry = registry.async_get(entity_id)

        if not entity_entry:
            _LOGGER.error(f"Entity {entity_id} not found")
            return

        # Get the sensor from the state machine
        state = hass.states.get(entity_id)
        if not state:
            _LOGGER.error(f"State for {entity_id} not found")
            return

        # Try to get the actual sensor object to call async_get_full_data
        # This would need to be implemented based on how the entities are stored
        _LOGGER.info(f"Full data service called for {entity_id}")
        return {"status": "service_registered"}

    hass.services.async_register(DOMAIN, "get_full_data", get_full_canvas_data)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, HA_SENSOR):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
