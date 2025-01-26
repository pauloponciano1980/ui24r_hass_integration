"""Platform for light integration."""
from __future__ import annotations

import logging
import math
from .soundcraftui import SoundcraftuiInstance, UiAuxFader, UiInputFader, UiInputAuxFader
import voluptuous as vol
from pprint import pformat

#import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA, LightEntity, ColorMode)
from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import time
_LOGGER = logging.getLogger("soundcraftui")



#### CONF_IP_ADDRESS: Final = "ip_address"
#Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string
})

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Soundcraftui Light platform."""
    #Add devices
    #_LOGGER.info(pformat(config))
    
    
    
    #MIXER_IP = "192.168.15.103"
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    
    conn=SoundcraftuiInstance(mixer_ip=config[CONF_IP_ADDRESS])
   
    #ui_aux_fader = UiAuxFader(conn = conn, id_aux = 3)
    
    ui_fader = UiInputFader(conn = conn, id_input = 4)
    
    #ui_input_aux_fader = UiInputAuxFader(conn = conn, id_input = 4, id_aux = 3)
    
    conn.async_run_forever()    
    add_entities([SoundcraftuiLight(ui_fader)])

class SoundcraftuiLight(LightEntity):
    """Reppresentation of an Soundcraftui Light."""
    
    def __init__(self, ui_fader) -> None:
        """Initialize an SoundcraftuiLight."""

        self._ui_fader = ui_fader

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._ui_fader.unique_id

    @property
    def name(self) -> str:
        """Return the display name of this light"""
        return self._ui_fader.name
    
    @property
    def icon(self) -> str | None:
        if self._ui_fader.mute: return "mdi:volume-mute"
        if self._ui_fader.volume >= 0.80: return "mdi:volume-high"
        if self._ui_fader.volume >= 0.60: return "mdi:volume-medium"        
        return "mdi:volume-low"

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self):
        return [ColorMode.BRIGHTNESS]

    @property
    def brightness(self) -> int:
        return int(self._ui_fader.volume*255)

    @brightness.setter
    def brightness(self, brightness: int) -> None:
        self._ui_fader.set_volume(brightness/255)

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return not self._ui_fader.mute
        
    def turn_on(self, **kwargs: dict) -> None:
        """Instruct the light to turn on."""
        if kwargs.get(ATTR_BRIGHTNESS): self._ui_fader.set_volume(kwargs.get(ATTR_BRIGHTNESS)/255)
        self._ui_fader.set_mute(False)
        
    def turn_off(self, **kwargs: dict) -> None:
         self._ui_fader.set_mute(True)
    
    
    