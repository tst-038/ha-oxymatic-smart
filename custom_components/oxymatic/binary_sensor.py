"""Binary sensor entities for the OxyMatic integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import OxyMaticConfigEntry, OxyMaticCoordinator
from .entity import OxyMaticEntity
from .oxymatic import DeviceStatus


@dataclass(frozen=True, kw_only=True)
class OxyMaticBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Entity description for OxyMatic binary sensors."""

    value_fn: Callable[[DeviceStatus], bool | None]


BINARY_SENSORS: tuple[OxyMaticBinarySensorEntityDescription, ...] = (
    OxyMaticBinarySensorEntityDescription(
        key="cloud_connection",
        translation_key="cloud_connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda s: s.is_connected,
    ),
    OxyMaticBinarySensorEntityDescription(
        key="pump_running",
        translation_key="pump_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda s: s.buttons.get("pump", False),
    ),
    OxyMaticBinarySensorEntityDescription(
        key="heating_active",
        translation_key="heating_active",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda s: s.buttons.get("heat", False),
    ),
    OxyMaticBinarySensorEntityDescription(
        key="water_flow",
        translation_key="water_flow",
        icon="mdi:water-check",
        value_fn=lambda s: s.buttons.get("flow", False),
    ),
    OxyMaticBinarySensorEntityDescription(
        key="oxidation_active",
        translation_key="oxidation_active",
        icon="mdi:molecule",
        value_fn=lambda s: (s.oxy_current is not None and s.oxy_current > 0)
        or s.buttons.get("oxy", False),
    ),
    OxyMaticBinarySensorEntityDescription(
        key="ionization_active",
        translation_key="ionization_active",
        icon="mdi:atom",
        value_fn=lambda s: (s.ion_current is not None and s.ion_current > 0)
        or s.buttons.get("ionper", False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OxyMaticConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OxyMatic binary sensors from a config entry."""
    coordinator = entry.runtime_data

    entities: list[OxyMaticBinarySensor] = []
    for device_id in coordinator.data:
        for description in BINARY_SENSORS:
            entities.append(
                OxyMaticBinarySensor(coordinator, device_id, description)
            )

    async_add_entities(entities)


class OxyMaticBinarySensor(OxyMaticEntity, BinarySensorEntity):
    """Binary sensor entity for an OxyMatic status reading."""

    entity_description: OxyMaticBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: OxyMaticCoordinator,
        device_id: int,
        description: OxyMaticBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        status = self.coordinator.data.get(self._device_id)
        if status is None:
            return None
        return self.entity_description.value_fn(status)
