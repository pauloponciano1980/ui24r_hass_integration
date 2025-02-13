from dataclasses import dataclass, field
import tkinter as tk
from tkinter import ttk
from typing import Callable
from pynput import keyboard
import asyncio

class UiConverters:
    def boolean_to_ui_value(value: bool) -> str:
         if value == True: return "1"
         elif value == False: return "0"
         else:
             print("Valor {} não é boleano")
             return "0"

    def float_to_ui_value(value: float) -> str:
        if value > 1.0: 
            print("Valor {} não pode ser maior que 1".format(value))
            value = 1
        if value < 0.0:
            print("Valor {} não pode ser menor que 0".format(value))
            value = 0
        return str(value)

    def string_to_ui_value(value: str) -> str:
        return value

    def ui_value_to_boolean(ui_value: str) -> bool:
        return True if ui_value == "1" else False

    def ui_value_to_float(ui_value: str) -> float:
        return float(ui_value)

    def ui_value_to_string(ui_value: str) -> str:
        return ui_value

class UiPaths:

    SETD_I_0_A_1_MUTE = "SETD^i.{}.a.{}.mute^"
    SETD_I_0_A_1_VOLUME = "SETD^i.{}.a.{}.volume^"

    SETS_I_0_NAME = "SETS^i.{}.name^"
    SETD_I_0_FORCEUNMUTE = "SETD^i.{}.forceunmute^"
    SETD_I_0_VOLUME = "SETD^i.{}.volume^"

    SETS_A_0_NAME = "SETS^a.{}.name^"
    SETD_A_0_MUTE = "SETD^a.{}.mute^"
    SETD_A_0_VOLUME = "SETD^a.{}.volume^"

@dataclass
class UiStrSubject:   
    
    submit_callable:Callable[[str],None] = field(repr=False)
    cached:str = field(default=None)
    listeners:list[Callable[[str], None]] = field(default_factory=list)
    
    def add_listener(self, listener: Callable[[str], None]) -> None:
        self.listeners.append(listener)

    def _notify_listeners(self, value: str):
        for listener in self.listeners:
            listener(value)

    def _reiceve_value(self, ui_value: str):
        value:str = UiConverters.ui_value_to_string(ui_value)
        self._cached = value
        self._notify_listeners(value)
    
    def submit(self, value:str)->None:
        ui_value = UiConverters.string_to_ui_value(value)
        self.submit_callable(ui_value)

@dataclass
class UiBoolSubject:
    
    submit_callable:Callable[[bool],None] = field(repr=False)
    cached:bool = field(default=None)
    listeners:list[Callable[[bool], None]] = field(default_factory=list)
    
    def add_listener(self, listener: Callable[[bool], None]) -> None:
        self.listeners.append(listener)

    def _notify_listeners(self, value: bool):
        # UI24r -> controle
        for listener in self.listeners:
            listener(value)

    def _reiceve_value(self, ui_value: str):
        value:bool = UiConverters.ui_value_to_boolean(ui_value)
        self._cached = value
        self._notify_listeners(value)
    
    def submit(self, value:bool)->None:
        ui_value = UiConverters.boolean_to_ui_value(value)
        self.submit_callable(ui_value)

@dataclass
class UiFloatSubject:

    submit_callable:Callable[[str],None] = field(repr=False)
    cached:float = field(default=None)
    listeners:list[Callable[[float], None]] = field(default_factory=list)
    
    def add_listener(self, listener: Callable[[bool], None]) -> None:
        self.listeners.append(listener)

    def _notify_listeners(self, value: float):
        for listener in self.listeners:
            listener(value)

    def _reiceve_value(self, ui_value: str):
        value:float = UiConverters.ui_value_to_float(ui_value)
        self._cached = value
        self._notify_listeners(value)
    
    def submit(self, value:float)->None:
        ui_value = UiConverters.float_to_ui_value(value)
        self.submit_callable(ui_value)

