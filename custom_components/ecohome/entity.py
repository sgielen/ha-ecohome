from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import WIDE_MAX_TEMP, WIDE_MIN_TEMP
from .coordinator import EcoHomeCoordinator

CardFinder = Callable[[list[dict[str, Any]]], dict[str, Any] | None]


class EcoHomeEntity(CoordinatorEntity[EcoHomeCoordinator]):
    """Entity showing heat pump data; unavailable while the heat pump is offline."""

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online


def card_list(coordinator: EcoHomeCoordinator) -> list[dict[str, Any]]:
    """Return the device's card list, or an empty list when the API has none (e.g. offline)."""
    return coordinator.data["detail"].get("cardList") or []


def card_temperature_range(card: dict[str, Any]) -> tuple[float, float]:
    """Return the target temperature range the device reports for a card, or a wide one if invalid."""
    try:
        low, high = float(card["lowerTemp"]), float(card["upperTemp"])
    except (KeyError, TypeError, ValueError):
        return WIDE_MIN_TEMP, WIDE_MAX_TEMP
    if low > high:
        return WIDE_MIN_TEMP, WIDE_MAX_TEMP
    return low, high


def card_temperature_step(card: dict[str, Any]) -> float:
    """Return the target temperature step the device reports for a card, or 1 if invalid."""
    try:
        step = float(card["stepLength"])
    except (KeyError, TypeError, ValueError):
        return 1.0
    return step if step > 0 else 1.0


@callback
def async_add_entity_when_card_present(
    entry: ConfigEntry,
    coordinator: EcoHomeCoordinator,
    find_card: CardFinder,
    create_entity: Callable[[EcoHomeCoordinator], Entity],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the entity now if its card is present, otherwise as soon as a coordinator update has it.

    When the heat pump has been offline for a while the API returns no cards. Without this, a
    Home Assistant restart during an outage would leave the entity missing until a manual reload.
    """
    if find_card(card_list(coordinator)) is not None:
        async_add_entities([create_entity(coordinator)])
        return

    unsubscribe: CALLBACK_TYPE | None = None

    @callback
    def _async_check_card() -> None:
        nonlocal unsubscribe
        if unsubscribe is None or find_card(card_list(coordinator)) is None:
            return
        unsubscribe()
        unsubscribe = None
        async_add_entities([create_entity(coordinator)])

    @callback
    def _async_on_unload() -> None:
        if unsubscribe is not None:
            unsubscribe()

    unsubscribe = coordinator.async_add_listener(_async_check_card)
    entry.async_on_unload(_async_on_unload)
