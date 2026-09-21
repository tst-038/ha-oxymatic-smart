"""Base entity for OxyMatic integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OxyMaticCoordinator


class OxyMaticEntity(CoordinatorEntity[OxyMaticCoordinator]):
    """Common base for all OxyMatic entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OxyMaticCoordinator,
        device_id: int,
        entity_key: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._entity_key = entity_key
        self._attr_unique_id = f"{device_id}_{entity_key}"

        # Build device info from the first data point
        data = coordinator.data.get(device_id)
        name = data.device_name if data else f"Device {device_id}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_id))},
            name=name,
            manufacturer="Hydrover",
            model=data.device_name if data else None,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._device_id in self.coordinator.data
        ):
            return False

        # Diagnostic/connection entities stay available to report disconnection status & timestamps
        if self._entity_key in (
            "cloud_connection",
            "status_message",
            "last_read",
        ):
            return True

        # Telemetry and control entities are unavailable when the physical controller is disconnected
        status = self.coordinator.data[self._device_id]
        return bool(status.is_connected)
