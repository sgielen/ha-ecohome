import asyncio
import json
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ecohome import AsyncEcoHomeClient, SessionExpiredError

from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    HEATING_CARD_ID,
    HOT_WATER_CARD_ID,
    ISSUE_TRACKER_URL,
)

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
        # Repair issue IDs of cards whose ID contradicts their modeList, currently reported.
        self._card_mismatch_issues: set[str] = set()

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
        self._check_card_consistency(detail)
        return {
            "detail": detail,
            "sensors": _flatten_params(sensor_params),
            "operational": _flatten_params(operational_params),
        }

    def _check_card_consistency(self, detail: dict) -> None:
        """Report cards whose ID contradicts their modeList; such cards are ignored by the entities.

        Each contradiction is logged once and shown as a Repairs issue until it disappears.
        """
        cards = detail.get("cardList") or []
        current: set[str] = set()
        for card in cards:
            card_id = card.get("card")
            has_modes = card.get("modeList") is not None
            if card_id == HEATING_CARD_ID and not has_modes:
                id_kind, mode_kind = "heating", "hot water"
            elif card_id == HOT_WATER_CARD_ID and has_modes:
                id_kind, mode_kind = "hot water", "heating"
            else:
                continue

            issue_id = f"card_mismatch_{self.device_code}_{card_id}"
            current.add(issue_id)
            if issue_id in self._card_mismatch_issues:
                continue

            card_json = json.dumps(card, ensure_ascii=False, sort_keys=True)
            _LOGGER.warning(
                "Device %s (%s) reported card %r, which this integration knows as the %s card, but "
                "its modeList (%s) indicates a %s card. The card is ignored so that the wrong "
                "function is never controlled; the %s entity stays missing or unavailable until "
                "this resolves. If this persists, please report it at %s and include this log "
                "message. Card: %s. All cards: %s",
                self.device_name,
                self.device_code,
                card_id,
                id_kind,
                json.dumps(card.get("modeList"), ensure_ascii=False),
                mode_kind,
                id_kind,
                ISSUE_TRACKER_URL,
                card_json,
                json.dumps(cards, ensure_ascii=False, sort_keys=True),
            )
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="card_mismatch",
                translation_placeholders={
                    "device_name": self.device_name,
                    "device_code": self.device_code,
                    "card_id": str(card_id),
                    "id_kind": id_kind,
                    "mode_kind": mode_kind,
                    "card": card_json,
                    "issue_tracker": ISSUE_TRACKER_URL,
                },
                learn_more_url=ISSUE_TRACKER_URL,
            )

        for issue_id in self._card_mismatch_issues - current:
            _LOGGER.info("Card mismatch %s on device %s resolved", issue_id, self.device_code)
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self._card_mismatch_issues = current
