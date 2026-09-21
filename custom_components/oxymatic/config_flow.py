"""Config flow for the OxyMatic integration."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN
from .oxymatic import OxyMaticClient


class OxyMaticConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow for OxyMatic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Present the user form and create the entry on valid input."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                valid = await self.hass.async_add_executor_job(
                    self._try_login, username, password
                )
            except Exception:
                valid = False

            if valid:
                return self.async_create_entry(
                    title=f"OxyMatic ({username})",
                    data={CONF_USERNAME: username, CONF_PASSWORD: password},
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def _try_login(username: str, password: str) -> bool:
        """Attempt a login to verify credentials (runs in executor)."""
        client = OxyMaticClient()
        return client.login(username, password)
