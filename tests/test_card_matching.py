"""Identifying heating and hot water cards, and reporting cards whose ID contradicts their modeList."""
import copy
import json
import logging
import re
from pathlib import Path

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import issue_registry as ir

import custom_components.ecohome as integration
from custom_components.ecohome.climate import _heating_card
from custom_components.ecohome.const import DOMAIN
from custom_components.ecohome.water_heater import _hot_water_card

from .conftest import DEVICE_CODE, MOCK_DETAIL, async_refresh_with_detail, card_entity_id


def test_card_id_rejects_mismatched_cards():
    """A card whose ID says it is the other kind is never picked, whatever its modeList."""
    heating_without_modes = {"card": "0", "modeList": None, "switchAddress": "1"}
    hot_water_with_modes = {"card": "2", "modeList": [{"modeMeaning": "Heat"}], "switchAddress": "2"}

    assert _hot_water_card([heating_without_modes]) is None
    assert _heating_card([hot_water_with_modes]) is None


def test_cards_without_id_still_identified_by_mode_list():
    heating = {"modeList": [{"modeMeaning": "Heat"}]}
    hot_water = {"modeList": None}

    assert _heating_card([hot_water, heating]) is heating
    assert _hot_water_card([heating, hot_water]) is hot_water


def _detail_with_mismatched_heating_card() -> dict:
    """Heating card (ID "0") that has lost its modeList, next to a normal hot water card."""
    detail = copy.deepcopy(MOCK_DETAIL)
    detail["cardList"][0]["card"] = "0"
    detail["cardList"][0]["modeList"] = None
    detail["cardList"][1]["card"] = "2"
    return detail


MISMATCH_ISSUE_ID = f"card_mismatch_{DEVICE_CODE}_0"


async def _refresh_with_mismatch(hass, entry, mock_client) -> None:
    await async_refresh_with_detail(hass, entry, _detail_with_mismatched_heating_card(), mock_client)


async def test_mismatched_card_logged_and_reported(hass, setup_integration, mock_login, caplog):
    caplog.set_level(logging.WARNING)
    await _refresh_with_mismatch(hass, setup_integration, mock_login)

    issue = ir.async_get(hass).async_get_issue(DOMAIN, MISMATCH_ISSUE_ID)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.translation_key == "card_mismatch"
    assert issue.translation_placeholders["card_id"] == "0"
    assert issue.translation_placeholders["id_kind"] == "heating"
    assert '"switchAddress": "1"' in issue.translation_placeholders["card"]

    # Every placeholder in the Repairs text must be filled in by the coordinator.
    translations = json.loads(
        (Path(integration.__file__).parent / "translations" / "en.json").read_text()
    )
    text = translations["issues"]["card_mismatch"]
    used = set(re.findall(r"{(\w+)}", text["title"] + text["description"]))
    assert used <= set(issue.translation_placeholders)

    warnings = [r for r in caplog.records if "card '0'" in r.getMessage()]
    assert len(warnings) == 1
    assert "switchAddress" in warnings[0].getMessage()

    # The mismatched card is not used: no climate, and the water heater keeps its own card.
    assert hass.states.get(card_entity_id(hass, "climate", "heating")).state == STATE_UNAVAILABLE
    water_heater = hass.states.get(card_entity_id(hass, "water_heater", "hot_water"))
    assert water_heater.attributes["current_temperature"] == 45.0


async def test_mismatched_card_logged_once(hass, setup_integration, mock_login, caplog):
    caplog.set_level(logging.WARNING)
    await _refresh_with_mismatch(hass, setup_integration, mock_login)
    await _refresh_with_mismatch(hass, setup_integration, mock_login)

    assert sum("card '0'" in r.getMessage() for r in caplog.records) == 1


async def test_mismatch_issue_removed_when_resolved(hass, setup_integration, mock_login):
    await _refresh_with_mismatch(hass, setup_integration, mock_login)
    assert ir.async_get(hass).async_get_issue(DOMAIN, MISMATCH_ISSUE_ID) is not None

    await async_refresh_with_detail(hass, setup_integration, copy.deepcopy(MOCK_DETAIL), mock_login)
    assert ir.async_get(hass).async_get_issue(DOMAIN, MISMATCH_ISSUE_ID) is None
    assert hass.states.get(card_entity_id(hass, "climate", "heating")).state == "heat"



async def test_mismatch_issue_removed_on_unload(hass, setup_integration, mock_login):
    await _refresh_with_mismatch(hass, setup_integration, mock_login)
    assert ir.async_get(hass).async_get_issue(DOMAIN, MISMATCH_ISSUE_ID) is not None

    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, MISMATCH_ISSUE_ID) is None
