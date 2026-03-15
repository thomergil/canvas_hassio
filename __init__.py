"""The canvas integration."""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .canvashub import CanvasHub
from .const import DOMAIN, HA_SENSOR

_LOGGER = logging.getLogger(__name__)

CARD_JS = "custom-canvas-homework-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"


def setup(hass, config):
    """Set up init."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up canvas from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = CanvasHub(hass)
    await hass.config_entries.async_forward_entry_setups(entry, HA_SENSOR)

    # Register frontend card (only once across multiple config entries)
    if "canvas_card_registered" not in hass.data[DOMAIN]:
        card_path = os.path.join(
            os.path.dirname(__file__), "www", CARD_JS
        )
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, card_path, True)]
        )
        add_extra_js_url(hass, CARD_URL)
        hass.data[DOMAIN]["canvas_card_registered"] = True

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
