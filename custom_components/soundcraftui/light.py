"""Platform for light integration."""
from __future__ import annotations

import logging
import math
from .soundcraftui import SoundcraftuiInstance
import voluptuous as vol
from pprint import pformat

#import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (ATTR_BRIGHTNESS, PLATFORM_SCHEMA, LightEntity, ColorMode)
from homeassistant.const import CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger("soundcraftui")



#### CONF_IP_ADDRESS: Final = "ip_address"
#Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_MAC): cv.string,
})

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Soundcraftui Light platform."""
    #Add devices
    _LOGGER.info(pformat(config))
    
    light = {
        "name": config[CONF_NAME],
        "mac": config[CONF_MAC]
    }
    
    add_entities([SoundcraftuiLight(light)])
    
    

class SoundcraftuiLight(LightEntity):
    """Reppresentation of an Soundcraftui Light."""
    
    def __init__(self, light) -> None:
        """Initialize an SoundcraftuiLight."""
        _LOGGER.info(pformat(light))
        self._light = SoundcraftuiInstance(light["mac"])
        self._name = light["name"]
        self._state = None
        self._brigtness = None
        
    @property
    def name(self) -> str:
        """Return the display name of this light"""
        return self._name
    
    @property
    def icon(self) -> str | None:
        if not self._state: return "mdi:volume-mute"
        if self._brightness/255 >= 0.80: return "mdi:volume-high"
        if self._brightness/255 >= 0.60: return "mdi:volume-medium"        
        return "mdi:volume-low"
    
    @property
    def brightness(self):
        """Return the brightness of the light.
        This method is optional. Removing it indicates to Home Assistant 
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def color_mode(self):
        return ColorMode.BRIGHTNESS

    @property
    def supported_color_modes(self):
        return [ColorMode.BRIGHTNESS]
            
    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state
        
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        if kwargs.get(ATTR_BRIGHTNESS): await self._light.set_brightness(kwargs.get(ATTR_BRIGHTNESS, 255))
        await self._light.turn_on()
        
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        await self._light.turn_off()
        
    def update(self) -> None:
        """Fetch new state data for this light.
        
        This is the only method that should fetch new data f...
        """
        self._state = self._light.is_on
        self._brightness = self._light.brightness
    
    @property
    def brightness(self) -> Optional[int]:
        """Return the current brightness."""
        return self._light.brightness 
    
    