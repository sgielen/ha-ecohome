import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from ecohome import AsyncEcoHomeClient

from .const import DOMAIN
from .coordinator import EcoHomeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CLIMATE, Platform.WATER_HEATER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        client = await AsyncEcoHomeClient.login(
            entry.data["username"],
            entry.data["password"],
        )
        devices = await client.list_all_devices()
    except Exception as err:
        raise ConfigEntryNotReady(f"Could not connect to Eco-Home API: {err}") from err

    device_registry = dr.async_get(hass)
    coordinators: list[EcoHomeCoordinator] = []
    for device in devices:
        # Devices the user disabled in Home Assistant are not polled at all. Home Assistant reloads
        # this config entry when such a device is enabled again.
        registered = device_registry.async_get_device(identifiers={(DOMAIN, device["device_code"])})
        if registered is not None and registered.disabled_by is not None:
            _LOGGER.debug("Skipping disabled device %s", device["device_code"])
            continue
        coordinator = EcoHomeCoordinator(hass, entry, device)
        await coordinator.async_config_entry_first_refresh()
        coordinators.append(coordinator)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinators: list[EcoHomeCoordinator] = hass.data[DOMAIN].pop(entry.entry_id)
        for coordinator in coordinators:
            coordinator.async_clear_issues()
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
