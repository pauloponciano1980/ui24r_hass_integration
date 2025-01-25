import asyncio
import logging

class SoundcraftuiInstance:
    
    def __init__(self, mac: str) -> None:
        self._mac = mac
        self._is_on = True
        self._brightness = 1
    
    @property
    def is_on(self):
        return self._is_on
        
    @property
    def brightness(self):
        logging.error(f"get_brightness:{self._brightness}")
        return self._brightness
        
    async def set_brightness(self, intensity: int):
        self._brightness = intensity
        logging.error(f"set_brightness:{self._brightness}")
        
    async def turn_on(self):
        self._is_on = True
        
    async def turn_off(self):
        self._is_on = False
    