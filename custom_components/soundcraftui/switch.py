import logging

from homeassistant import core
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .ui_websocket_broker import UiBoolSubject

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for Soundcraft UI integration."""
    conn = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for input_control in conn.inputs:
        entities.append(SoundcraftUISwitch(conn, input_control.forceunmute_subject, f"Input {conn.inputs.index(input_control)} Force Unmute"))
        for aux_control in input_control.auxiliars:
             entities.append(SoundcraftUISwitch(conn, aux_control.mute_subject, f"Input {conn.inputs.index(input_control)} Aux {input_control.auxiliars.index(aux_control)} Mute"))
    
    for aux_control in conn.auxiliars:
        entities.append(SoundcraftUISwitch(conn, aux_control.mute_subject, f"Aux {conn.auxiliars.index(aux_control)} Mute"))

    async_add_entities(entities)


class SoundcraftUISwitch(SwitchEntity):
    """Representation of a Soundcraft UI switch."""

    def __init__(self, conn, subject: UiBoolSubject, name):
        """Initialize the switch."""
        self._conn = conn
        self._subject = subject
        self._attr_name = name
        self._attr_unique_id = subject.topic.replace("^", "")
        self._is_on = subject.cached

        subject.add_listener(self.async_update_state)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._subject.submit(True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._subject.submit(False)

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._subject.cached

    async def async_update_state(self, value):
        """Update the switch's state."""
        self._is_on = value
        self.async_write_ha_state()
