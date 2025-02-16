"""
This module handles the websocket communication with the Soundcraft UI Series. 
It defines the data structures and logic for sending commands to and receiving 
updates from the mixer, using a broker pattern to manage different UI elements 
(inputs, auxiliaries, etc.) as subjects.
"""
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

@dataclass
class UiSubject(Generic[T]):
    
    #WRITER
    send_message: Callable[[str], None] = field(repr=False)
    topic: str = field(repr=True)
    serialize_value: Callable[[T], str]
    deserialize_value: Callable[[str], T]
    pre_submit: Callable[[T], bool] = field(default=None)
    post_submit: Callable[[T], None] = field(default=None)

    def submit(self, value: T) -> None:
        if not self.pre_submit is None:
            self.pre_submit(value)
       
        try:
             ui_value:str = self.serialize_value(value)
        except Exception as e:
            raise Exception(f"Bad value Writing on topic {self.topic}: {e}")
        self.send_message(self.topic+ui_value)
        self.cached = value

        if not self.post_submit is None: 
            self.post_submit(value)

    #READER
    cached: T = field(default=None)
    listeners: list[Callable[[T], None]] = field(default_factory=list)

    def add_listener(self, listener: Callable[[T], None]) -> None:
        self.listeners.append(listener)

    def _notify_listeners(self, value: T) -> None:
        for listener in self.listeners:
            if listener(value) == True:
                _LOGGER.debug("stop_propagation")
                return

    def _reiceve_value(self, ui_value: str) -> None:
        try:
            value: T = self.deserialize_value(ui_value)
        except ValueError as e:
            raise ValueError(f"Value Error on topic {self.topic}: {e}")

        self.cached = value
        self._notify_listeners(value)

def serialize_str(value: str) -> str:
    return value

def deserialize_str(ui_value: str) -> str:
    return ui_value

def serialize_int(value: int) -> str:
    return str(value)

def deserialize_int(ui_value: str) -> int:
    return int(ui_value)

def serialize_bool(value: bool) -> str:
    if value == True:
        return "1"
    elif value == False:
        return "0"
    raise ValueError("Valor {} não é boleano".format(value))

def deserialize_bool(ui_value: str) -> bool:
    if ui_value == "1":
        return True
    elif ui_value == "0":
        return False
    
    raise ValueError("Valor {} não pode ser convertido para booleano".format(ui_value))

def serialize_percent(value: float) -> str:
    if value > 1.0:
        raise ValueError("Valor {} não pode ser maior que 1".format(value))
        value = 1
    if value < 0.0:
        raise ValueError("Valor {} não pode ser menor que 0".format(value))
        value = 0
    return str(value)

def deserialize_percent(ui_value: str) -> float:
    return float(ui_value)

@dataclass
class UiStrSubject(UiSubject[str]):
    serialize_value: Callable[[str], str] = field(default=serialize_str)
    deserialize_value: Callable[[str], str] = field(default=deserialize_str)

@dataclass
class UiBoolSubject(UiSubject[bool]):
    serialize_value: Callable[[bool], str] = field(default=serialize_bool)
    deserialize_value: Callable[[str], bool] = field(default=deserialize_bool)
    
@dataclass
class UiIntSubject(UiSubject[int]):
    serialize_value: Callable[[int], str] = field(default=serialize_int)
    deserialize_value: Callable[[str], int] = field(default=deserialize_int)
    
@dataclass
class UiPercentSubject(UiSubject[float]):
    serialize_value: Callable[[float], str] = field(default=serialize_percent)
    deserialize_value: Callable[[str], float] = field(default=deserialize_percent)

@dataclass
class UiInputAuxiliarControl:
    volume_subject: UiPercentSubject
    mute_subject:UiBoolSubject

@dataclass
class UiInputControl:
    name_subject:UiStrSubject
    mix_subject:UiPercentSubject
    forceunmute_subject:UiBoolSubject
    stereo_index_subject:UiBoolSubject
    pan_subject:UiPercentSubject
    auxiliars:list[UiInputAuxiliarControl]

@dataclass
class UiInputFxControl:
    value_subject:UiPercentSubject
    mute_subject:UiBoolSubject
    post_subject:UiBoolSubject

@dataclass
class UiAuxiliarControl:
    name_subject:UiStrSubject
    volume_subject:UiPercentSubject
    mute_subject:UiBoolSubject

