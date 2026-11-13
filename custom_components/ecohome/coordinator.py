import asyncio
import json
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from ecohome import AsyncEcoHomeClient, SessionExpiredError

from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    HEATING_CARD_ID,
    HOT_WATER_CARD_ID,
    ISSUE_TRACKER_URL,
    OFFLINE_ISSUE_DELAY_MINUTES,
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
        # Online state from the previous successful update; None before the first one.
        self._was_online: bool | None = None
        # When the heat pump was first seen offline in the current outage, and whether the
        # Repairs issue for that outage has been created.
        self._offline_since: datetime | None = None
        self._offline_issue_created = False

    @property
    def _offline_issue_id(self) -> str:
        return f"device_offline_{self.device_code}"

    def async_clear_issues(self) -> None:
        """Remove this device's Repairs issues, e.g. when the integration is unloaded."""
        for issue_id in {self._offline_issue_id, *self._card_mismatch_issues}:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self._card_mismatch_issues = set()
        self._offline_issue_created = False

    @property
    def online(self) -> bool:
        """Whether the cloud reported the heat pump as online in the last successful update.

        While offline, the cloud keeps serving the last known values, so they must not be shown.
        """
        return bool(self.data and self.data.get("online", True))

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
        devices, detail, sensor_params, operational_params = await asyncio.gather(
            client.list_all_devices(),
            client.get_device_detail(self.device_code),
            client.get_param_list(self.device_code, 0),
            client.get_param_list(self.device_code, 1),
        )
        self._check_card_consistency(detail)
        record = next((d for d in devices if d.get("device_code") == self.device_code), None)
        online = record is not None and record.get("device_status") != "OFFLINE"
        self._log_online_change(online, record)
        self._update_offline_issue(online)
        return {
            "online": online,
            "detail": detail,
            "sensors": _flatten_params(sensor_params),
            "operational": _flatten_params(operational_params),
        }

    def _log_online_change(self, online: bool, record: dict | None) -> None:
        """Log once when the heat pump goes offline (or is offline at startup) and when it returns."""
        previous, self._was_online = self._was_online, online
        if online == previous or (online and previous is None):
            return
        if online:
            _LOGGER.info("Heat pump %s (%s) is back online", self.device_name, self.device_code)
        elif record is None:
            _LOGGER.warning(
                "Heat pump %s (%s) is no longer in this account's device list; its entities are "
                "unavailable until it is listed again",
                self.device_name,
                self.device_code,
            )
        else:
            _LOGGER.warning(
                "Heat pump %s (%s) is offline according to the Eco-Home cloud; its entities are "
                "unavailable until it is back online. Check the heat pump's network connection",
                self.device_name,
                self.device_code,
            )

    def _update_offline_issue(self, online: bool) -> None:
        """Show a Repairs issue once the heat pump has been offline for a while; remove it when back."""
        if online:
            if self._offline_issue_created:
                ir.async_delete_issue(self.hass, DOMAIN, self._offline_issue_id)
            self._offline_since = None
            self._offline_issue_created = False
            return

        now = dt_util.utcnow()
        if self._offline_since is None:
            self._offline_since = now
        delay = timedelta(minutes=OFFLINE_ISSUE_DELAY_MINUTES)
        if self._offline_issue_created or now - self._offline_since < delay:
            return

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._offline_issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="device_offline",
            translation_placeholders={
                "device_name": self.device_name,
                "device_code": self.device_code,
                "offline_since": dt_util.as_local(self._offline_since).strftime("%Y-%m-%d %H:%M"),
                "minutes": str(OFFLINE_ISSUE_DELAY_MINUTES),
            },
        )
        self._offline_issue_created = True

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
