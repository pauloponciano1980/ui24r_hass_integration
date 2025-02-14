import logging
import threading
from  websocket import WebSocketApp
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from ui_desktop import UiDesktop
from ui_broker import UiBroker

UI_CMD_PREFIX = "3:::"
ALIVE = "ALIVE"
PING = "2::"

_LOGGER = logging.getLogger("ui_websocket_broker")

class SoundcraftuiInstance(WebSocketApp, UiBroker):
    
    def __init__(self, url:str):
        UiBroker.__init__(self, ui_send_command=self.ui_send_command)
        WebSocketApp.__init__(self, url=url, on_error = self.on_error, on_close = self.on_close, on_message=self.on_message,on_open=self.on_open)

    def on_message(self, web_socket_app, message: str):
        for line in message.split("\n"):
            
            if line == PING:
                self.ui_send_command(ALIVE)
            else:
                cmd = line.split(":")[-1]
                self.on_ui_command(cmd)

    def ui_send_command(self, cmd: str):
        self.send(UI_CMD_PREFIX + cmd)
        if cmd == ALIVE: return
        _LOGGER.debug(">>" + cmd)

    def on_error(self, web_socket_app, error):
        _LOGGER.info(f"on_error(web_socket_app, {error})")

    def on_close(self,web_socket_app, close_status_code, close_msg):
        _LOGGER.info(f"on_close(web_socket_app, {close_status_code}, {close_msg})")

    def on_open(self, web_socket_app):
        _LOGGER.info(f"on_open(web_socket_app)")

def main():
    MIXER_IP = "192.168.15.103"
    MIXER_PORT = "80"
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    conn = SoundcraftuiInstance(url=f"ws://{MIXER_IP}:{MIXER_PORT}")

    ui_desktop = UiDesktop(conn)
    wst = threading.Thread(target=conn.run_forever)
    wst.daemon = True
    wst.start()
    ui_desktop.run_forever()
    conn.close()
if __name__ == "__main__":
    main()
