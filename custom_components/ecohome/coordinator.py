import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ecohome import AsyncEcoHomeClient, SessionExpiredError

from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _flatten_params(param_list: list) -> list[dict]:
    result = []
    for item in param_list:
        if "moduleContent" in item:
            result.extend(item["moduleContent"])
        else:
            result.append(item)
    return result


class EcoHomeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device: dict) -> None:
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device['device_code']}",
            update_interval=timedelta(minutes=interval),
        )
        self._entry = entry
        self.device_code: str = device["device_code"]
        self.device_name: str = device.get("device_nick_name") or device["device_code"]
        self.device_model: str = device.get("device_name") or "Eco-Home"
        self.device_img_url: str | None = device.get("product_img_url")
        self._client: AsyncEcoHomeClient | None = None

    async def _get_client(self) -> AsyncEcoHomeClient:
        if self._client is None:
            self._client = await AsyncEcoHomeClient.login(
                self._entry.data["username"],
                self._entry.data["password"],
            )
        return self._client

    async def _async_update_data(self) -> dict:
        try:
            return await self._fetch()
        except SessionExpiredError:
            _LOGGER.warning("Session expired, re-logging in")
            try:
                self._client = await AsyncEcoHomeClient.login(
                    self._entry.data["username"],
                    self._entry.data["password"],
                    force_relogin=True,
                )
                return await self._fetch()
            except Exception as err:
                raise UpdateFailed(f"Error after re-login: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def async_update_switch_state(self, address: str, value: bool) -> None:
        client = await self._get_client()
        await client.update_switch_state(self.device_code, address, value)

    async def async_set_value(self, address: str, value: int) -> None:
        client = await self._get_client()
        await client.set_value(self.device_code, address, value)

    async def _fetch(self) -> dict:
        client = await self._get_client()
        detail, sensor_params, operational_params = await asyncio.gather(
            client.get_device_detail(self.device_code),
            client.get_param_list(self.device_code, 0),
            client.get_param_list(self.device_code, 1),
        )
        return {
            "detail": detail,
            "sensors": _flatten_params(sensor_params),
            "operational": _flatten_params(operational_params),
        }
