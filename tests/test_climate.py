import copy

import pytest
from homeassistant.components.climate.const import HVACMode
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.ecohome.const import DOMAIN

from .conftest import DEVICE_CODE, MOCK_DETAIL, async_refresh_with_detail


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


def _detail_with_heating(**fields) -> dict:
    detail = copy.deepcopy(MOCK_DETAIL)
    detail["cardList"][0].update(fields)
    return detail


async def test_climate_range_comes_from_card(hass, setup_integration):
    """Home Assistant's default range (7-35) is for room temperatures; this is a water temperature."""
    state = hass.states.get(await _climate_entity_id(hass))

    assert state.attributes["min_temp"] == 20
    assert state.attributes["max_temp"] == 55
    assert state.attributes["target_temp_step"] == 1


async def test_climate_invalid_range_falls_back_to_wide_range(hass, setup_integration, mock_login):
    for fields in ({"lowerTemp": None, "upperTemp": None}, {"lowerTemp": "60", "upperTemp": "20"}):
        detail = _detail_with_heating(**fields)
        await async_refresh_with_detail(hass, setup_integration, detail, mock_login)

        state = hass.states.get(await _climate_entity_id(hass))
        assert (state.attributes["min_temp"], state.attributes["max_temp"]) == (5, 75), fields


async def test_climate_curve_uses_wide_range(hass, setup_integration, mock_login):
    """With the climate curve on, the device reports the curve's target as both ends of the range."""
    detail = _detail_with_heating(isClimateCurve=True, lowerTemp="40", upperTemp="40", settingTemp="40.0")
    await async_refresh_with_detail(hass, setup_integration, detail, mock_login)

    state = hass.states.get(await _climate_entity_id(hass))
    assert (state.attributes["min_temp"], state.attributes["max_temp"]) == (5, 75)
    assert state.attributes["temperature"] == 40


async def test_climate_curve_refuses_temperature_change(hass, setup_integration, mock_login):
    detail = _detail_with_heating(isClimateCurve=True, lowerTemp="40", upperTemp="40", settingTemp="40.0")
    await async_refresh_with_detail(hass, setup_integration, detail, mock_login)

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            "climate", "set_temperature",
            {"entity_id": await _climate_entity_id(hass), "temperature": 45},
            blocking=True,
        )

    assert err.value.translation_key == "climate_curve_active"
    assert err.value.translation_placeholders == {"device_name": "My heat pump"}
    mock_login.set_value.assert_not_awaited()


async def test_climate_curve_still_allows_switching(hass, setup_integration, mock_login):
    detail = _detail_with_heating(isClimateCurve=True, lowerTemp="40", upperTemp="40")
    await async_refresh_with_detail(hass, setup_integration, detail, mock_login)

    await hass.services.async_call(
        "climate", "set_hvac_mode",
        {"entity_id": await _climate_entity_id(hass), "hvac_mode": HVACMode.OFF},
        blocking=True,
    )

    mock_login.update_switch_state.assert_awaited_once()