@dataclass
class UiInputAuxiliarControl:
    volume_subject: UiFloatSubject
    mute_subject:UiBoolSubject

@dataclass
class UiInputControl:
    name_subject:UiStrSubject
    volume_subject:UiFloatSubject
    forceunmute_subject:UiBoolSubject
    auxiliars:list[UiInputAuxiliarControl]

@dataclass
class UiAuxiliarControl:
    name_subject:UiStrSubject
    volume_subject:UiFloatSubject
    mute_subject:UiBoolSubject

class WebsocketWrapper:
    
    def __init__(self):
        self._keylistener = keyboard.Listener(on_press=self._on_press)
        self._subjects = {}
        self._inputs = []
        for id_input in range(0, 24):
            input_auxiliars = []
            for id_auxiliar in range(0, 10):
                
                input_aux_mute_topic = UiPaths.SETD_I_0_A_1_MUTE.format(id_input, id_auxiliar)
                input_aux_mute_subject = UiBoolSubject(self._create_submit_callable(input_aux_mute_topic))
                self._subjects[input_aux_mute_topic] = input_aux_mute_subject

                input_aux_volume_topic = UiPaths.SETD_I_0_A_1_VOLUME.format(id_input, id_auxiliar)
                input_aux_volume_subject = UiFloatSubject(self._create_submit_callable(input_aux_volume_topic))
                self._subjects[input_aux_volume_topic] = input_aux_volume_subject

                input_auxiliar = UiInputAuxiliarControl(mute_subject=input_aux_mute_subject, volume_subject=input_aux_volume_subject)
                input_auxiliars.append(input_auxiliar)

            input_name_topic = UiPaths.SETS_I_0_NAME.format(id_input)
            input_name_subject = UiStrSubject(self._create_submit_callable(input_name_topic))
            self._subjects[input_name_topic] = input_name_subject

            input_volume_topic = UiPaths.SETD_I_0_VOLUME.format(id_input)
            input_volume_subject = UiFloatSubject(self._create_submit_callable(input_volume_topic))
            self._subjects[input_volume_topic] = input_volume_subject

            input_forceunmute_topic = UiPaths.SETD_I_0_FORCEUNMUTE.format(id_input)
            input_forceunmute_subject = UiBoolSubject(self._create_submit_callable(input_forceunmute_topic))
            self._subjects[input_forceunmute_topic] = input_forceunmute_subject

            input = UiInputControl(auxiliars=input_auxiliars, name_subject=input_name_subject, volume_subject=input_volume_subject, forceunmute_subject=input_forceunmute_subject)
            self._inputs.append(input)

        self._auxiliars = []
        for id_auxiliar in range(0, 10):
            
            auxiliar_name_topic = UiPaths.SETS_A_0_NAME.format(id_auxiliar)
            auxiliar_name_subject = UiStrSubject(self._create_submit_callable(auxiliar_name_topic))
            self._subjects[auxiliar_name_topic] = auxiliar_name_subject

            auxiliar_volume_topic = UiPaths.SETD_A_0_VOLUME.format(id_auxiliar)
            auxiliar_volume_subject = UiFloatSubject(self._create_submit_callable(input_aux_volume_topic))
            self._subjects[auxiliar_volume_topic] = auxiliar_volume_subject

            auxiliar_mute_topic = UiPaths.SETD_A_0_MUTE.format(id_auxiliar)
            auxiliar_mute_subject = UiBoolSubject(self._create_submit_callable(auxiliar_mute_topic))
            self._subjects[auxiliar_mute_topic] = auxiliar_mute_subject

            auxiliar = UiAuxiliarControl(
                volume_subject=auxiliar_volume_subject, 
                name_subject=auxiliar_name_subject, 
                mute_subject=auxiliar_mute_subject
            )
            self._auxiliars.append(auxiliar)

    def _create_submit_callable(self, topic):
        return lambda ui_value, ws=self, topic=topic: ws._send_message(topic+ui_value)

    def run_forever(self):
        self._keylistener.start()
        self._keylistener.join()


    def start(self):
        self._keylistener.start()

    async def async_run_forever(self):
        self.run_forever()
    
    @property
    def inputs(self) -> tuple[UiInputControl]:
        return tuple(self._inputs)
    
    @property
    def auxiliars(self) -> tuple[UiAuxiliarControl]:
        return tuple(self._auxiliars)

    def _reiceve_message(self, message: str):
        print("<< {}".format(message))
        topic = next(filter(lambda topic, message=message : message.startswith(topic), self._subjects.keys()),None)

        if topic is None: 
            print("nenhum tópico encontrato para {}".format(message))
            return
        
        subject:UiFloatSubject = self._subjects[topic]
        ui_value = message[len(topic):]

        subject._reiceve_value(ui_value)

    def _send_message(self, message:str)->None:
        print(">> {}".format(message))

    def _on_press(self, key):
        try:
            if key is None:
                return False
            elif key == keyboard.Key.esc:
                self._keylistener.stop()

            elif key.char == '1':
                self._reiceve_message("SETD^i.0.forceunmute^1")
            elif key.char == 'q':
                self._reiceve_message("SETD^i.0.forceunmute^0")
            elif key.char == 'a':
                self._reiceve_message("SETD^i.0.volume^0.80")
            elif key.char == 'z':
                self._reiceve_message("SETD^i.0.volume^0.20")

            elif key.char == '2':
                self._reiceve_message("SETD^i.1.forceunmute^1")
            elif key.char == 'w':
                self._reiceve_message("SETD^i.1.forceunmute^0")
            elif key.char == 's':
                self._reiceve_message("SETD^i.1.volume^0.80")
            elif key.char == 'x':
                self._reiceve_message("SETD^i.1.volume^0.20")

            elif key.char == '3':
                self._reiceve_message("SETD^i.2.forceunmute^1")
            elif key.char == 'e':
                self._reiceve_message("SETD^i.2.forceunmute^0")
            elif key.char == 'd':
                self._reiceve_message("SETD^i.2.volume^0.80")
            elif key.char == 'c':
                self._reiceve_message("SETD^i.2.volume^0.20")
        except AttributeError: return
