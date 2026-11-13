import copy

from homeassistant.const import STATE_OFF

from .conftest import DEVICE_CODE, MOCK_DETAIL, async_refresh_with_detail, card_entity_id


def _water_heater_id(hass) -> str:
    return card_entity_id(hass, "water_heater", "hot_water")


async def test_operation_modes_are_standard(hass, setup_integration):
    """Standard modes get translated by Home Assistant; custom ones like "on" are shown raw."""
    state = hass.states.get(_water_heater_id(hass))
    assert state.attributes["operation_list"] == ["heat_pump", "off"]
    assert state.state == STATE_OFF  # MOCK_DETAIL's hot water card has curSwitch False


async def test_switched_on_reports_heat_pump(hass, setup_integration, mock_login):
    detail = copy.deepcopy(MOCK_DETAIL)
    detail["cardList"][1]["curSwitch"] = True
    await async_refresh_with_detail(hass, setup_integration, detail, mock_login)

    assert hass.states.get(_water_heater_id(hass)).state == "heat_pump"


async def test_set_operation_mode(hass, setup_integration, mock_login):
    hot_water_card = MOCK_DETAIL["cardList"][1]
    for mode, expected in (("heat_pump", True), ("off", False)):
        mock_login.update_switch_state.reset_mock()
        await hass.services.async_call(
            "water_heater", "set_operation_mode",
            {"entity_id": _water_heater_id(hass), "operation_mode": mode},
            blocking=True,
        )
        mock_login.update_switch_state.assert_awaited_once_with(
            DEVICE_CODE, hot_water_card["switchAddress"], expected
        )


async def test_name_comes_from_translation(hass, setup_integration):
    """The name is translated ("Hot water" in English, "Warm water" in Dutch), not hard-coded."""
    assert hass.states.get(_water_heater_id(hass)).attributes["friendly_name"] == "My heat pump Hot water"


async def test_range_comes_from_card(hass, setup_integration):
    """Home Assistant's default range is 110-140 °F (43-60 °C); the device allows more."""
    state = hass.states.get(_water_heater_id(hass))

    assert state.attributes["min_temp"] == 18
    assert state.attributes["max_temp"] == 75
    assert state.attributes["target_temp_step"] == 1


async def test_set_temperature_above_home_assistant_default(hass, setup_integration, mock_login):
    await hass.services.async_call(
        "water_heater", "set_temperature",
        {"entity_id": _water_heater_id(hass), "temperature": 70},
        blocking=True,
    )

    mock_login.set_value.assert_awaited_once_with(
        DEVICE_CODE, MOCK_DETAIL["cardList"][1]["settingAddress"], 70
    )
