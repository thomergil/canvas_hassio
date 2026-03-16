"""Frontend registration for canvas integration."""
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)

CARD_JS = "custom-canvas-homework-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_JS}"


async def async_setup_view(hass: HomeAssistant) -> None:
    """Register the Canvas card frontend resources."""

    # Serve the card JS file
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL,
                hass.config.path(f"custom_components/{DOMAIN}/frontend/{CARD_JS}"),
                True,
            )
        ]
    )
    add_extra_js_url(hass, CARD_URL + "?" + INTEGRATION_VERSION)

    # Also register as a lovelace resource so it shows in the card picker
    resources = hass.data["lovelace"].resources
    resource_url = CARD_URL + "?automatically-added&" + INTEGRATION_VERSION
    if resources:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        frontend_added = False
        for r in resources.async_items():
            if r["url"].startswith(CARD_URL):
                frontend_added = True
                if not r["url"].endswith(INTEGRATION_VERSION):
                    if isinstance(resources, ResourceStorageCollection):
                        await resources.async_update_item(
                            r["id"],
                            {
                                "res_type": "module",
                                "url": resource_url,
                            },
                        )
                break

        if not frontend_added:
            if getattr(resources, "async_create_item", None):
                await resources.async_create_item(
                    {
                        "res_type": "module",
                        "url": resource_url,
                    }
                )
