"""DataUpdateCoordinator for the OxyMatic integration."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .oxymatic import (
    DeviceStatus,
    OxyMaticAuthError,
    OxyMaticClient,
    OxyMaticConnectionError,
)

_LOGGER = logging.getLogger(__name__)

type OxyMaticConfigEntry = ConfigEntry["OxyMaticCoordinator"]


class OxyMaticCoordinator(DataUpdateCoordinator[dict[int, DeviceStatus]]):
    """Coordinator that fetches data from the OxyMatic cloud API."""

    config_entry: OxyMaticConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: OxyMaticConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_USERNAME]}",
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
        )
        self._client: OxyMaticClient | None = None
        self._device_ids: list[int] = []
        self.consecutive_failures: int = 0

    @property
    def client(self) -> OxyMaticClient:
        """Return the API client (must be initialised)."""
        if self._client is None:
            raise RuntimeError("Client not initialised")
        return self._client

    async def _async_update_data(self) -> dict[int, DeviceStatus]:
        """Fetch the latest data from all devices."""
        try:
            async with asyncio.timeout(60):
                data = await self.hass.async_add_executor_job(self._sync_update)
                self.consecutive_failures = 0
                return data
        except ConfigEntryAuthFailed:
            raise
        except (asyncio.TimeoutError, Exception) as err:
            self.consecutive_failures += 1
            if self.data and self.consecutive_failures <= 3:
                _LOGGER.warning(
                    "OxyMatic update error (%d consecutive), retaining previous state: %s",
                    self.consecutive_failures,
                    err,
                )
                return self.data
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def _sync_update(self) -> dict[int, DeviceStatus]:
        """Synchronous data fetch (runs in executor thread)."""
        username = self.config_entry.data[CONF_USERNAME]
        password = self.config_entry.data[CONF_PASSWORD]

        if self._client is None:
            self._client = OxyMaticClient(username=username, password=password)

        if not self._client.is_logged_in:
            try:
                if not self._client.login(username, password):
                    raise ConfigEntryAuthFailed("Invalid OxyMatic credentials")
            except OxyMaticAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except OxyMaticConnectionError as err:
                raise UpdateFailed(f"Connection error during login: {err}") from err

        # Only discover devices from account page if not yet cached
        if not self._device_ids:
            try:
                devices = self._client.get_devices()
                self._device_ids = list(devices.keys())
            except Exception as err:
                _LOGGER.warning("Failed to discover devices: %s", err)

        if not self._device_ids:
            raise UpdateFailed("No devices found")

        result: dict[int, DeviceStatus] = {}
        for device_id in self._device_ids:
            try:
                status = self._client.get_device_status(device_id)
                if status is not None:
                    result[device_id] = status
            except Exception as err:
                _LOGGER.warning("Failed to fetch status for device %s: %s", device_id, err)

        if not result:
            raise UpdateFailed("Failed to fetch status for any device")

        return result
