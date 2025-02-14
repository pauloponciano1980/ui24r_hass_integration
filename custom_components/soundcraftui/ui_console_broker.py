
from pynput.keyboard import Listener as KeyboardListener, Key

from ui_broker import UiPaths, UiBroker
import logging
_LOGGER = logging.getLogger("soundcraftui")

class UiConsoleBroker(UiBroker):
    def __init__(self):
        UiBroker.__init__(self, ui_send_command=self.ui_send_command)
        self._keylistener:KeyboardListener = KeyboardListener(on_press=self.on_press)
    
    def on_ui_command(self, message:str):
        _LOGGER.info(">> {}".format(message))

    def ui_send_command(self, message:str)->None:
        _LOGGER.info(">> {}".format(message))

    def on_press(self, key):
        try:
            if key is None:
                return False
            elif key == Key.esc:
                self._keylistener.stop()

            elif key.char == '1':
                self.on_ui_command(UiPaths.SETD_I_0_FORCEUNMUTE.format(0)+"1")
            elif key.char == 'q':
                self.on_ui_command(UiPaths.SETD_I_0_FORCEUNMUTE.format(0)+"0")
            elif key.char == 'a':
                self.on_ui_command(UiPaths.SETD_I_0_MIX.format(0)+"0.80")
            elif key.char == 'z':
                self.on_ui_command(UiPaths.SETD_I_0_MIX.format(0)+"0.20")

            elif key.char == '2':
                self.on_ui_command(UiPaths.SETD_I_0_FORCEUNMUTE.format(1)+"1")
            elif key.char == 'w':
                self.on_ui_command(UiPaths.SETD_I_0_FORCEUNMUTE.format(1)+"0")
            elif key.char == 's':
                self.on_ui_command(UiPaths.SETD_I_0_MIX.format(1)+"0.80")
            elif key.char == 'x':
                self.on_ui_command(UiPaths.SETD_I_0_MIX.format(1)+"0.20")

            elif key.char == '3':
                self.on_ui_command(UiPaths.SETD_I_0_FORCEUNMUTE.format(2)+"1")
            elif key.char == 'e':
                self.on_ui_command(UiPaths.SETD_I_0_FORCEUNMUTE.format(2)+"0")
            elif key.char == 'd':
                self.on_ui_command(UiPaths.SETD_I_0_MIX.format(2)+"0.80")
            elif key.char == 'c':
                self.on_ui_command(UiPaths.SETD_I_0_MIX.format(2)+"0.20")
        except AttributeError: return

    def join(self):
        self._keylistener.join()

    def start(self):
        self._keylistener.start()

