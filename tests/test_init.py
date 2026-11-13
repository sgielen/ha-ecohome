from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.ecohome.const import DOMAIN, MANUFACTURER

from .conftest import DEVICE_CODE, MOCK_DEVICES


async def test_setup_loads_entry(hass, setup_integration):
    entry = setup_integration
    assert entry.state == ConfigEntryState.LOADED


async def test_setup_registers_all_entity_types(hass, setup_integration):
    registry = er.async_get(hass)

    climate_id = registry.async_get_entity_id("climate", DOMAIN, f"{DEVICE_CODE}_heating")
    water_heater_id = registry.async_get_entity_id("water_heater", DOMAIN, f"{DEVICE_CODE}_hot_water")

    assert climate_id is not None
    assert water_heater_id is not None


async def test_device_info(hass, setup_integration):
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, DEVICE_CODE)})

    assert device is not None
    assert device.name == MOCK_DEVICES[0]["device_nick_name"]
    assert device.manufacturer == MANUFACTURER
    assert device.model == MOCK_DEVICES[0]["device_name"]


async def test_unload_entry(hass, setup_integration):
    entry = setup_integration
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state == ConfigEntryState.NOT_LOADED
    assert DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]


async def test_shared_devices_are_set_up(hass, config_entry, mock_login):
    """Devices shared with the account (returned by list_all_devices) get their own device and entities."""
    shared_code = "WQ0B07654321"
    mock_login.list_all_devices.return_value = [
        *MOCK_DEVICES,
        {"device_code": shared_code, "device_nick_name": "Neighbour's heat pump", "device_name": "Heat Pump"},
    ]
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    for code in (DEVICE_CODE, shared_code):
        assert devices.async_get_device(identifiers={(DOMAIN, code)}) is not None
        assert entities.async_get_entity_id("climate", DOMAIN, f"{code}_heating") is not None
    assert devices.async_get_device(identifiers={(DOMAIN, shared_code)}).name == "Neighbour's heat pump"
    mock_login.list_devices.assert_not_called()
