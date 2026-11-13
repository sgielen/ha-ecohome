from collections import Counter

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER
from .coordinator import EcoHomeCoordinator
from .entity import EcoHomeEntity

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

# The API sometimes uses the single-character Unicode degree symbols; Home Assistant
# only accepts the two-character forms as valid temperature units.
_UNIT_ALIASES: dict[str, str] = {
    "\u2103": "°C",  # ℃
    "\u2109": "°F",  # ℉
}


def _all_params(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        address = item.get("address")
        if not address:
            continue
        unit = item.get("unit") or ""
        unit = _UNIT_ALIASES.get(unit, unit)
        result.append({
            "address": address,
            "name": (item.get("pointName") or address).strip(),
            "unit": unit,
            "numeric": bool(unit),  # all numeric params in this API have a unit
        })
    return result


def _disambiguate_names(params: list[dict]) -> None:
    """Add the address to names that occur more than once on a device, so the entities can be told apart.

    In some languages the API gives different parameters the same name; in French, for example, both
    the room and the outdoor temperature are called "Température ambiante".
    """
    counts = Counter(param["name"] for param in params)
    for param in params:
        if counts[param["name"]] > 1:
            param["name"] = f"{param['name']} ({param['address']})"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: list[EcoHomeCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities: list[EcoHomeSensor] = []
    for coordinator in coordinators:
        params = [
            (source, param)
            for source in ("sensors", "operational")
            for param in _all_params(coordinator.data[source])
        ]
        _disambiguate_names([param for _, param in params])
        entities.extend(EcoHomeSensor(coordinator, param, source) for source, param in params)
    async_add_entities(entities)


class EcoHomeSensor(EcoHomeEntity, SensorEntity):  # type: ignore[misc]
    _attr_has_entity_name = True

    def __init__(self, coordinator: EcoHomeCoordinator, param: dict, source: str) -> None:
        super().__init__(coordinator)
        self._address = param["address"]
        self._source = source
        self._numeric = param["numeric"]
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
                if raw is None or raw in ("", "N/A"):
                    self._attr_native_value = None
                    return
                try:
                    self._attr_native_value = float(raw)
                except (ValueError, TypeError):
                    # Numeric sensors must never get a string state; HA raises on it.
                    self._attr_native_value = None if self._numeric else str(raw)
                return
        self._attr_native_value = None

    def _handle_coordinator_update(self) -> None:
        self._update_attrs()
        self.async_write_ha_state()
