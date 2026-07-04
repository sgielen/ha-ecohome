from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecohome.const import DOMAIN

DEVICE_CODE = "WQ0B01234567"

MOCK_DEVICES = [
    {
        "device_code": DEVICE_CODE,
        "device_nick_name": "My heat pump",
        "device_name": "Heating & Cooling Heat Pump",
    }
]

MOCK_DETAIL = {
    "curUnit": "°C",
    "cardList": [
        {
            "curSwitch": True,
            "curTempMain": "21.5",
            "curTempMinor": None,
            "settingTemp": "22.0",
            "switchAddress": "1",
            "settingAddress": "100",
            "modeList": [{"modeMeaning": "Heat"}],
        },
        {
            "curSwitch": False,
            "curTempMain": "45.0",
            "curTempMinor": None,
            "settingTemp": "55.0",
            "switchAddress": "2",
            "settingAddress": "1024",
            "modeList": None,
        },
    ],
}

# Type 0: sensor temps (flat list)
MOCK_SENSOR_PARAMS = [
    {"address": "1000", "addressValue": "21.5", "pointName": "Outdoor temp", "unit": "°C"},
    {"address": "1001", "addressValue": "45.0", "pointName": "Water inlet temp", "unit": "°C"},
    {"address": "1002", "addressValue": "N/A", "pointName": "Unused sensor", "unit": "°C"},
]

# Type 1: operational (nested in modules)
MOCK_OPERATIONAL_PARAMS = [
    {
        "moduleName": "0#",
        "moduleContent": [
            {"address": "2072", "addressValue": "1200", "pointName": "Compressor speed", "unit": "rpm"},
            {"address": "2192", "addressValue": "N/A", "pointName": "Pump flow", "unit": "L/h"},
        ],
    }
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this suite."""
    yield enable_custom_integrations


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.list_devices.return_value = MOCK_DEVICES
    client.get_device_detail.return_value = MOCK_DETAIL

    async def get_param_list(device_code, param_type):
        return MOCK_SENSOR_PARAMS if param_type == 0 else MOCK_OPERATIONAL_PARAMS

    client.get_param_list.side_effect = get_param_list
    return client


@pytest.fixture
def mock_login(mock_client):
    """Patch AsyncEcoHomeClient.login at all import sites."""
    with (
        patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cf_cls,
        patch("custom_components.ecohome.coordinator.AsyncEcoHomeClient") as coord_cls,
        patch("custom_components.ecohome.AsyncEcoHomeClient") as init_cls,
    ):
        for cls in (cf_cls, coord_cls, init_cls):
            cls.login = AsyncMock(return_value=mock_client)
        yield mock_client


@pytest.fixture
def config_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test@example.com", "password": "testpassword"},
        unique_id="test@example.com",
    )


@pytest.fixture
async def setup_integration(hass, config_entry, mock_login):
    """Set up the integration and return the config entry."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
