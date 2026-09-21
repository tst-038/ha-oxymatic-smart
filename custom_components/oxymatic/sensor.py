"""Sensor entities for the OxyMatic integration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import OxyMaticConfigEntry
from .entity import OxyMaticEntity
from .oxymatic import DeviceStatus

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class OxyMaticSensorEntityDescription(SensorEntityDescription):
    """Entity description for OxyMatic sensors."""

    value_fn: Callable[[DeviceStatus], StateType]


SENSORS: tuple[OxyMaticSensorEntityDescription, ...] = (
    OxyMaticSensorEntityDescription(
        key="water_temp",
        translation_key="water_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: s.water_temp,
    ),
    OxyMaticSensorEntityDescription(
        key="ph",
        translation_key="ph",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda s: s.ph,
    ),
    OxyMaticSensorEntityDescription(
        key="orp",
        translation_key="orp",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mV",
        value_fn=lambda s: s.orp,
    ),
    OxyMaticSensorEntityDescription(
        key="oxy_current",
        translation_key="oxy_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda s: s.oxy_current,
    ),
    OxyMaticSensorEntityDescription(
        key="oxy_voltage",
        translation_key="oxy_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda s: s.oxy_voltage,
    ),
    OxyMaticSensorEntityDescription(
        key="ion_current",
        translation_key="ion_current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda s: s.ion_current,
    ),
    OxyMaticSensorEntityDescription(
        key="ion_voltage",
        translation_key="ion_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda s: s.ion_voltage,
    ),
    OxyMaticSensorEntityDescription(
        key="copper",
        translation_key="copper",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mg/L",
        value_fn=lambda s: s.copper,
    ),
    OxyMaticSensorEntityDescription(
        key="chlorine",
        translation_key="chlorine",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mg/L",
        value_fn=lambda s: s.chlorine,
    ),
    OxyMaticSensorEntityDescription(
        key="water_temp_target",
        translation_key="water_temp_target",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: s.water_temp_max,
    ),
    OxyMaticSensorEntityDescription(
        key="active_program",
        translation_key="active_program",
        icon="mdi:calendar-clock",
        value_fn=lambda s: s.program or "Unknown",
    ),
    OxyMaticSensorEntityDescription(
        key="operating_mode",
        translation_key="operating_mode",
        icon="mdi:cog",
        value_fn=lambda s: s.mode or "Unknown",
    ),
    OxyMaticSensorEntityDescription(
        key="last_read",
        translation_key="last_read",
        icon="mdi:clock-check",
        value_fn=lambda s: s.last_read,
    ),
    OxyMaticSensorEntityDescription(
        key="status_message",
        translation_key="status_message",
        icon="mdi:information-outline",
        value_fn=lambda s: s.error_message if s.error_message else "Normal",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OxyMaticConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OxyMatic sensors from a config entry."""
    coordinator = entry.runtime_data

    entities: list[OxyMaticSensor] = []
    for device_id in coordinator.data:
        for description in SENSORS:
            entities.append(
                OxyMaticSensor(coordinator, device_id, description)
            )

    async_add_entities(entities)


class OxyMaticSensor(OxyMaticEntity, SensorEntity):
    """A sensor entity for an OxyMatic device reading."""

    entity_description: OxyMaticSensorEntityDescription

    def __init__(
        self,
        coordinator,
        device_id: int,
        description: OxyMaticSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value."""
        status = self.coordinator.data.get(self._device_id)
        if status is None:
            return None
        return self.entity_description.value_fn(status)
