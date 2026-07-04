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
