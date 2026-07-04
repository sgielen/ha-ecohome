from unittest.mock import AsyncMock, patch

from homeassistant.data_entry_flow import FlowResultType

from custom_components.ecohome.const import DOMAIN


async def test_user_step_creates_entry(hass, mock_client):
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(return_value=mock_client)

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "secret"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {"username": "test@example.com", "password": "secret"}
    cls.login.assert_awaited_once_with("test@example.com", "secret")


async def test_user_step_login_failure_shows_error(hass):
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(side_effect=RuntimeError("bad credentials"))

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "wrong"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_account_aborts(hass, config_entry, mock_login):
    config_entry.add_to_hass(hass)

    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(return_value=mock_login)

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "secret"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
