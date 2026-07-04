from homeassistant.components.climate.const import HVACMode
from homeassistant.helpers import entity_registry as er

from custom_components.ecohome.const import DOMAIN

from .conftest import DEVICE_CODE, MOCK_DETAIL


async def _climate_entity_id(hass):
    registry = er.async_get(hass)
    return registry.async_get_entity_id("climate", DOMAIN, f"{DEVICE_CODE}_heating")


async def test_climate_initial_state(hass, setup_integration):
    entity_id = await _climate_entity_id(hass)
    state = hass.states.get(entity_id)

    assert state.state == HVACMode.HEAT
    assert state.attributes["current_temperature"] == 21.5
    assert state.attributes["temperature"] == 22.0


async def test_climate_set_hvac_mode_off(hass, setup_integration, mock_login):
    entity_id = await _climate_entity_id(hass)
    heating_card = MOCK_DETAIL["cardList"][0]

    await hass.services.async_call(
        "climate", "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": HVACMode.OFF},
        blocking=True,
    )

    mock_login.update_switch_state.assert_awaited_once_with(
        DEVICE_CODE, heating_card["switchAddress"], False
    )


async def test_climate_set_temperature(hass, setup_integration, mock_login):
    entity_id = await _climate_entity_id(hass)
    heating_card = MOCK_DETAIL["cardList"][0]

    await hass.services.async_call(
        "climate", "set_temperature",
        {"entity_id": entity_id, "temperature": 24},
        blocking=True,
    )

    mock_login.set_value.assert_awaited_once_with(
        DEVICE_CODE, heating_card["settingAddress"], 24
    )
