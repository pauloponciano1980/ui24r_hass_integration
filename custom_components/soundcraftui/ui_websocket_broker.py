import logging
import threading
from  websocket import WebSocketApp
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar
import asyncio
import logging

_LOGGER = logging.getLogger("soundcraftui")
T = TypeVar('T')

class UiPaths:
    VU2 = "VU2^"
    RTA = "RTA^"
    VUA = "VUA^"
    SETD_I_0_A_1_MUTE = "SETD^i.{}.a.{}.mute^"
    SETD_I_0_A_1_VALUE = "SETD^i.{}.a.{}.value^"

    SETS_I_0_NAME = "SETS^i.{}.name^"
    SETD_I_0_FORCEUNMUTE = "SETD^i.{}.forceunmute^"
    SETD_I_0_MIX = "SETD^i.{}.mix^"
    SETD_I_0_STEREO_INDEX = "SETD^i.{}.stereoIndex^"

    SETS_A_0_NAME = "SETS^a.{}.name^"
    SETD_A_0_MUTE = "SETD^a.{}.mute^"
    SETD_A_0_MIX = "SETD^a.{}.mix^"

@dataclass
class UiSubject(Generic[T]):
    
    #WRITER
    send_message: Callable[[str], None] = field(repr=False)
    topic: str = field(repr=True)
    pre_submit: Callable[[T], bool] = field(default=None)
    post_submit: Callable[[T], None] = field(default=None)
    @abstractmethod
    def serialize_value(self, value: T) -> str:
        raise NotImplementedError

    def submit(self, value: T) -> None:
        if not self.pre_submit is None:
            self.pre_submit(value)
        ui_value = self.serialize_value(value)
        self.send_message(self.topic+ui_value)
        self.cached = value

        if not self.post_submit is None: 
            self.post_submit(value)

    #READER
    cached: T = field(default=None)
    listeners: list[Callable[[T], None]] = field(default_factory=list)

    @abstractmethod
    def deserialize_value(self, ui_value: str) -> T:
        raise NotImplementedError

    def add_listener(self, listener: Callable[[T], None]) -> None:
        self.listeners.append(listener)

    def _notify_listeners(self, value: T) -> None:
        for listener in self.listeners:
            if listener(value) == True:
                _LOGGER.debug("stop_propagation")
                return

    def _reiceve_value(self, ui_value: str) -> None:
        value: T = self.deserialize_value(ui_value)
        self.cached = value
        self._notify_listeners(value)

@dataclass
class UiStrSubject(UiSubject[str]):
    def serialize_value(self, value: str) -> str:
        return value

    def deserialize_value(self, ui_value: str) -> str:
        return ui_value

@dataclass
class UiBoolSubject(UiSubject[bool]):
    def serialize_value(self, value: bool) -> str:
        if value == True:
            return "1"
        elif value == False:
            return "0"
        else:
            _LOGGER.error("Valor {} não é boleano".format(value))
            return "0"

    def deserialize_value(self, ui_value: str) -> bool:
        if ui_value == "1":
            return True
        elif ui_value == "0":
            return False
        else:
            _LOGGER.error("Valor {} não pode ser convertido para booleano".format(ui_value))
            return False
@dataclass
class UiIntSubject(UiSubject[int]):
    def serialize_value(self, value: int) -> str:
        return str(value)

    def deserialize_value(self, ui_value: str) -> int:
        return int(ui_value)
    
@dataclass
class UiFloatSubject(UiSubject[float]):
    def serialize_value(self, value: float) -> str:
        if value > 1.0:
            _LOGGER.warning("Valor {} não pode ser maior que 1".format(value))
            value = 1
        if value < 0.0:
            _LOGGER.warning("Valor {} não pode ser menor que 0".format(value))
            value = 0
        return str(value)

    def deserialize_value(self, ui_value: str) -> float:
        return float(ui_value)

@dataclass
class UiInputAuxiliarControl:
    volume_subject: UiFloatSubject
    mute_subject:UiBoolSubject

@dataclass
class UiInputControl:
    name_subject:UiStrSubject
    mix_subject:UiFloatSubject
    forceunmute_subject:UiBoolSubject
    stereo_index_subject:UiBoolSubject
    auxiliars:list[UiInputAuxiliarControl]

@dataclass
class UiAuxiliarControl:
    name_subject:UiStrSubject
    volume_subject:UiFloatSubject
    mute_subject:UiBoolSubject

