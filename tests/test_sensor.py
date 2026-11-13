from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.helpers import entity_registry as er

from custom_components.ecohome.const import DOMAIN

from .conftest import DEVICE_CODE, MOCK_OPERATIONAL_PARAMS, MOCK_SENSOR_PARAMS


def _all_addresses(params):
    """Collect all addresses from flat or nested param lists."""
    addresses = []
    for item in params:
        if "moduleContent" in item:
            addresses.extend(p["address"] for p in item["moduleContent"])
        else:
            addresses.append(item["address"])
    return addresses


async def test_all_params_registered(hass, setup_integration):
    """Every address from both param lists should have a registered entity, including N/A ones."""
    registry = er.async_get(hass)

    for address in _all_addresses(MOCK_SENSOR_PARAMS):
        uid = f"{DEVICE_CODE}_sensors_{address}"
        assert registry.async_get_entity_id("sensor", DOMAIN, uid) is not None, (
            f"sensor entity missing for address {address}"
        )

    for address in _all_addresses(MOCK_OPERATIONAL_PARAMS):
        uid = f"{DEVICE_CODE}_operational_{address}"
        assert registry.async_get_entity_id("sensor", DOMAIN, uid) is not None, (
            f"operational entity missing for address {address}"
        )


async def test_na_value_is_none(hass, setup_integration):
    """A param with addressValue N/A should report state unknown (None native_value)."""
    registry = er.async_get(hass)
    # address 1002 has addressValue "N/A" in MOCK_SENSOR_PARAMS
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_sensors_1002")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state.state == "unknown"


async def test_valid_value_is_float(hass, setup_integration):
    registry = er.async_get(hass)
    # address 1000 has addressValue "21.5"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_sensors_1000")
    state = hass.states.get(entity_id)
    assert state.state == "21.5"


async def test_empty_value_is_none(hass, setup_integration):
    """An empty addressValue on a numeric sensor should report unknown, not raise."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_sensors_1003")
    assert hass.states.get(entity_id).state == "unknown"


async def test_unparseable_numeric_value_is_none(hass, setup_integration):
    """A non-numeric addressValue on a sensor with a unit should report unknown, not raise."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_sensors_1004")
    assert hass.states.get(entity_id).state == "unknown"


async def test_unicode_celsius_unit_is_normalized(hass, setup_integration):
    """The single-character \u2103 unit should map to \u00b0C with temperature device class."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_sensors_1005")
    state = hass.states.get(entity_id)
    assert state.state == "38.0"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE


async def test_duplicate_names_get_address(hass, config_entry, mock_login):
    """Parameters with the same name (as in some languages) are told apart by their address."""
    sensor_params = [
        {"address": "1000", "addressValue": "21.5", "pointName": "Température ambiante", "unit": "°C"},
        {"address": "1001", "addressValue": "5.0", "pointName": "Température ambiante", "unit": "°C"},
        {"address": "1002", "addressValue": "45.0", "pointName": "Température de l'eau", "unit": "°C"},
    ]
    operational_params = [
        {"address": "2000", "addressValue": "45.0", "pointName": "Température de l'eau ", "unit": "°C"},
        {"address": "2001", "addressValue": "1200", "pointName": "Vitesse du compresseur", "unit": "rpm"},
    ]

    async def get_param_list(device_code, param_type):
        return sensor_params if param_type == 0 else operational_params

    mock_login.get_param_list.side_effect = get_param_list
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)

    def name(source, address):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_{source}_{address}")
        return registry.async_get(entity_id).original_name

    assert name("sensors", "1000") == "Température ambiante (1000)"
    assert name("sensors", "1001") == "Température ambiante (1001)"
    # Duplicates across the two parameter lists count as well; names are compared after stripping.
    assert name("sensors", "1002") == "Température de l'eau (1002)"
    assert name("operational", "2000") == "Température de l'eau (2000)"
    assert name("operational", "2001") == "Vitesse du compresseur"