class UiBroker():

    def createSubject(self, topic:str, subject_type: type[UiSubject[T]]) -> UiSubject[T]:
        if topic in self._subjects: _LOGGER.error(f"Topico [{topic}] ja existe")
        subject = subject_type(send_message=self.ui_send_command, topic=topic)
        self._subjects[topic] = subject
        return subject

    def __init__(self, ui_send_command:Callable[[str],None], nr_inputs:int=24, nr_auxs:int=10):
        self.ui_send_command = ui_send_command

        
        self._subjects = {}
        self._inputs = []
        self._auxiliars = []
        ### GENERAL
        self.model_subject = self.createSubject("SETS^model^", UiStrSubject)
        self.firmware_subject = self.createSubject("SETS^firmware^", UiStrSubject)
        self.vu2_subject = self.createSubject("VU2^", UiStrSubject)
        self.rta_subject = self.createSubject("RTA^", UiStrSubject)
        self.vua_subject = self.createSubject("VUA^", UiStrSubject)

        self.createSubject("SETS^iso.ch^", UiStrSubject)
        self.createSubject("SETS^iso.mtx^", UiStrSubject)
        self.createSubject("SETS^iso.m^", UiStrSubject)
        self.createSubject("SETS^iso.bus^", UiStrSubject)
        self.createSubject("SETS^iso.fx^", UiStrSubject)
        self.createSubject("SETS^iso.gr^", UiStrSubject)
        self.createSubject("SETS^l.1.dyn.prname^", UiStrSubject)
        self.createSubject("SETS^l.1.gate.prname^", UiStrSubject)
        self.createSubject("SETS^l.1.iosyscmd^", UiStrSubject)
        self.createSubject("SETS^l.1.iosysname^", UiStrSubject)
        self.createSubject("SETS^l.1.instrument^", UiStrSubject)
        self.createSubject("SETS^l.1.scsrc^", UiStrSubject)
        self.createSubject("SETS^l.1.src^", UiStrSubject)
        self.createSubject("SETS^l.1.eq.prname^", UiStrSubject)
        self.createSubject("SETD^settings.maxconn^", UiIntSubject)
        self.createSubject("SETD^settings.clock^", UiBoolSubject)
        self.createSubject("SETD^settings.cascade.master^", UiBoolSubject)
        self.createSubject("SETD^settings.cascade.enabled^", UiBoolSubject)
        self.createSubject("SETD^settings.cascade.snapsync^", UiBoolSubject)
        self.createSubject("SETD^settings.block.presets^", UiBoolSubject)
        self.createSubject("SETD^settings.block.gsettings^", UiBoolSubject)
        self.createSubject("SETD^settings.demo^", UiBoolSubject)
        self.createSubject("SETD^settings.block.loadshows^", UiBoolSubject)
        self.createSubject("SETD^settings.solovol^", UiBoolSubject)
        self.createSubject("SETD^settings.mtxsendpoint^", UiBoolSubject)
        self.createSubject("SETD^settings.hpvol.1^", UiPercentSubject)
        self.createSubject("SETD^settings.block.mixgain^", UiBoolSubject)
        self.createSubject("SETD^settings.block.mixproc^", UiBoolSubject)
        self.createSubject("SETD^settings.block.mproc^", UiBoolSubject)
        self.createSubject("SETD^settings.block.mlvl^", UiBoolSubject)
        self.createSubject("SETD^settings.block.auxproc^", UiBoolSubject)
        self.createSubject("SETD^settings.block.auxlvl^", UiBoolSubject)
        self.createSubject("SETD^settings.block.shows^", UiBoolSubject)
        self.createSubject("SETD^settings.block.player^", UiBoolSubject)
        self.createSubject("SETD^settings.hpswap^", UiBoolSubject)
        self.createSubject("SETD^settings.auxmutelink^", UiBoolSubject)
        self.createSubject("SETD^settings.underscan^", UiBoolSubject)
        self.createSubject("SETD^settings.auxsendpoint^", UiBoolSubject)
        self.createSubject("SETD^settings.nophantomonboot^", UiBoolSubject)
        self.createSubject("SETD^settings.afsonboot^", UiBoolSubject)
        self.createSubject("SETD^settings.block.mixlvl^", UiBoolSubject)
        self.createSubject("SETD^settings.cascade.vcasync^", UiBoolSubject)
        self.createSubject("SETD^settings.cascade.mgsync^", UiBoolSubject)
        self.createSubject("SETD^settings.cue^", UiBoolSubject)
        self.createSubject("SETD^settings.playMode^", UiBoolSubject)
        self.createSubject("SETD^settings.footswitchfunc^", UiBoolSubject)
        self.createSubject("SETD^settings.solotype^", UiBoolSubject)
        self.createSubject("SETD^settings.recordMode^", UiIntSubject)
        self.createSubject("SETD^settings.fsmgidx^", UiBoolSubject)
        self.createSubject("SETD^settings.iosys^", UiBoolSubject)
        self.createSubject("SETD^settings.mtk.format^", UiIntSubject)
        self.createSubject("SETD^settings.player.dualmono^", UiBoolSubject)
        self.createSubject("SETD^settings.soloMode^", UiBoolSubject)
        self.createSubject("SETD^settings.multiplesolo^", UiBoolSubject)
        for id_settings_hpvol in (0,2):
            self.createSubject("SETD^settings.hpvol.{}^".format(id_settings_hpvol), UiPercentSubject)
        
        self.createSubject("SETD^mgmask^", UiIntSubject)

        self.createSubject("SETD^afs.enabled^", UiBoolSubject)
        self.createSubject("SETD^automix.time^", UiPercentSubject)
        self.createSubject("SETD^automix.a.on^", UiBoolSubject)
        self.createSubject("SETD^automix.b.on^", UiBoolSubject)

        self.createSubject("SETD^var.lig_bypass^", UiBoolSubject)
        self.createSubject("SETD^var.digitech_avoid^", UiBoolSubject)
        self.createSubject("SETD^var.nophantom^", UiBoolSubject)
        self.createSubject("SETD^var.asosec^", UiIntSubject)
        self.createSubject("SETD^var.pongtime^", UiBoolSubject)
        self.createSubject("SETD^var.footswitch^", UiBoolSubject)
        self.createSubject("SETD^var.hpaux^", UiBoolSubject)
        self.createSubject("SETD^var.rswgpio^", UiBoolSubject)
        self.createSubject("SETD^var.fswgpio^", UiBoolSubject)
        self.createSubject("SETD^var.unsaved.mutegroups^", UiBoolSubject)
        self.createSubject("SETD^var.unsaved.chsafes^", UiBoolSubject)
        self.createSubject("SETD^var.cascade.connected^", UiBoolSubject)
        self.createSubject("SETD^var.currentState^", UiBoolSubject)
        self.createSubject("SETD^var.currentLength^", UiIntSubject)
        self.createSubject("SETD^var.isRecording^", UiBoolSubject)
        self.createSubject("SETD^var.playBusy^", UiBoolSubject)
        self.createSubject("SETD^var.shuffle^", UiBoolSubject)
        self.createSubject("SETD^var.recBusy^", UiBoolSubject)
        self.createSubject("SETD^var.present^", UiBoolSubject)
        self.createSubject("SETD^var.spior^", UiBoolSubject)
        self.createSubject("SETD^var.spiec^", UiBoolSubject)
        self.createSubject("SETD^var.spimb^", UiBoolSubject)
        self.createSubject("SETD^var.spioa^", UiBoolSubject)
        self.createSubject("SETD^var.spids^", UiBoolSubject)
        self.createSubject("SETD^var.currentTrackPos^", UiBoolSubject)
        self.createSubject("SETD^var.sdram^", UiBoolSubject)
        self.createSubject("SETD^var.usbfill^", UiBoolSubject)
        self.createSubject("SETD^var.spien^", UiBoolSubject)

        self.createSubject("SETS^var.testcode^", UiStrSubject)
        self.createSubject("SETS^var.rta^", UiStrSubject)
        self.createSubject("SETD^var.mtk.rec.busy^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.rec.time^", UiIntSubject)
        self.createSubject("SETD^var.mtk.rec.currentState^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.present^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.soundcheck^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.currentLength^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.currentState^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.currentTrackPos^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.freespace^", UiIntSubject)
        self.createSubject("SETD^var.mtk.busy^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.dropouts^", UiBoolSubject)
        self.createSubject("SETD^var.mtk.bufferfill^", UiIntSubject)
        self.createSubject("SETS^var.mtk.rec.session^", UiStrSubject)
        self.createSubject("SETS^var.mtk.playsession^", UiStrSubject)

        for id_vg in range(0,6):
            self.createSubject("SETS^vg.{}.name^".format(id_vg), UiStrSubject)
            self.createSubject("SETS^vg.{}".format(id_vg), UiStrSubject)

        for id_mg in range(0,6):
            self.createSubject("SETS^mg.{}.name^".format(id_mg), UiStrSubject)

        for id_v in range(0,6):
            self.createSubject("SETS^v.{}.name^".format(id_v), UiStrSubject)
            self.createSubject("SETD^v.{}.forceunmute^".format(id_v), UiBoolSubject)
            self.createSubject("SETD^v.{}.mgmask^".format(id_v), UiBoolSubject)
            self.createSubject("SETD^v.{}.mute^".format(id_v), UiBoolSubject)
            self.createSubject("SETD^v.{}.solo^".format(id_v), UiBoolSubject)
            self.createSubject("SETD^v.{}.mix^".format(id_v), UiPercentSubject)

        for id_hwouthp in range(0,4):
            self.createSubject("SETS^hwouthp.{}.src^".format(id_hwouthp), UiStrSubject)

        for id_hwouthpdsp in range(0,4):
            self.createSubject("SETS^hwouthpdsp.{}.src^".format(id_hwouthpdsp), UiStrSubject)

        for id_casc in range(0,32):
            self.createSubject("SETS^casc.{}.src^".format(id_casc), UiStrSubject)

        for id_hwoutm in range(0,2):
            self.createSubject("SETS^hwoutm.{}.src^".format(id_hwoutm), UiStrSubject)

        for id_hwoutaux in range(0,10):
            self.createSubject("SETS^hwoutaux.{}.src^".format(id_hwoutaux), UiStrSubject)
        
        #MASTER        
        self.createSubject("SETD^m.delayR^", UiBoolSubject)
        self.createSubject("SETD^m.delayL^", UiBoolSubject)
        self.createSubject("SETD^m.r.invert^", UiBoolSubject)
        self.createSubject("SETD^m.l.invert^", UiBoolSubject)
        self.createSubject("SETD^m.pan^", UiPercentSubject)
        self.createSubject("SETD^m.mix^", UiPercentSubject)
        self.createSubject("SETD^m.dim^", UiBoolSubject)
        self.createSubject("SETD^m.safe^", UiBoolSubject)
        self.createSubject("SETD^m.afs.clearlive^", UiBoolSubject)
        self.createSubject("SETD^m.afs.clearall^", UiBoolSubject)
        self.createSubject("SETD^m.afs.livelift^", UiBoolSubject)
        self.createSubject("SETD^m.afs.clearfixed^", UiBoolSubject)
        self.createSubject("SETD^m.afs.sensitivity^", UiPercentSubject)
        self.createSubject("SETD^m.afs.enabled^", UiBoolSubject)
        self.createSubject("SETD^m.afs.fmode^", UiBoolSubject)
        self.createSubject("SETD^m.afs.numtotal^", UiIntSubject)
        self.createSubject("SETD^m.afs.cmode^", UiBoolSubject)
        self.createSubject("SETD^m.afs.logic^", UiBoolSubject)
        self.createSubject("SETD^m.afs.numfixed^", UiIntSubject)
        self.createSubject("SETD^m.gate.thresh^", UiBoolSubject)
        self.createSubject("SETD^m.gate.prmod^", UiBoolSubject)
        self.createSubject("SETD^m.gate.bypass^", UiBoolSubject)
        self.createSubject("SETD^m.gate.hold^", UiPercentSubject)
        self.createSubject("SETD^m.gate.depth^", UiBoolSubject)
        self.createSubject("SETD^m.gate.attack^", UiBoolSubject)
        self.createSubject("SETD^m.gate.release^", UiPercentSubject)
        self.createSubject("SETD^m.gate.enabled^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.l.outgain^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.l.release^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.l.gain^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.l.threshold^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.l.softknee^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.l.ratio^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.l.hold^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.l.attack^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.r.gain^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.r.ratio^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.r.threshold^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.r.hold^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.r.release^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.r.softknee^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.r.attack^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.r.outgain^", UiPercentSubject)
        self.createSubject("SETD^m.dyn.prmod^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.bypass^", UiBoolSubject)
        self.createSubject("SETD^m.dyn.linked^", UiBoolSubject)
        
        for id_mtx in range(0, 10):
            self.createSubject("SETD^m.mtx.{}.value^".format(id_mtx), UiPercentSubject)
            self.createSubject("SETD^m.mtx.{}.pan^".format(id_mtx), UiPercentSubject)
            self.createSubject("SETD^m.mtx.{}.postproc^".format(id_mtx), UiBoolSubject)
            self.createSubject("SETD^m.mtx.{}.mute^".format(id_mtx), UiBoolSubject)

        
        self.createSubject("SETD^m.eq.hpf.l^", UiBoolSubject)
        self.createSubject("SETD^m.eq.hpf.r^", UiBoolSubject)
        self.createSubject("SETD^m.eq.lpf.r^", UiBoolSubject)
        self.createSubject("SETD^m.eq.lpf.l^", UiBoolSubject)
        self.createSubject("SETD^m.eq.prmod^", UiBoolSubject)
        self.createSubject("SETD^m.eq.linked^", UiBoolSubject)
        self.createSubject("SETD^m.eq.bypass^", UiBoolSubject)
        for id_eq_peak in range(0,31):
            self.createSubject("SETD^m.eq.peak.l.{}^".format(id_eq_peak), UiPercentSubject)
            
        for id_eq_peak in range(0,31):
            self.createSubject("SETD^m.eq.peak.r.{}^".format(id_eq_peak), UiPercentSubject)

        for id_s in range(0,6):
            self.createSubject("SETS^s.{}.dyn.prname^".format(id_s), UiStrSubject)
            self.createSubject("SETS^s.{}.gate.prname^".format(id_s), UiStrSubject)
            self.createSubject("SETS^s.{}.name^".format(id_s), UiStrSubject)
            self.createSubject("SETS^s.{}.eq.prname^".format(id_s), UiStrSubject)
            self.createSubject("SETD^s.{}.dyn.bypass^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.dyn.threshold^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.dyn.prmod^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.dyn.softknee^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.dyn.attack^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.dyn.gain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.dyn.ratio^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.dyn.release^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.dyn.outgain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.gate.depth^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.gate.release^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.gate.hold^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.gate.enabled^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.gate.thresh^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.gate.attack^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.gate.prmod^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.gate.bypass^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.eq.b1.q^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b1.gain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.hpf.slope^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.eq.b1.freq^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b2.gain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b3.freq^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b2.freq^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b2.q^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b4.freq^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b4.q^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b3.q^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b3.gain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b5.q^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b5.gain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b4.gain^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.b5.freq^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.eq.easy^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.eq.hpf.freq^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.eq.prmod^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.eq.bypass^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.mute^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.forceunmute^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.mix^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.pan^".format(id_s), UiPercentSubject)
            self.createSubject("SETD^s.{}.safe^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.mgmask^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.solo^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.exclude^".format(id_s), UiBoolSubject)
            self.createSubject("SETD^s.{}.ducker^".format(id_s), UiBoolSubject)
            
            for id_mtx in range (0,10):
                self.createSubject("SETD^s.{}.mtx.{}.pan^".format(id_s, id_mtx), UiPercentSubject)
                self.createSubject("SETD^s.{}.mtx.{}.postproc^".format(id_s, id_mtx), UiBoolSubject)
                self.createSubject("SETD^s.{}.mtx.{}.value^".format(id_s, id_mtx), UiBoolSubject)
                self.createSubject("SETD^s.{}.mtx.{}.mute^".format(id_s, id_mtx), UiBoolSubject)

            for id_fx in range(0,4):
                self.createSubject("SETD^s.{}.fx.{}.mute^".format(id_s, id_fx), UiBoolSubject)
                self.createSubject("SETD^s.{}.fx.{}.post^".format(id_s, id_fx), UiBoolSubject)
                self.createSubject("SETD^s.{}.fx.{}.value^".format(id_s, id_fx), UiBoolSubject)

        for id_usbdaw in range(0, 32):
            self.createSubject("SETS^usbdaw.{}.src^".format(id_usbdaw), UiStrSubject)
            
        for id_p in range(0,2):    
            self.createSubject("SETD^p.{}.eq.b1.freq^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b1.q^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b1.gain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b2.gain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b2.freq^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b2.q^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b3.q^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b3.gain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b3.freq^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b4.gain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b4.freq^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b4.q^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b5.freq^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b5.q^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.b5.gain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.eq.prmod^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.eq.bypass^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.eq.hpf.slope^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.eq.easy^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.eq.hpf.freq^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.dyn.prmod^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.dyn.gain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.dyn.ratio^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.dyn.bypass^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.dyn.threshold^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.vca^".format(id_p), UiIntSubject)
            self.createSubject("SETD^p.{}.dyn.autogain^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.stereoIndex^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.subgroup^".format(id_p), UiIntSubject)
            self.createSubject("SETD^p.{}.pan^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.mute^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.mix^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.solo^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.safe^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.forceunmute^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.mgmask^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.dyn.release^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.dyn.outgain^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.dyn.softknee^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.dyn.attack^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.gate.prmod^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.gate.bypass^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.gate.enabled^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.gate.release^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.gate.hold^".format(id_p), UiPercentSubject)
            self.createSubject("SETD^p.{}.gate.thresh^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.gate.attack^".format(id_p), UiBoolSubject)
            self.createSubject("SETD^p.{}.gate.depth^".format(id_p), UiBoolSubject)

            for if_fx in range(0,4):
                self.createSubject("SETD^p.{}.fx.{}.mute^".format(id_p, if_fx), UiBoolSubject)
                self.createSubject("SETD^p.{}.fx.{}.post^".format(id_p, if_fx), UiBoolSubject)
                self.createSubject("SETD^p.{}.fx.{}.value^".format(id_p, if_fx), UiPercentSubject)
            for id_aux in range(0,10):
                self.createSubject("SETD^p.{}.aux.{}.post^".format(id_p, id_aux), UiBoolSubject)
                self.createSubject("SETD^p.{}.aux.{}.postproc^".format(id_p, id_aux), UiBoolSubject)
                self.createSubject("SETD^p.{}.aux.{}.value^".format(id_p, id_aux), UiPercentSubject)
                self.createSubject("SETD^p.{}.aux.{}.mute^".format(id_p, id_aux), UiBoolSubject)
                self.createSubject("SETD^p.{}.aux.{}.pan^".format(id_p, id_aux), UiBoolSubject)

        for id_l in range(0,2):                      
            self.createSubject("SETD^l.{}.eq.b1.q^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b1.freq^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b1.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b2.freq^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b2.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b2.q^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b3.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b3.q^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b3.freq^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b4.freq^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b4.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b4.q^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b5.q^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b5.freq^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.b5.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.eq.bypass^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.eq.easy^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.eq.prmod^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.eq.hpf.slope^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.eq.hpf.freq^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.dyn.bypass^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.dyn.prmod^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.dyn.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.dyn.threshold^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.dyn.softknee^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.dyn.ratio^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.dyn.release^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.dyn.attack^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.dyn.outgain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.gate.prmod^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.gate.thresh^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.gate.bypass^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.gate.release^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.gate.attack^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.gate.depth^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.gate.hold^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.gate.enabled^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.forceunmute^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.mute^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.solo^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.mgmask^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.safe^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.gain^".format(id_l), UiPercentSubject)
            self.createSubject("SETD^l.{}.invert^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.phantom^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.stereoIndex^".format(id_l), UiIntSubject)
            self.createSubject("SETD^l.{}.subgroup^".format(id_l), UiIntSubject)
            self.createSubject("SETD^l.{}.delay^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.vca^".format(id_l), UiIntSubject)
            self.createSubject("SETD^l.{}.mtkrec^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.pan^".format(id_l), UiBoolSubject)
            self.createSubject("SETD^l.{}.mix^".format(id_l), UiPercentSubject)

            for id_fx in range(0,4):
                self.createSubject("SETD^l.{}.fx.{}.value^".format(id_l, id_fx), UiPercentSubject)
                self.createSubject("SETD^l.{}.fx.{}.mute^".format(id_l, id_fx), UiBoolSubject)
                self.createSubject("SETD^l.{}.fx.{}.post^".format(id_l, id_fx), UiBoolSubject)

            for id_aux in range(0, 10):
                self.createSubject("SETD^l.{}.aux.{}.pan^".format(id_l, id_aux), UiPercentSubject)
                self.createSubject("SETD^l.{}.aux.{}.value^".format(id_l, id_aux), UiPercentSubject)
                self.createSubject("SETD^l.{}.aux.{}.postproc^".format(id_l, id_aux), UiBoolSubject)
                self.createSubject("SETD^l.{}.aux.{}.mute^".format(id_l, id_aux), UiBoolSubject)
                self.createSubject("SETD^l.{}.aux.{}.post^".format(id_l, id_aux), UiBoolSubject)

        

        for id_hw in range(0, 20):
            self.createSubject("SETD^hw.{}.gain^".format(id_hw), UiPercentSubject)
            self.createSubject("SETD^hw.{}.phantom^".format(id_hw), UiBoolSubject)
            self.createSubject("SETD^hw.{}.disablegain^".format(id_hw), UiBoolSubject)
            self.createSubject("SETD^hw.{}.hiz^".format(id_hw), UiBoolSubject)

        for id_out in range(0, 22):
            self.createSubject("SETS^mtk.out.{}^".format(id_out), UiStrSubject)

        for id_mtk_scout in range(0,22):
            self.createSubject("SETS^mtk.scout.{}^".format(id_mtk_scout), UiStrSubject)

        for id_input in range(0, nr_inputs):
            input_auxiliars = []
            for id_auxiliar in range(0, nr_auxs):
                input_auxiliar = UiInputAuxiliarControl(
                    mute_subject = self.createSubject("SETD^i.{}.a.{}.mute^".format(id_input, id_auxiliar), UiBoolSubject), 
                    volume_subject = self.createSubject("SETD^i.{}.a.{}.value^".format(id_input, id_auxiliar), UiPercentSubject)
                )

                # BEGIN: VALIDAR
                self.createSubject("SETD^i.{}.aux.{}.value^".format(id_input, id_auxiliar), UiPercentSubject)
                self.createSubject("SETD^i.{}.aux.{}.pan^".format(id_input, id_auxiliar), UiPercentSubject)
                self.createSubject("SETD^i.{}.aux.{}.post^".format(id_input, id_auxiliar), UiBoolSubject)
                self.createSubject("SETD^i.{}.aux.{}.mute^".format(id_input, id_auxiliar), UiBoolSubject)
                self.createSubject("SETD^i.{}.aux.{}.postproc^".format(id_input, id_auxiliar), UiBoolSubject)
                # END: VALIDAR
                input_auxiliars.append(input_auxiliar)

            input_fxs = []
            for id_fx in range(0,4):
                input_fx = UiInputFxControl(
                    value_subject = self.createSubject("SETD^i.{}.fx.{}.value^".format(id_input, id_fx), UiPercentSubject), 
                    mute_subject = self.createSubject("SETD^i.{}.fx.{}.mute^".format(id_input, id_fx), UiBoolSubject), 
                    post_subject = self.createSubject("SETD^i.{}.fx.{}.post^".format(id_input, id_fx), UiBoolSubject), 
                )
                input_fxs.append(input_fx)
            input = UiInputControl(
                auxiliars = input_auxiliars, 
                name_subject = self.createSubject("SETS^i.{}.name^".format(id_input), UiStrSubject), 
                mix_subject = self.createSubject("SETD^i.{}.mix^".format(id_input), UiPercentSubject), 
                forceunmute_subject = self.createSubject("SETD^i.{}.forceunmute^".format(id_input), UiBoolSubject), 
                stereo_index_subject = self.createSubject("SETD^i.{}.stereoIndex^".format(id_input), UiIntSubject),
                pan_subject = self.createSubject("SETD^i.{}.pan^".format(id_input), UiPercentSubject),
            )
            ## BEGIN: NAO UTILIZAR
            self.createSubject("SETD^i.{}.mute^".format(id_input), UiStrSubject) 
            ## END: NAO UTILIZAR

            ## BEGIN: EM ANALISE
            self.createSubject("SETS^i.{}.iosysname^".format(id_input), UiStrSubject)
            self.createSubject("SETS^i.{}.iosyscmd^".format(id_input), UiStrSubject)
            self.createSubject("SETS^i.{}.scsrc^".format(id_input), UiStrSubject)
            self.createSubject("SETS^i.{}.src^".format(id_input), UiStrSubject)
            self.createSubject("SETS^i.{}.instrument^".format(id_input), UiStrSubject) 
            self.createSubject("SETS^i.{}.gate.prname^".format(id_input), UiStrSubject)
            self.createSubject("SETS^i.{}.eq.prname^".format(id_input), UiStrSubject) 
            self.createSubject("SETS^i.{}.dyn.prname^".format(id_input), UiStrSubject)
            self.createSubject("SETD^i.{}.eq.b1.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b1.q^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b1.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b2.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b2.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b2.q^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b3.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b3.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b3.q^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b4.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b4.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b4.q^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b5.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b5.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.b5.q^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.hpf.slope^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.eq.hpf.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.eq.prmod^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.eq.easy^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.eq.lpf.slope^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.eq.lpf.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.digitech.cab^".format(id_input), UiIntSubject) 
            self.createSubject("SETD^i.{}.digitech.amp^".format(id_input), UiIntSubject) 
            self.createSubject("SETD^i.{}.digitech.mid^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.digitech.treble^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.digitech.level^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.digitech.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.digitech.bass^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.digitech.enabled^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.deesser.threshold^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.deesser.ratio^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.deesser.enabled^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.deesser.freq^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.attack^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.softknee^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.dyn.outgain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.release^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.threshold^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.bypass^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.dyn.ratio^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.gain^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.dyn.prmod^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.gate.attack^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.gate.thresh^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.gate.hold^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.gate.release^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.gate.enabled^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.gate.bypass^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.gate.prmod^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.gate.depth^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.eq.bypass^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.hiz^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.amix^".format(id_input), UiPercentSubject) 
            self.createSubject("SETD^i.{}.amixgroup^".format(id_input), UiIntSubject) 
            self.createSubject("SETD^i.{}.mtkrec^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.exclude^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.phantom^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.invert^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.disablegain^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.gain^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.safe^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.solo^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.mgmask^".format(id_input), UiIntSubject) 
            self.createSubject("SETD^i.{}.vca^".format(id_input), UiIntSubject) 
            self.createSubject("SETD^i.{}.delay^".format(id_input), UiBoolSubject) 
            self.createSubject("SETD^i.{}.color^".format(id_input), UiIntSubject) 
            self.createSubject("SETD^i.{}.subgroup^".format(id_input), UiIntSubject) 
            ## END: EM ANALISE
            self._inputs.append(input)

        for id_auxiliar in range(0, nr_auxs):

            for id_eq_peak in range(0, 31):
                self.createSubject("SETD^a.{}.eq.peak.{}^".format(id_auxiliar, id_eq_peak), UiStrSubject)

            for id_aux_afs_eq in range(0,12):
                self.createSubject("SETS^a.{}.afs.eq.{}^".format(id_auxiliar, id_aux_afs_eq), UiStrSubject)

            for id_mtx in range(0,10):
                self.createSubject("SETD^a.{}.mtx.{}.pan^".format(id_auxiliar, id_mtx), UiPercentSubject)
                self.createSubject("SETD^a.{}.mtx.{}.mute^".format(id_auxiliar, id_mtx), UiBoolSubject)
                self.createSubject("SETD^a.{}.mtx.{}.value^".format(id_auxiliar, id_mtx), UiBoolSubject)
                self.createSubject("SETD^a.{}.mtx.{}.postproc^".format(id_auxiliar, id_mtx), UiBoolSubject)

            auxiliar = UiAuxiliarControl(
                name_subject = self.createSubject("SETS^a.{}.name^".format(id_auxiliar), UiStrSubject), 
                volume_subject = self.createSubject("SETD^a.{}.mix^".format(id_auxiliar), UiPercentSubject), 
                mute_subject = self.createSubject("SETD^a.{}.mute^".format(id_auxiliar), UiBoolSubject)
            )
            self._auxiliars.append(auxiliar)

            ## BEGIN: ANALISAR
            self.createSubject("SETS^a.{}.gate.prname^".format(id_auxiliar), UiStrSubject)
            self.createSubject("SETS^a.{}.eq.prname^".format(id_auxiliar), UiStrSubject)
            self.createSubject("SETS^a.{}.dyn.prname^".format(id_auxiliar), UiStrSubject) 
            self.createSubject("SETD^a.{}.afs.enabled^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.cmode^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.fmode^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.numfixed^".format(id_auxiliar), UiIntSubject)
            self.createSubject("SETD^a.{}.afs.numtotal^".format(id_auxiliar), UiIntSubject)
            self.createSubject("SETD^a.{}.afs.clearall^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.logic^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.clearfixed^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.clearlive^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.afs.sensitivity^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.afs.livelift^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.dyn.prmod^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.dyn.threshold^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.dyn.bypass^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.dyn.ratio^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.dyn.gain^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.dyn.attack^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.dyn.softknee^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.dyn.outgain^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.dyn.release^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.gate.enabled^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.gate.bypass^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.gate.prmod^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.gate.attack^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.gate.thresh^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.gate.hold^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.gate.release^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.gate.depth^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.pan^".format(id_auxiliar), UiPercentSubject)
            self.createSubject("SETD^a.{}.forceunmute^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.solo^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.mgmask^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.stereoIndex^".format(id_auxiliar), UiIntSubject)
            self.createSubject("SETD^a.{}.safe^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.link2master^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.delay^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.vca^".format(id_auxiliar), UiIntSubject)
            self.createSubject("SETD^a.{}.matrix^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.invert^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.eq.lpf^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.eq.hpf^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.eq.bypass^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.eq.prmod^".format(id_auxiliar), UiBoolSubject)
            self.createSubject("SETD^a.{}.eq.linked^".format(id_auxiliar), UiBoolSubject)
            ## END: ANALISAR

        ### FX
        for id_fx in range(0, 4):
            self.createSubject("SETS^f.{}.name^".format(id_fx), UiStrSubject)
            self.createSubject("SETS^f.{}.dyn.prname^".format(id_fx), UiStrSubject)
            self.createSubject("SETS^f.{}.gate.prname^".format(id_fx), UiStrSubject)
            self.createSubject("SETS^f.{}.prname^".format(id_fx), UiStrSubject)
            self.createSubject("SETD^f.{}.pan^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.mute^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.mix^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.solo^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.safe^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.forceunmute^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.mgmask^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.smix^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.subgroup^".format(id_fx), UiIntSubject)
            self.createSubject("SETD^f.{}.span^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.dyn.release^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.dyn.outgain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.dyn.softknee^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.dyn.attack^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.gate.prmod^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.gate.bypass^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.gate.enabled^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.gate.release^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.gate.hold^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.gate.thresh^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.gate.attack^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.gate.depth^".format(id_fx), UiBoolSubject)

            self.createSubject("SETS^f.{}.eq.prname^".format(id_fx), UiStrSubject)  
            self.createSubject("SETD^f.{}.eq.b1.freq^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b1.q^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b1.gain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b2.gain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b2.freq^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b2.q^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b3.q^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b3.gain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b3.freq^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b4.gain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b4.freq^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b4.q^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b5.freq^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b5.q^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.b5.gain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.eq.prmod^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.eq.bypass^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.eq.hpf.slope^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.eq.easy^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.eq.hpf.freq^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.dyn.prmod^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.dyn.gain^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.dyn.ratio^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.dyn.bypass^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.dyn.threshold^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.bpm^".format(id_fx), UiIntSubject)
            self.createSubject("SETD^f.{}.vca^".format(id_fx), UiIntSubject)
            self.createSubject("SETD^f.{}.bypass^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.prmod^".format(id_fx), UiBoolSubject)
            self.createSubject("SETD^f.{}.fxtype^".format(id_fx), UiIntSubject)
            self.createSubject("SETD^f.{}.par1^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.par2^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.par3^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.par4^".format(id_fx), UiPercentSubject)
            self.createSubject("SETD^f.{}.par5^".format(id_fx), UiPercentSubject)      
            self.createSubject("SETD^f.{}.par6^".format(id_fx), UiPercentSubject)

            for ix_aux in range(0, nr_auxs):
                self.createSubject("SETD^f.{}.aux.{}.pan^".format(id_fx, ix_aux), UiPercentSubject)  
                self.createSubject("SETD^f.{}.aux.{}.mute^".format(id_fx, ix_aux), UiBoolSubject)   
                self.createSubject("SETD^f.{}.aux.{}.value^".format(id_fx, ix_aux), UiPercentSubject)
                self.createSubject("SETD^f.{}.aux.{}.postproc^".format(id_fx, ix_aux), UiBoolSubject)
                self.createSubject("SETD^f.{}.aux.{}.post^".format(id_fx, ix_aux), UiBoolSubject)

        ### POST CREATION
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
        if topic not in ["VU2^", "RTA^", "VUA^"]: 
            _LOGGER.debug("<< {}".format(message))
        if topic is None: 
            _LOGGER.warning("nenhum topico encontrato para [{}]".format(message))
            return
        subject:UiSubject = self._subjects[topic]
        ui_value = message[len(topic):]
        subject._reiceve_value(ui_value)

