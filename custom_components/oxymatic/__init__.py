"""The OxyMatic integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import OxyMaticConfigEntry, OxyMaticCoordinator

PLATFORMS = [
    Platform.SENSOR,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: OxyMaticConfigEntry
) -> bool:
    """Set up OxyMatic from a config entry."""
    coordinator = OxyMaticCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: OxyMaticConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
