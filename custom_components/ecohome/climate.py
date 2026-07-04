from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EcoHomeCoordinator


def _heating_card(card_list: list) -> dict | None:
    return next((c for c in card_list if c.get("modeList") is not None), None)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: list[EcoHomeCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EcoHomeClimate(coordinator)
        for coordinator in coordinators
        if _heating_card(coordinator.data["detail"]["cardList"]) is not None
    )


class EcoHomeClimate(CoordinatorEntity[EcoHomeCoordinator], ClimateEntity):  # type: ignore[misc]
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_has_entity_name = True
    _attr_name = None  # entity name is the device alias from the app

    def __init__(self, coordinator: EcoHomeCoordinator) -> None:
        super().__init__(coordinator)
        card = _heating_card(coordinator.data["detail"]["cardList"])
        assert card is not None
        self._switch_address: str = card["switchAddress"]
        self._setting_address: str = card["settingAddress"]
        self._attr_unique_id = f"{coordinator.device_code}_heating"
        self._attr_entity_picture = coordinator.device_img_url
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_code)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=coordinator.device_model,
        )
        self._update_attrs()

    def _update_attrs(self) -> None:
        detail = self.coordinator.data["detail"]
        unit = detail.get("curUnit", "°C")
        self._attr_temperature_unit = (
            UnitOfTemperature.FAHRENHEIT if unit == "°F" else UnitOfTemperature.CELSIUS
        )
        card = _heating_card(detail["cardList"])
        if card is None:
            self._attr_hvac_mode = None
            self._attr_current_temperature = None
            self._attr_target_temperature = None
            return
        self._attr_hvac_mode = HVACMode.HEAT if card["curSwitch"] else HVACMode.OFF
        try:
            self._attr_current_temperature = float(card["curTempMain"])
        except (ValueError, TypeError):
            self._attr_current_temperature = None
        try:
            self._attr_target_temperature = float(card["settingTemp"])
        except (ValueError, TypeError):
            self._attr_target_temperature = None

    def _handle_coordinator_update(self) -> None:
        self._update_attrs()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.coordinator.async_update_switch_state(
            self._switch_address, hvac_mode == HVACMode.HEAT
        )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        if (temp := kwargs.get("temperature")) is None:
            return
        await self.coordinator.async_set_value(self._setting_address, int(temp))
        await self.coordinator.async_request_refresh()
