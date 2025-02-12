import tkinter as tk
from tkinter import ttk
from typing import Callable
from pynput import keyboard

class WebsocketWrapper:

    def __init__(self):
        self._listners = {}

    def add_listener(self, listener: Callable[[str, str], None], control_key:str):
        if self._listeners.get(control_key) is None: self._listeners[control_key] = []
        self._listeners[control_key].append(listener)

    def remove_listener(self, listener: Callable[[str, str], None], control_key:str):
        if self._listeners.get(control_key) is None: return
        self._listeners[control_key].remove(listener)

    def reiceve_message(self, control_key: str, ui_value: str):
        print(f"ui_reiceve_message: {control_key}^{ui_value}")

    def ui_send_message(self, control_key: str, ui_value: str):
        #for listener in self._listeners.get(control_key, []):
        #    listener(control_key, ui_value)
        control_reiceve_message(control_key, ui_value)

    
def on_press(key):
    global suppress_event
    try:
        if key.char == '1':
            websocketWrapper.ui_send_message("i.0.mute", "0")
        elif key.char == 'q':
            websocketWrapper.ui_send_message("i.0.mute", "1")
        elif key.char == 'a':
            websocketWrapper.ui_send_message("i.0.volume", "0.80")
        elif key.char == 'z':
            websocketWrapper.ui_send_message("i.0.volume", "0.20")
    except AttributeError:
        pass

listener = keyboard.Listener(on_press=on_press)
listener.start()
#listener.join()

class App:

    def __init__(self):
        self.suppress_event = False
        self.controls = {}
        self.root = tk.Tk()
        self.root.title("Sound Mixer")
        self.root.geometry("1000x500")  # Aumenta o tamanho da tela
        for i in range(0, 10):
            frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, width=30)
            frame.pack(side=tk.LEFT, padx=5, pady=10)

            name_key = f"i.{i}.name"
            name_var = tk.StringVar()
            name_var.set(f"CH{i+1}")
            name_control = tk.Entry(frame, textvariable=name_var)
            name_control.pack(anchor=tk.CENTER, pady=5)
            name_control.bind("<FocusOut>", lambda event, control_key=name_key, control_var=name_var: self.control_send_message(control_key, control_var))
            name_control.bind("<Return>", lambda event, control_key=name_key, control_var=name_var: self.control_send_message(control_key, control_var))
            self.controls[name_key] = name_var

            mute_var = tk.BooleanVar()
            mute_key = f"i.{i}.mute"
            mute_control = tk.Checkbutton(
                frame,
                text="Mute",
                variable=mute_var,
                command=lambda control_key=mute_key, control_var=mute_var: self.control_send_message(control_key, control_var))
            mute_control.pack(anchor=tk.CENTER, pady=5)
            self.controls[mute_key] = mute_var

            volume_var = tk.DoubleVar()
            volume_key = f"i.{i}.volume"
            volume_control = tk.Scale(
                frame,
                from_=255, to=0, orient=tk.VERTICAL, length=300,
                variable=volume_var,
                command=lambda event, control_key=volume_key, control_var=volume_var: self.control_send_message(control_key, control_var))
            volume_control.pack(anchor=tk.CENTER, pady=5)
            self.controls[volume_key] = volume_var
        
    def control_send_message(self, control_key: str, control_var: any):
        if not app.suppress_event:
            #print(f"control_send_message({control_key}, {control_var.get()})")
            if isinstance(control_var, tk.BooleanVar):
                websocketWrapper.reiceve_message(control_key, boolean_to_ui_value(control_var.get()))
            elif isinstance(control_var, tk.DoubleVar):
                websocketWrapper.reiceve_message(control_key, double_to_ui_value(control_var.get()))
            elif isinstance(control_var, tk.StringVar):
                websocketWrapper.reiceve_message(control_key, string_to_ui_value(control_var.get()))
            else:
                print(f"Unknown control type: {control_key}, {control_var.__class__.__name__}")
                return

    def mainloop(self):   
        self.root.mainloop()

def main():
    pass

websocketWrapper = WebsocketWrapper()
app = App()




def control_reiceve_message(control_key: str, ui_value: str):

    app.suppress_event = True
    control_var = app.controls[control_key]
    if isinstance(control_var, tk.BooleanVar):
        control_value = ui_value_to_boolean(ui_value)
        control_var.set(control_value)
    elif isinstance(control_var, tk.DoubleVar):
        control_value = ui_value_to_double(ui_value)
        control_var.set(control_value)
    elif isinstance(control_var, tk.StringVar):
        control_value = ui_value_to_string(ui_value)
        control_var.set(control_value)
    else:
        print(f"Unknown control type: {control_key}, {control_var.__class__.__name__}")
    app.suppress_event = False


def boolean_to_ui_value(value: bool) -> str:
    return "1" if value == True else "0"

def double_to_ui_value(value: float) -> str:
    return str(value / 255)

def string_to_ui_value(value: str) -> str:
    return value

def ui_value_to_boolean(ui_value: str) -> bool:
        return True if ui_value == "1" else False

def ui_value_to_double(ui_value: str) -> float:
    return float(ui_value) * 255

def ui_value_to_string(ui_value: str) -> str:
    return ui_value




app.mainloop()

if __name__ == "__main__":
    main()