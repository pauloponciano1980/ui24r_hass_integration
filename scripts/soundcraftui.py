#sugira docstrings para as classes abaixo, tratam-se de classes para comunicação com a mesa de som digital Soundcraft UI24R
# a interface para estes modulos são Os inputs dos instrumentos, os outputs auxiliares, e a mixagem de cada intrumento em uma saida
#este console tem 24 entradas e 10 saidas auxiliares

import logging
import websocket
import asyncio
import threading
from dataclasses import dataclass, field

UI_CMD_PREFIX = "3:::"
ALIVE = "ALIVE"
PING = "2::"

#@dataclass(frozen=True)
class UiConnection(threading.Thread):
    
    #ui_state : dict = field(default_factory=dict)
    #mixer_ip : str
    
    def __init__(self, mixer_ip):
        threading.Thread.__init__(self)
        self._ui_state = dict()
        self._mixer_ip = mixer_ip
        
    def ui_send_command(self, cmd: str):
        self.web_socket_app.send(UI_CMD_PREFIX + cmd)
        if cmd == ALIVE: return
        logging.debug(">>" + cmd)
        
    def on_message(self, web_socket_app, message: str):
        
        for line in message.split("\n"):
            
            if line == PING:
                self.ui_send_command(ALIVE)
            else:
                cmd = line.split(":")[-1]
                cmdargs = cmd.split("^")
                if cmdargs[0] in ["RTA", "VU2", "VUA", "UPDATE_PLAYLIST"]: None
                elif cmdargs[0] in ["SETD", "SETS"]:
                    k = "^".join(cmdargs[:-1])
                    v = cmdargs[-1]
                    self._ui_state[k] = v
                    logging.debug("<<" + cmd)
                else:
                    logging.warn("Unknow received message:" + cmd)

    def on_error(self, web_socket_app, error):
        logging.error(error)

    def on_close(self,web_socket_app, close_status_code, arg4):
        self._is_open=False
        logging.debug("### closed ###")

    def on_open(self, web_socket_app):
        logging.debug("Connected to the server")
        self._is_open=True
        
    def close(self):
        self.web_socket_app.keep_running = False;
        self._is_open=False
        
    async def async_run_forever(self):
        
        self._is_open = False
        self.web_socket_app = websocket.WebSocketApp(f"ws://{self._mixer_ip}:80", on_error = self.on_error, on_close = self.on_close, on_message=self.on_message,on_open=self.on_open)
        self.web_socket_app.keep_running = True
        self.wst = threading.Thread(target=self.web_socket_app.run_forever)
        self.wst.daemon = True
        self.wst.start()
        
        while not self._is_open:
            await asyncio.sleep(0.1)
        return

@dataclass(frozen=True)
class UiFaderTemplate():
    conn: UiConnection
    
    @staticmethod
    def _ui_to_float(value: str) -> float:
        return float(value)
    
    @staticmethod
    def _float_to_ui(value: float) -> str:
        return str(round(value,11))
    
    @staticmethod
    def _ui_to_bool(value: str) -> bool:
        if value == "1": return True
        elif value == "0": return False
        
    @staticmethod
    def _bool_to_ui(value: bool) -> str:
        if value == True: return "1"
        elif value == False: return "0"

    def ui_retrieve_str(self, path:str) -> str:
        ui_value = self.conn._ui_state.get(path)
        value = str(ui_value)
        return value
        
    def ui_retrieve_bool(self, path:str) -> bool:
        ui_value = self.conn._ui_state.get(path)
        value = self._ui_to_bool(ui_value)
        return value
        
    def ui_send_bool(self, path:str, value:bool) -> None:
        ui_value = self._bool_to_ui(value)
        self.conn.ui_send_command(path + "^" + ui_value)
        self.conn._ui_state[path]=value
        
    def ui_retrieve_float(self, path:str) -> float:
        ui_value = self.conn._ui_state.get(path)
        value = self._ui_to_float(ui_value)
        return value
        
    def ui_send_float(self, path:str, value:float) -> None:
        ui_value = self._float_to_ui(value)
        self.conn.ui_send_command(path + "^" + ui_value)
        self.conn._ui_state[path]=value
        