class App:

    def __init__(self, ws:WebsocketWrapper):
        import enum
        self.suppress_event = False
        self.websocketWrapper = ws
        self.root = tk.Tk()
        self.root.title("Sound Mixer")
        self.root.geometry("1000x500")  # Aumenta o tamanho da tela
        
        self.frames = []
        self.name_vars = []
        self.name_controls = []
        self.forceunmute_vars = []
        self.forceunmute_controls = []
        for id, input in enumerate(ws.inputs): 
            self.frames.append(tk.Frame(self.root, bd=2, relief=tk.RIDGE, width=30, name=f"input-{id}-frame"))
            self.frames[id].pack(side=tk.LEFT, padx=5, pady=10)

            self.name_vars.append(tk.StringVar(name=f"input-{id}-name"))
            self.name_controls.append(tk.Entry(self.frames[id], textvariable=self.name_vars[id], name=f"input-{id}-name_control"))
            self.name_controls[id].pack(anchor=tk.CENTER, pady=5)
            self.name_controls[id].bind("<FocusOut>", lambda event, subject=input.name_subject, control_var=self.name_vars[id]: subject.submit(control_var.get()))
            self.name_controls[id].bind("<Return>", lambda event, subject=input.name_subject, control_var=self.name_vars[id]: subject.submit(control_var.get()))
            ws.inputs[id].name_subject.add_listener(lambda value, var=self.name_vars[id]: var.set(value))
            
            self.forceunmute_vars.append(tk.BooleanVar(name=f"input-{id}-mute"))
            self.forceunmute_controls.append(tk.Checkbutton(
                self.frames[id],
                name=f"input-{id}-mute_control",
                text="Force Unmute",
                command = lambda subject=input.forceunmute_subject, var=self.forceunmute_vars[id]: subject.submit(var.get()),
                variable=self.forceunmute_vars[id]))
            self.forceunmute_controls[id].pack(anchor=tk.CENTER, pady=5)
            ws.inputs[id].forceunmute_subject.add_listener(lambda value, var=self.forceunmute_vars[id]: var.set(value))
            
            volume_var = tk.DoubleVar(name=f"input-{id}-volume")
            volume_control = tk.Scale(
                self.frames[id],
                from_=255, to=0, orient=tk.VERTICAL, length=300,
                name=f"input-{id}-volume-control",
                variable=volume_var,
                command=lambda event, subject=input.volume_subject, var=volume_var: subject.submit(var.get()/255))
            volume_control.pack(anchor=tk.CENTER, pady=5)

            ws.inputs[id].volume_subject.add_listener(lambda value, var=volume_var: var.set(value*255))
            
    def run_forever(self):   
        self.root.mainloop()

    async def async_run_forever(self):
        self.run_forever()

