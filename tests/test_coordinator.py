from unittest.mock import AsyncMock, patch

from ecohome import SessionExpiredError

from custom_components.ecohome.coordinator import EcoHomeCoordinator

from .conftest import MOCK_DETAIL, MOCK_DEVICES


async def test_session_relogin_preserves_language(hass, config_entry):
    hass.config.language = "de"

    expired_client = AsyncMock()
    expired_client.get_device_detail.side_effect = SessionExpiredError
    expired_client.get_param_list.return_value = []

    refreshed_client = AsyncMock()
    refreshed_client.get_device_detail.return_value = MOCK_DETAIL
    refreshed_client.get_param_list.return_value = []

    with patch(
        "custom_components.ecohome.coordinator.AsyncEcoHomeClient"
    ) as client_class:
        client_class.login = AsyncMock(side_effect=[expired_client, refreshed_client])
        coordinator = EcoHomeCoordinator(hass, config_entry, MOCK_DEVICES[0])

        await coordinator._async_update_data()

    assert client_class.login.await_args_list[0].kwargs == {"language": "de_DE"}
    assert client_class.login.await_args_list[1].kwargs == {
        "force_relogin": True,
        "language": "de_DE",
    }