class UiBroker():

    def __init__(self, ui_send_command:Callable[[str],None], nr_inputs:int=24, nr_auxs:int=10):
        #UiConsoleBroker.__init__(self)
        self._subjects = {}
        self._inputs = []
        self._auxiliars = []
        for id_input in range(0, nr_inputs):
            input_auxiliars = []
            for id_auxiliar in range(0, nr_auxs):
                
                input_aux_mute_topic = UiPaths.SETD_I_0_A_1_MUTE.format(id_input, id_auxiliar)
                input_aux_mute_subject = UiBoolSubject(send_message=self.ui_send_command, topic=input_aux_mute_topic)
                self._subjects[input_aux_mute_topic] = input_aux_mute_subject

                input_aux_value_topic = UiPaths.SETD_I_0_A_1_VALUE.format(id_input, id_auxiliar)
                input_aux_value_subject = UiFloatSubject(send_message=self.ui_send_command, topic=input_aux_value_topic)
                self._subjects[input_aux_value_topic] = input_aux_value_subject

                input_auxiliar = UiInputAuxiliarControl(mute_subject=input_aux_mute_subject, volume_subject=input_aux_value_subject)
                input_auxiliars.append(input_auxiliar)

            input_name_topic = UiPaths.SETS_I_0_NAME.format(id_input)
            input_name_subject = UiStrSubject(send_message=self.ui_send_command, topic=input_name_topic)
            self._subjects[input_name_topic] = input_name_subject

            input_mix_topic = UiPaths.SETD_I_0_MIX.format(id_input)
            input_mix_subject = UiFloatSubject(send_message=self.ui_send_command, topic=input_mix_topic)
            self._subjects[input_mix_topic] = input_mix_subject

            input_stereo_index_topic = UiPaths.SETD_I_0_STEREO_INDEX.format(id_input)
            input_stereo_index_subject = UiIntSubject(send_message=self.ui_send_command, topic=input_stereo_index_topic, cached=-1)
            self._subjects[input_stereo_index_topic] = input_stereo_index_subject

            input_forceunmute_topic = UiPaths.SETD_I_0_FORCEUNMUTE.format(id_input)
            input_forceunmute_subject = UiBoolSubject(send_message=self.ui_send_command, topic=input_forceunmute_topic)
            self._subjects[input_forceunmute_topic] = input_forceunmute_subject

            input = UiInputControl(auxiliars=input_auxiliars, name_subject=input_name_subject, mix_subject=input_mix_subject, forceunmute_subject=input_forceunmute_subject, stereo_index_subject=input_stereo_index_subject)
            self._inputs.append(input)

        for id_auxiliar in range(0, nr_auxs):
            
            auxiliar_name_topic = UiPaths.SETS_A_0_NAME.format(id_auxiliar)
            auxiliar_name_subject = UiStrSubject(send_message=self.ui_send_command, topic=auxiliar_name_topic)
            self._subjects[auxiliar_name_topic] = auxiliar_name_subject

            auxiliar_volume_topic = UiPaths.SETD_A_0_MIX.format(id_auxiliar)
            auxiliar_volume_subject = UiFloatSubject(send_message=self.ui_send_command, topic=input_aux_value_topic)
            self._subjects[auxiliar_volume_topic] = auxiliar_volume_subject

            auxiliar_mute_topic = UiPaths.SETD_A_0_MUTE.format(id_auxiliar)
            auxiliar_mute_subject = UiBoolSubject(send_message=self.ui_send_command, topic=auxiliar_mute_topic)
            self._subjects[auxiliar_mute_topic] = auxiliar_mute_subject

            auxiliar = UiAuxiliarControl(
                volume_subject=auxiliar_volume_subject, 
                name_subject=auxiliar_name_subject, 
                mute_subject=auxiliar_mute_subject
            )
            self._auxiliars.append(auxiliar)

        vu2_topic = UiPaths.VU2
        vu2_subject = UiStrSubject(send_message=self.ui_send_command, topic=vu2_topic)
        self._subjects[vu2_topic] = vu2_subject
        self.vu2_subject=vu2_subject

        rta_topic = UiPaths.RTA
        rta_subject = UiStrSubject(send_message=self.ui_send_command, topic=rta_topic)
        self._subjects[rta_topic] = rta_subject
        self.rta_subject=rta_subject


        vua_topic = UiPaths.VUA
        vua_subject = UiStrSubject(send_message=self.ui_send_command, topic=vua_topic)
        self._subjects[vua_topic] = vua_subject
        self.vua_subject=vua_subject

        for id_input, input in enumerate(self._inputs):
            input.mix_subject.post_submit = lambda value, id_input=id_input: self.input_mix_post_submit(value, id_input)
            input.forceunmute_subject.post_submit = lambda value, id_input=id_input: self.input_forceunmute_post_submit(value, id_input)

    def input_mix_post_submit(self, value, id_input):
        id_input_link = self._inputs[id_input].stereo_index_subject.cached
        if id_input_link == -1:
            return
        if self.inputs[id_input_link].mix_subject.cached == value: 
            return
        self.inputs[id_input_link].mix_subject.submit(value)
        self.inputs[id_input_link].mix_subject._notify_listeners(value)

    def input_forceunmute_post_submit(self, value, id_input):
        id_input_link = self.inputs[id_input].stereo_index_subject.cached
        if id_input_link == -1:
            return
        if self.inputs[id_input_link].forceunmute_subject.cached == value: 
            return
        self.inputs[id_input_link].forceunmute_subject.submit(value)
        self.inputs[id_input_link].forceunmute_subject._notify_listeners(value)
        
    @property
    def inputs(self) -> tuple[UiInputControl]:
        return tuple(self._inputs)
    
    @property
    def auxiliars(self) -> tuple[UiAuxiliarControl]:
        return tuple(self._auxiliars)

    def on_ui_command(self, message: str):
        
        topic = next(filter(lambda topic, message=message : message.startswith(topic), self._subjects.keys()),None)
        if topic not in [UiPaths.VU2, UiPaths.RTA, UiPaths.VUA]: 
            _LOGGER.debug("<< {}".format(message))
        if topic is None: 
            _LOGGER.debug("nenhum tópico encontrato para {}".format(message))
            return
        
        subject:UiSubject = self._subjects[topic]
        ui_value = message[len(topic):]

        subject._reiceve_value(ui_value)



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
    from ui_desktop import UiDesktop
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
