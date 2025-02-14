import logging

from homeassistant import core
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .ui_websocket_broker import UiFloatSubject

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up numbers for Soundcraft UI integration."""
    conn = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for input_control in conn.inputs:
        entities.append(SoundcraftUINumber(conn, input_control.mix_subject, f"Input {conn.inputs.index(input_control)} Mix"))
        for aux_control in input_control.auxiliars:
            entities.append(SoundcraftUINumber(conn, aux_control.volume_subject, f"Input {conn.inputs.index(input_control)} Aux {input_control.auxiliars.index(aux_control)} Volume"))

    for aux_control in conn.auxiliars:
        entities.append(SoundcraftUINumber(conn, aux_control.volume_subject, f"Aux {conn.auxiliars.index(aux_control)} Volume"))
    async_add_entities(entities)


class SoundcraftUINumber(NumberEntity):
    """Representation of a Soundcraft UI number."""

    def __init__(self, conn, subject: UiFloatSubject, name):
        """Initialize the number."""
        self._conn = conn
        self._subject = subject
        self._attr_name = name
        self._attr_unique_id = subject.topic.replace("^", "")
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 1.0
        self._attr_native_step = 0.01
        self._attr_native_value = subject.cached

        subject.add_listener(self.async_update_state)

    async def async_set_native_value(self, value: float):
        """Set the number's value."""
        self._subject.submit(value)

    async def async_update_state(self, value):
        """Update the number's state."""
        self._attr_native_value = value
        self.async_write_ha_state()
