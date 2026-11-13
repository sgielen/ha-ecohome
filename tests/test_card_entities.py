"""Climate and water heater entities when the API temporarily returns no cards (heat pump offline)."""
import copy

import pytest
from homeassistant.const import STATE_UNAVAILABLE

from .conftest import MOCK_DETAIL, async_refresh_with_detail, card_entity_id

CARD_ENTITIES = [("climate", "heating"), ("water_heater", "hot_water")]


def _detail_without_cards() -> dict:
    detail = copy.deepcopy(MOCK_DETAIL)
    detail["cardList"] = []
    return detail


@pytest.fixture
async def setup_without_cards(hass, config_entry, mock_login):
    """Set up the integration while the API returns no cards."""
    mock_login.get_device_detail.return_value = _detail_without_cards()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_entities_not_created_without_cards(hass, setup_without_cards):
    for platform, suffix in CARD_ENTITIES:
        assert card_entity_id(hass, platform, suffix) is None


async def test_entities_added_when_cards_appear(hass, setup_without_cards, mock_login):
    await async_refresh_with_detail(hass, setup_without_cards, copy.deepcopy(MOCK_DETAIL), mock_login)

    climate = hass.states.get(card_entity_id(hass, "climate", "heating"))
    assert climate.state == "heat"
    assert climate.attributes["current_temperature"] == 21.5

    water_heater = hass.states.get(card_entity_id(hass, "water_heater", "hot_water"))
    assert water_heater.state == "off"
    assert water_heater.attributes["current_temperature"] == 45.0


async def test_entities_added_only_once(hass, setup_without_cards, mock_login):
    await async_refresh_with_detail(hass, setup_without_cards, copy.deepcopy(MOCK_DETAIL), mock_login)
    await async_refresh_with_detail(hass, setup_without_cards, copy.deepcopy(MOCK_DETAIL), mock_login)

    assert len(hass.states.async_entity_ids("climate")) == 1
    assert len(hass.states.async_entity_ids("water_heater")) == 1


async def test_entities_unavailable_while_cards_missing(hass, setup_integration, mock_login):
    await async_refresh_with_detail(hass, setup_integration, _detail_without_cards(), mock_login)
    for platform, suffix in CARD_ENTITIES:
        assert hass.states.get(card_entity_id(hass, platform, suffix)).state == STATE_UNAVAILABLE

    await async_refresh_with_detail(hass, setup_integration, copy.deepcopy(MOCK_DETAIL), mock_login)
    for platform, suffix in CARD_ENTITIES:
        assert hass.states.get(card_entity_id(hass, platform, suffix)).state != STATE_UNAVAILABLE


async def test_missing_card_list_is_handled(hass, setup_integration, mock_login):
    detail = copy.deepcopy(MOCK_DETAIL)
    detail["cardList"] = None
    await async_refresh_with_detail(hass, setup_integration, detail, mock_login)
    for platform, suffix in CARD_ENTITIES:
        assert hass.states.get(card_entity_id(hass, platform, suffix)).state == STATE_UNAVAILABLE
