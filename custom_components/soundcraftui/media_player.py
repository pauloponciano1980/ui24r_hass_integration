"""Platform for light integration."""
from __future__ import annotations

import logging
import math
from .soundcraftui import SoundcraftuiInstance, UiAuxFader, UiInputFader, UiInputAuxFader
import voluptuous as vol
from pprint import pformat
import asyncio
#import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.media_player import (PLATFORM_SCHEMA, MediaPlayerEntity, MediaPlayerEntityFeature,MediaPlayerState, MediaPlayerDeviceClass)
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import time
_LOGGER = logging.getLogger("soundcraftui")

DOMAIN="media_player"

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
    
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    
    conn=SoundcraftuiInstance(mixer_ip=config[CONF_IP_ADDRESS])
   
    #ui_aux_fader = UiAuxFader(conn = conn, id_aux = 3)
    
    ui_input1_fader = UiInputFader(conn = conn, id_input = 4)
    ui_input2_fader = UiInputFader(conn = conn, id_input = 5)
    
    #ui_input_aux_fader = UiInputAuxFader(conn = conn, id_input = 4, id_aux = 3)
    
    conn.async_run_forever()    
    add_entities([SoundcraftuiLight(ui_input1_fader), SoundcraftuiLight(ui_input2_fader)])

class SoundcraftuiLight(MediaPlayerEntity):
    """Reppresentation of an Soundcraftui Light."""
    
    def __init__(self, ui_fader) -> None:
        """Initialize an SoundcraftuiLight."""
        self._volume_step = 0.05
        self._ui_fader = ui_fader

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._ui_fader.unique_id}"
        
    @property
    def name(self) -> str:
        """Return the display name of this light"""
        return self._ui_fader.name
        
    @property
    def force_refresh (self) -> bool:
        return True
    
    @property
    def icon(self) -> str | None:
        if self._ui_fader.mute: return "mdi:volume-mute"
        if self._ui_fader.volume >= 0.70: return "mdi:volume-high"
        if self._ui_fader.volume >= 0.40: return "mdi:volume-medium"        
        return "mdi:volume-low"


    @property
    def device_class(self):
        return MediaPlayerDeviceClass.SPEAKER
        
    @property
    def state(self):
        return MediaPlayerState.ON

    @property
    def supported_features(self) :
        return MediaPlayerEntityFeature.VOLUME_SET| MediaPlayerEntityFeature.VOLUME_MUTE |MediaPlayerEntityFeature.VOLUME_STEP

    @property
    def volume_step(self) -> float:
        return self._volume_step
        
    @volume_step.setter
    def set_volume_step(self, volume_step:float) -> None:
        self._volume_step = volume_step

    @property
    def volume_level(self) -> float:
        return self._ui_fader.volume

    def set_volume_level(self, volume_level):
        self._ui_fader.set_volume(float(volume_level))

    @property
    def is_volume_muted(self) -> bool:
        """Return true if light is on."""
        return self._ui_fader.mute
        
    def mute_volume(self, mute) -> None:
        
        self._ui_fader.set_mute(mute)
        
    def unmute_volume(self) -> None:
        self._ui_fader.set_mute(False)
        
        
    async def async_update(self):
        # Aqui você coloca o código de atualização
        print("Atualizando...")

    async def _async_update_loop(self):
        while True:
            await self.async_update()
            await asyncio.sleep(1)

    async def async_added_to_hass(self):
        self.hass.loop.create_task(self._async_update_loop())
    