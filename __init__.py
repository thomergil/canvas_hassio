"""The canvas integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CoreState, EVENT_HOMEASSISTANT_STARTED

from .canvashub import CanvasHub
from .const import DOMAIN, HA_SENSOR
from .frontend import JSModuleRegistration

_LOGGER = logging.getLogger(__name__)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register frontend resources."""
    module_register = JSModuleRegistration(hass)
    await module_register.async_register()


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the canvas integration."""
    async def _setup_frontend(_event=None) -> None:
        await _async_register_frontend(hass)

    if hass.state == CoreState.running:
        await _setup_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _setup_frontend)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up canvas from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = CanvasHub(hass)
    await hass.config_entries.async_forward_entry_setups(entry, HA_SENSOR)
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
