"""Detecting that the heat pump goes offline and comes back, and what the entities do meanwhile."""
import json
import logging
import re
from datetime import timedelta
from pathlib import Path

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

import custom_components.ecohome as integration

from custom_components.ecohome.const import DOMAIN

from .conftest import DEVICE_CODE, MOCK_DEVICES, card_entity_id

OFFLINE_DEVICES = [{**MOCK_DEVICES[0], "device_status": "OFFLINE", "running_status": "offline"}]


def _connectivity_id(hass) -> str:
    return er.async_get(hass).async_get_entity_id("binary_sensor", DOMAIN, f"{DEVICE_CODE}_connectivity")


def _data_entity_ids(hass) -> list[str]:
    """A sensor, the climate and the water heater: all entities that show heat pump data."""
    sensor = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{DEVICE_CODE}_sensors_1000")
    return [
        sensor,
        card_entity_id(hass, "climate", "heating"),
        card_entity_id(hass, "water_heater", "hot_water"),
    ]


async def _refresh_with_devices(hass, entry, mock_client, devices: list[dict]) -> None:
    mock_client.list_all_devices.return_value = devices
    await hass.data[DOMAIN][entry.entry_id][0].async_refresh()
    await hass.async_block_till_done()


async def test_connectivity_on_while_online(hass, setup_integration):
    state = hass.states.get(_connectivity_id(hass))
    assert state.state == STATE_ON
    assert state.attributes["device_class"] == "connectivity"
    assert er.async_get(hass).async_get(_connectivity_id(hass)).entity_category == "diagnostic"


async def test_offline_makes_data_entities_unavailable(hass, setup_integration, mock_login):
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)

    assert hass.states.get(_connectivity_id(hass)).state == STATE_OFF
    for entity_id in _data_entity_ids(hass):
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE, entity_id


async def test_back_online_restores_entities(hass, setup_integration, mock_login):
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    await _refresh_with_devices(hass, setup_integration, mock_login, MOCK_DEVICES)

    assert hass.states.get(_connectivity_id(hass)).state == STATE_ON
    sensor, climate, water_heater = (hass.states.get(e) for e in _data_entity_ids(hass))
    assert sensor.state == "21.5"
    assert climate.state == "heat"
    assert water_heater.state == "off"


async def test_device_missing_from_list_counts_as_offline(hass, setup_integration, mock_login, caplog):
    caplog.set_level(logging.WARNING)
    await _refresh_with_devices(hass, setup_integration, mock_login, [])

    assert hass.states.get(_connectivity_id(hass)).state == STATE_OFF
    assert any("no longer in this account's device list" in r.getMessage() for r in caplog.records)


async def test_offline_and_online_logged_once(hass, setup_integration, mock_login, caplog):
    caplog.set_level(logging.INFO, logger="custom_components.ecohome.coordinator")
    for _ in range(2):
        await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    for _ in range(2):
        await _refresh_with_devices(hass, setup_integration, mock_login, MOCK_DEVICES)

    messages = [r.getMessage() for r in caplog.records]
    offline = [m for m in messages if "is offline" in m]
    online = [m for m in messages if m.endswith(") is back online")]
    assert len(offline) == 1
    assert "WQ0B01234567" in offline[0]
    assert len(online) == 1


async def test_offline_at_startup_logged(hass, config_entry, mock_login, caplog):
    caplog.set_level(logging.WARNING)
    mock_login.list_all_devices.return_value = OFFLINE_DEVICES
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert sum("is offline" in r.getMessage() for r in caplog.records) == 1
    assert hass.states.get(_connectivity_id(hass)).state == STATE_OFF


async def test_online_at_startup_not_logged(hass, setup_integration, caplog):
    assert not any(r.getMessage().endswith(") is back online") for r in caplog.records)


async def test_connectivity_unavailable_when_cloud_unreachable(hass, setup_integration, mock_login):
    """If the cloud itself fails, the heat pump's state is unknown, so connectivity is unavailable too."""
    mock_login.get_device_detail.side_effect = Exception("cloud down")
    await hass.data[DOMAIN][setup_integration.entry_id][0].async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(_connectivity_id(hass)).state == STATE_UNAVAILABLE


OFFLINE_ISSUE_ID = f"device_offline_{DEVICE_CODE}"


def _offline_issue(hass):
    return ir.async_get(hass).async_get_issue(DOMAIN, OFFLINE_ISSUE_ID)


async def test_offline_issue_after_ten_minutes(hass, setup_integration, mock_login, freezer):
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    assert _offline_issue(hass) is None

    freezer.tick(timedelta(minutes=9))
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    assert _offline_issue(hass) is None

    freezer.tick(timedelta(minutes=1))
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    issue = _offline_issue(hass)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
    assert issue.translation_key == "device_offline"
    assert issue.translation_placeholders["device_code"] == DEVICE_CODE
    assert issue.translation_placeholders["minutes"] == "10"

    # Every placeholder in the Repairs text must be filled in by the coordinator.
    translations = json.loads(
        (Path(integration.__file__).parent / "translations" / "en.json").read_text()
    )
    text = translations["issues"]["device_offline"]
    used = set(re.findall(r"{(\w+)}", text["title"] + text["description"]))
    assert used <= set(issue.translation_placeholders)


async def test_offline_issue_removed_when_back_online(hass, setup_integration, mock_login, freezer):
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    freezer.tick(timedelta(minutes=10))
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    assert _offline_issue(hass) is not None

    await _refresh_with_devices(hass, setup_integration, mock_login, MOCK_DEVICES)
    assert _offline_issue(hass) is None


async def test_short_outage_creates_no_issue(hass, setup_integration, mock_login, freezer):
    """The delay starts over with each outage, so two short outages never add up to an issue."""
    for _ in range(2):
        await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
        freezer.tick(timedelta(minutes=6))
        await _refresh_with_devices(hass, setup_integration, mock_login, MOCK_DEVICES)
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    assert _offline_issue(hass) is None


async def test_offline_issue_removed_on_unload(hass, setup_integration, mock_login, freezer):
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    freezer.tick(timedelta(minutes=10))
    await _refresh_with_devices(hass, setup_integration, mock_login, OFFLINE_DEVICES)
    assert _offline_issue(hass) is not None

    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert _offline_issue(hass) is None
