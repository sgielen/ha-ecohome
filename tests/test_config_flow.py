from unittest.mock import AsyncMock, patch

import httpx
from ecohome import ApiError, AuthenticationFailedError
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ecohome.const import DOMAIN

WRONG_PASSWORD = AuthenticationFailedError(
    "login", "-1", "Fout gebruikersnaam of wachtwoord"
)


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
    cls.login.assert_awaited_once_with(
        "test@example.com",
        "secret",
        language="en_US",
    )


async def test_user_step_wrong_password_shows_invalid_auth(hass):
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(side_effect=WRONG_PASSWORD)

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "wrong"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_step_server_error_shows_cannot_connect(hass):
    """An API error that is not an authentication failure is not the user's password."""
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(side_effect=ApiError("login", "500", "Systeemfout"))

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "secret"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_unreachable_server_shows_cannot_connect(hass):
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "secret"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_timeout_shows_cannot_connect(hass):
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "secret"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_recovers_after_error(hass, mock_client):
    """After a failed attempt the user can correct the password and continue."""
    with patch("custom_components.ecohome.config_flow.AsyncEcoHomeClient") as cls:
        cls.login = AsyncMock(side_effect=WRONG_PASSWORD)

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "wrong"},
        )
        assert result["errors"] == {"base": "invalid_auth"}

        cls.login = AsyncMock(return_value=mock_client)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test@example.com", "password": "secret"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {"username": "test@example.com", "password": "secret"}


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