@dataclass(frozen=True)
class UiAuxFader(UiFaderTemplate):
    
    id_aux: int
        
    @property
    def unique_id(self):
        return 'aux' + str(self.id_aux)
        
    @property
    def name(self):
        path = f'SETS^a.{self.id_aux}.name'
        nm_aux = self.ui_retrieve_str(path)    
        if nm_aux == "" : nm_aux = f'AUX {str(self.id_aux)}'
        return nm_aux
        
    @property
    def volume(self):
        path = f'SETD^a.{self.id_aux}.mix'
        return self.ui_retrieve_float(path)
        
    def set_volume(self, value: float):
        path = f'SETD^a.{self.id_aux}.mix'
        self.ui_send_float(path, value)
    
    @property
    def mute(self) -> bool:
        return self.ui_retrieve_bool(f'SETD^a.{self.id_aux}.mute')
        
    def set_mute(self, mute:bool):        
        self.ui_send_bool(f'SETD^a.{self.id_aux}.mute', mute)
        
    def toggle_mute(self):
        self.set_mute(not self.mute)
    
    def __str__(self):
        return f'{self.__class__.__name__}[id_aux: {self.id_aux}, unique_id: {self.unique_id}, name: {self.name}, mute: {self.mute}, volume: {self.volume}]'

@dataclass(frozen=True)
class UiInputFader(UiFaderTemplate):
     
    id_input: int
        
    @property
    def unique_id(self):
        return 'input' + str(self.id_input)
        
    @property
    def name(self):
        nm_aux = self.ui_retrieve_str(f'SETS^i.{self.id_input}.name')
        if nm_aux == "" : nm_aux = 'CH {self.id_input}'
        return nm_aux
        
        
    @property
    def volume(self):
        return self.ui_retrieve_float(f'SETD^i.{self.id_input}.mix')
            
    def set_volume(self, value: float):
        path = f'SETD^i.{self.id_input}.mix'
        self.ui_send_float(path, value)
        
    @property
    def mute(self):
        return not self.ui_retrieve_bool(f'SETD^i.{self.id_input}.forceunmute')
        
    def set_mute(self, mute:bool):
        self.ui_send_bool(f'SETD^i.{self.id_input}.forceunmute', not mute)
        
    def toggle_mute(self):
        self.set_mute(not self.mute)
    
    def __str__(self):
        return f'{self.__class__.__name__}[id_input: {self.id_input}, unique_id: {self.unique_id}, name: {self.name}, mute: {self.mute}, volume: {self.volume}]'

@dataclass(frozen=True)
class UiInputAuxFader(UiFaderTemplate):

    id_input: int
    id_aux: int
        
    @property
    def unique_id(self) -> str:
        return 'input' + str(self.id_input) + 'aux' + str(self.id_aux)
        
    @property
    def name(self) -> str:
        
        nm_input = self.ui_retrieve_str(f'SETS^i.{self.id_input}.name')
        if nm_input == "" : nm_aux = 'CH ' + str(self.id_input)
        
        nm_aux = self.ui_retrieve_str(f'SETS^a.{self.id_aux}.name')
        if nm_aux == "" : nm_aux = 'AUX ' + str(self.id_aux)
        
        return f'{nm_input} em {nm_aux}'
        
    @property
    def volume(self) -> float:
        return self.ui_retrieve_float(f'SETD^i.{self.id_input}.aux.{self.id_aux}.value')
            
    def set_volume(self, value: float) -> None:
        path = f'SETD^i.{self.id_input}.aux.{self.id_aux}.value'
        self.ui_send_float(path, value)
        
    @property
    def mute(self) -> bool:
        return self.ui_retrieve_bool(f'SETD^i.{self.id_input}.aux.{self.id_aux}.mute')
    
    def set_mute(self, value:bool) -> None:
        self.ui_send_bool(f'SETD^i.{self.id_input}.aux.{self.id_aux}.mute', value)
        
    def toggle_mute(self) -> None:
        self.set_mute(not self.mute)
    
    def __str__(self) -> str:
        return f'{self.__class__.__name__}[id_input: {self.id_input}, id_aux: {self.id_aux}, unique_id: {self.unique_id}, name: {self.name}, mute: {self.mute}, volume: {self.volume}]'