async def main():
    
    websocketWrapper = WebsocketWrapper()

    app = App(websocketWrapper)
    #websocketWrapper.auxiliars[0].name_subject.add_listener(lambda value: print(f"auxiliars[0].name = {value}"))
    #websocketWrapper._reiceve_message("SETS^a.0.name^brasil")
    #websocketWrapper.auxiliars[0].name_subject.submit("china")

    #websocketWrapper.auxiliars[0].volume_subject.add_listener(lambda value: print(f"auxiliars[0].volume = {value}"))
    #websocketWrapper._reiceve_message("SETD^a.0.volume^0.5")
    #websocketWrapper.auxiliars[0].volume_subject.submit(1.0)

    #websocketWrapper.auxiliars[0].mute_subject.add_listener(lambda value: print(f"auxiliars[0].mute = {value}"))
    #websocketWrapper._reiceve_message("SETD^a.0.mute^1")
    #websocketWrapper.auxiliars[0].volume_subject.submit(False)
#########################################################
    #websocketWrapper.inputs[0].name_subject.add_listener(lambda value: print(f"inputs[0].name = {value}"))
    #websocketWrapper._reiceve_message("SETS^i.0.name^brasil")
    #websocketWrapper.inputs[0].name_subject.submit("china")

    websocketWrapper.inputs[0].volume_subject.add_listener(lambda value: print(f"inputs[0].volume = {value}"))
    websocketWrapper._reiceve_message("SETD^i.0.volume^0.6")
    #websocketWrapper.inputs[0].volume_subject.submit(1.0)
    print(websocketWrapper.inputs)

    #websocketWrapper.inputs[0].mute_subject.add_listener(lambda value: print(f"inputs[0].mute = {value}"))
    #websocketWrapper._reiceve_message("SETD^i.0.mute^1")
    #websocketWrapper.inputs[0].volume_subject.submit(False)
#########################################################
    #websocketWrapper.inputs[0].auxiliars[0].volume_subject.add_listener(lambda value: print(f"inputs[0].auxiliars[0].volume = {value}"))
    #websocketWrapper._reiceve_message("SETD^i.0.a.0.volume^0.3")
    #websocketWrapper.inputs[0].auxiliars[0].volume_subject.submit(1.0)

    #websocketWrapper.inputs[0].auxiliars[0].mute_subject.add_listener(lambda value: print(f"inputs[0].auxiliars[0].mute = {value}"))
    #websocketWrapper._reiceve_message("SETD^i.0.a.0.mute^1")
    #websocketWrapper.inputs[0].auxiliars[0].mute_subject.submit(False)

    
    websocketWrapper.start()
    t2 = app.async_run_forever()
    
    await t2
    


if __name__ == "__main__":
    asyncio.run(main())