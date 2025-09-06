"""Config flow for canvas integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_BASEURI, CONF_SECRET, DEFAULT_SEMAPHORE, DOMAIN, NAME, VERSION, CONF_SEMAPHORE, CONF_DISABLE_PERSISTENCE, DEFAULT_DISABLE_PERSISTENCE

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_BASEURI): str, vol.Required(CONF_SECRET): str}
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    return {"title": NAME, CONF_BASEURI: "test", CONF_SECRET: "test"}


@config_entries.HANDLERS.register(DOMAIN)
class CanvasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for canvas."""

    VERSION = VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options Flow Class"""
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.warn("init options flow handler no user input")
            return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SEMAPHORE,
                        default = self.config_entry.options.get(CONF_SEMAPHORE, DEFAULT_SEMAPHORE),
                        description = {
                            CONF_SEMAPHORE: "The Semaphore is the number of concurrent requests to send to the Canvas API. Since Canvas rate-limits requests, it is recommended to keep this number low (max 15) to prevent rate limiting."
                        }
                    ): int,
                    vol.Optional(
                        CONF_DISABLE_PERSISTENCE,
                        default = self.config_entry.options.get(CONF_DISABLE_PERSISTENCE, DEFAULT_DISABLE_PERSISTENCE),
                        description = {
                            CONF_DISABLE_PERSISTENCE: "Disable persistent storage for homework events. When enabled, the integration will work with raw Canvas data only and won't remember previously seen assignments across restarts. Useful for debugging or if you prefer not to use caching."
                        }
                    ): bool
                }
            ),
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