UI_CMD_PREFIX = "3:::"
ALIVE = "ALIVE"
PING = "2::"
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
                if cmd.strip() == "":
                    pass
                else:
                    self.on_ui_command(cmd)

    def ui_send_command(self, cmd: str):
        self.send(UI_CMD_PREFIX + cmd)
        if cmd not in [ALIVE]: _LOGGER.debug(">>" + cmd)

    def on_error(self, web_socket_app, error):
        _LOGGER.info(f"on_error(web_socket_app, {error})")

    def on_close(self,web_socket_app, close_status_code, close_msg):
        _LOGGER.info(f"on_close(web_socket_app, {close_status_code}, {close_msg})")

    def on_open(self, web_socket_app):
        _LOGGER.info(f"on_open(web_socket_app)")

async def main():
    from ui_desktop import UiDesktop
    MIXER_IP = "192.168.15.103"
    MIXER_PORT = "80"
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s')
    #logging.basicConfig(filename="log.txt",filemode='w', format='%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.WARNING)
    conn = SoundcraftuiInstance(url=f"ws://{MIXER_IP}:{MIXER_PORT}")

    ui_desktop = UiDesktop(conn)
    wst = threading.Thread(target=conn.run_forever)
    wst.daemon = True
    wst.start()

    for i in range(0, 10) :
        print(i)
        if not conn.model_subject.cached is None: 
            break
        await asyncio.sleep(1)
    
    if conn.model_subject.cached is None:
        raise TimeoutError

    print(f"Connected to: {conn.model_subject.cached}")
    ui_desktop.run_forever()
    conn.close()
if __name__ == "__main__":
    asyncio.run(main())
