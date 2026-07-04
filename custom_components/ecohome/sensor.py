from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EcoHomeCoordinator

_UNIT_TO_DEVICE_CLASS: dict[str, SensorDeviceClass] = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "°F": SensorDeviceClass.TEMPERATURE,
    "bar": SensorDeviceClass.PRESSURE,
    "Bar": SensorDeviceClass.PRESSURE,
    "A": SensorDeviceClass.CURRENT,
    "V": SensorDeviceClass.VOLTAGE,
    "W": SensorDeviceClass.POWER,
    "kW": SensorDeviceClass.POWER,
}


def _all_params(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        address = item.get("address")
        if not address:
            continue
        unit = item.get("unit") or ""
        result.append({
            "address": address,
            "name": (item.get("pointName") or address).strip(),
            "unit": unit,
            "numeric": bool(unit),  # all numeric params in this API have a unit
        })
    return result


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: list[EcoHomeCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities: list[EcoHomeSensor] = []
    for coordinator in coordinators:
        for source in ("sensors", "operational"):
            for param in _all_params(coordinator.data[source]):
                entities.append(EcoHomeSensor(coordinator, param, source))
    async_add_entities(entities)


class EcoHomeSensor(CoordinatorEntity[EcoHomeCoordinator], SensorEntity):  # type: ignore[misc]
    _attr_has_entity_name = True

    def __init__(self, coordinator: EcoHomeCoordinator, param: dict, source: str) -> None:
        super().__init__(coordinator)
        self._address = param["address"]
        self._source = source
        unit = param["unit"] or None
        self._attr_name = param["name"]
        self._attr_unique_id = f"{coordinator.device_code}_{source}_{self._address}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = _UNIT_TO_DEVICE_CLASS.get(unit) if unit else None
        self._attr_state_class = SensorStateClass.MEASUREMENT if param["numeric"] else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_code)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=coordinator.device_model,
        )
        self._update_attrs()

    def _update_attrs(self) -> None:
        for item in self.coordinator.data[self._source]:
            if item["address"] == self._address:
                raw = item.get("addressValue")
                if raw is None or raw == "N/A":
                    self._attr_native_value = None
                    return
                try:
                    self._attr_native_value = float(raw)
                except (ValueError, TypeError):
                    self._attr_native_value = str(raw)
                return
        self._attr_native_value = None

    def _handle_coordinator_update(self) -> None:
        self._update_attrs()
        self.async_write_ha_state()
