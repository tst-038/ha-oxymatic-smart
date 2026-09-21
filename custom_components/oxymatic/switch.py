"""Switch entities for the OxyMatic integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OxyMaticConfigEntry, OxyMaticCoordinator
from .entity import OxyMaticEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class OxyMaticSwitchEntityDescription(SwitchEntityDescription):
    """Entity description for OxyMatic switches."""

    parameter: str


SWITCHES: tuple[OxyMaticSwitchEntityDescription, ...] = (
    OxyMaticSwitchEntityDescription(
        key="pump",
        translation_key="pump",
        icon="mdi:pump",
        parameter="pump",
    ),
    OxyMaticSwitchEntityDescription(
        key="heat",
        translation_key="heat",
        icon="mdi:water-boiler",
        parameter="heat",
    ),
    OxyMaticSwitchEntityDescription(
        key="aux1",
        translation_key="aux1",
        icon="mdi:dip-switch",
        parameter="aux1",
    ),
    OxyMaticSwitchEntityDescription(
        key="aux2",
        translation_key="aux2",
        icon="mdi:dip-switch",
        parameter="aux2",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OxyMaticConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OxyMatic switches from a config entry."""
    coordinator = entry.runtime_data

    entities: list[OxyMaticSwitch] = []
    for device_id in coordinator.data:
        for description in SWITCHES:
            entities.append(OxyMaticSwitch(coordinator, device_id, description))

    async_add_entities(entities)


class OxyMaticSwitch(OxyMaticEntity, SwitchEntity):
    """Switch entity for OxyMatic manual outputs."""

    entity_description: OxyMaticSwitchEntityDescription

    def __init__(
        self,
        coordinator: OxyMaticCoordinator,
        device_id: int,
        description: OxyMaticSwitchEntityDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        status = self.coordinator.data.get(self._device_id)
        if status is None:
            return False
        return status.buttons.get(self.entity_description.parameter, False)

    async def _async_toggle(self) -> None:
        """Toggle the switch via the API."""
        par = self.entity_description.parameter

        def _toggle():
            return self.coordinator.client.toggle_manual(self._device_id, par)

        await self.hass.async_add_executor_job(_toggle)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.is_on:
            return
        await self._async_toggle()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if not self.is_on:
            return
        await self._async_toggle()
        await self.coordinator.async_request_refresh()
