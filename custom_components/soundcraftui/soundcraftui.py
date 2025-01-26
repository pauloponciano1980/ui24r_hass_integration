#sugira docstrings para as classes abaixo, tratam-se de classes para comunicação com a mesa de som digital Soundcraft UI24R
# a interface para estes modulos são Os inputs dos instrumentos, os outputs auxiliares, e a mixagem de cada intrumento em uma saida
#este console tem 24 entradas e 10 saidas auxiliares

import logging
import websocket
import time
import threading
import asyncio
from dataclasses import dataclass, field

UI_CMD_PREFIX = "3:::"
ALIVE = "ALIVE"
PING = "2::"

log = logging.getLogger("soundcraftui")

#@dataclass(frozen=True)
class SoundcraftuiInstance(threading.Thread):
    
    def __init__(self, mixer_ip):
        threading.Thread.__init__(self)
        self._ui_state = dict()
        self._mixer_ip = mixer_ip
        
    def ui_send_command(self, cmd: str):
        self.web_socket_app.send(UI_CMD_PREFIX + cmd)
        if cmd == ALIVE: return
        log.debug(">>" + cmd)
        
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
                    log.debug("<<" + cmd)
                else:
                    log.warn("Unknow received message:" + cmd)

    def on_error(self, web_socket_app, error):
        log.error(error)

    def on_close(self,web_socket_app, close_status_code, arg4):
        log.debug("### closed ###")

    def on_open(self, web_socket_app):
        log.debug("Connected to the server")
        
    def close(self):
        self.web_socket_app.keep_running = False;
        
    def ui_wait_for_value(self, path:str) -> str:
        ASYNC_SLEEP_TIME = 1
        UI_TIMEOUT = 5
        for i in range(0, int(UI_TIMEOUT/ASYNC_SLEEP_TIME)+1):
            ui_value = self._ui_state.get(path)
            if ui_value is not None: break
            asyncio.run(asyncio.sleep(ASYNC_SLEEP_TIME))
        if ui_value is None: raise Exception(f"Timeout ao aguardar a chave {path}")
        return ui_value
    
    def async_run_forever(self):
        
        self.web_socket_app = websocket.WebSocketApp(f"ws://{self._mixer_ip}:80", on_error = self.on_error, on_close = self.on_close, on_message=self.on_message,on_open=self.on_open)
        self.web_socket_app.keep_running = True
        self.wst = threading.Thread(target=self.web_socket_app.run_forever)
        self.wst.daemon = True
        self.wst.start()
        
        model = self.ui_wait_for_value("SETS^model")

        log.info(f"Connected to {model}")
        return

@dataclass(frozen=True)
class UiFaderTemplate():
    conn: SoundcraftuiInstance
    
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
        else: raise Exception(f"Invalid value: {value}")
        
    @staticmethod
    def _bool_to_ui(value: bool) -> str:
        if value == True: return "1"
        elif value == False: return "0"
    
    def ui_retrieve_float(self, path:str) -> float:
        ui_value = self.conn.ui_wait_for_value(path)   
        value = self._ui_to_float(ui_value)
        return value
    
    def ui_retrieve_str(self, path:str) -> str:
        ui_value = self.conn.ui_wait_for_value(path)
        value = str(ui_value)
        return value
        
    def ui_retrieve_bool(self, path:str) -> bool:
        ui_value = self.conn.ui_wait_for_value(path)
        value = self._ui_to_bool(ui_value)
        return value
        
    def ui_send_bool(self, path:str, value:bool) -> None:
        ui_value = self._bool_to_ui(value)
        self.conn.ui_send_command(path + "^" + ui_value)
        self.conn._ui_state[path]=ui_value
        
    def ui_send_float(self, path:str, value:float) -> None:
        ui_value = self._float_to_ui(value)
        self.conn.ui_send_command(path + "^" + ui_value)
        self.conn._ui_state[path]=ui_value
        
@dataclass(frozen=True)
class UiAuxFader(UiFaderTemplate):
    
    id_aux: int
        
    @property
    def unique_id(self):
        return f"aux{str(self.id_aux+1)}"
        
    @property
    def name(self):
        path = f'SETS^a.{self.id_aux}.name'
        nm_aux = self.ui_retrieve_str(path)    
        if nm_aux == "" : nm_aux = f'AUX {str(self.id_aux+1)}'
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
        return f'input{str(self.id_input+1)}' 
        
    @property
    def name(self):
        nm_aux = self.ui_retrieve_str(f'SETS^i.{self.id_input}.name')
        if nm_aux == "" : nm_aux = f'CH {str(self.id_input+1)}'
        return nm_aux
        
    @property
    def volume(self):
        return self.ui_retrieve_float(f'SETD^i.{self.id_input}.mix')
            
    def set_volume(self, value: float):
        path = f'SETD^i.{self.id_input}.mix'
        self.ui_send_float(path, value)
        
    @property
    def mute(self):
        valor = self.ui_retrieve_bool(f'SETD^i.{self.id_input}.forceunmute')
        log.info(f"mute: {valor}")
        return not valor
        
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
        return f'input{str(self.id_input)}aux{str(self.id_aux)}'
        
    @property
    def name(self) -> str:
        
        nm_input = self.ui_retrieve_str(f'SETS^i.{self.id_input}.name')
        if nm_input == "" : nm_aux = 'CH ' + str(self.id_input+1)
        
        nm_aux = self.ui_retrieve_str(f'SETS^a.{self.id_aux}.name')
        if nm_aux == "" : nm_aux = 'AUX ' + str(self.id_aux+1)
        
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