"""Light entities for the OxyMatic integration."""

import logging

from homeassistant.components.light import LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OxyMaticConfigEntry
from .entity import OxyMaticEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OxyMaticConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OxyMatic lights from a config entry."""
    coordinator = entry.runtime_data

    entities: list[OxyMaticLight] = []
    for device_id in coordinator.data:
        entities.append(OxyMaticLight(coordinator, device_id))

    async_add_entities(entities)


class OxyMaticLight(OxyMaticEntity, LightEntity):
    """Light entity for the OxyMatic pool light."""

    _attr_translation_key = "light"

    def __init__(self, coordinator, device_id: int) -> None:
        """Initialise the light."""
        super().__init__(coordinator, device_id, "light")

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        status = self.coordinator.data.get(self._device_id)
        if status is None:
            return False
        return status.lights_state == "on"

    async def _async_toggle_light(self) -> None:
        """Toggle the light via the API."""

        def _toggle():
            return self.coordinator.client.toggle_manual(
                self._device_id, "light"
            )

        await self.hass.async_add_executor_job(_toggle)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        if self.is_on:
            return
        await self._async_toggle_light()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        if not self.is_on:
            return
        await self._async_toggle_light()
        await self.coordinator.async_request_refresh()
