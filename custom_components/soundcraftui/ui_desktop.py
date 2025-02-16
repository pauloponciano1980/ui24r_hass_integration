

import asyncio
import logging
import tkinter as tk
from tkinter import ttk

_LOGGER = logging.getLogger("ui_desktop")

from ui_console_broker import UiConsoleBroker
class UiDesktop:

    def __init__(self, ws: UiConsoleBroker):
        import enum
        self.suppress_event = False
        self.websocketWrapper = ws
        self.root = tk.Tk()
        self.root.title("Sound Mixer")
        self.root.geometry("1000x500")  # Aumenta o tamanho da tela
        canvas = tk.Canvas(self.root, bd=0, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(canvas, orient=tk.HORIZONTAL, command=canvas.xview)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.BOTH) # Changed fill to BOTH
        canvas.configure(xscrollcommand=scrollbar.set)

        channel_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=channel_frame, anchor="nw")

        # Bind the canvas to configure event to update the scrollable region
        channel_frame.bind("<Configure>", lambda event, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        for id, input in enumerate(ws.inputs): 
            frame = tk.Frame(channel_frame, bd=2, relief=tk.RIDGE, width=30, name=f"input-{id}-frame")
            frame.pack(side=tk.LEFT, padx=5, pady=10)

            name_var = tk.StringVar(name=f"input-{id}-name", value=input.name_subject.cached)
            name_control = tk.Entry(frame, textvariable=name_var, name=f"input-{id}-name_control")
            name_control.pack(anchor=tk.CENTER, pady=5)
            name_control.bind("<FocusOut>", lambda event, subject=input.name_subject, control_var=name_var: subject.submit(control_var.get()))
            name_control.bind("<Return>", lambda event, subject=input.name_subject, control_var=name_var: subject.submit(control_var.get()))
            input.name_subject.add_listener(lambda value, var=name_var: var.set(value))
            
            forceunmute_var = tk.BooleanVar(name=f"input-{id}-mute", value=input.forceunmute_subject.cached)
            tk.Checkbutton(
                frame,
                name=f"input-{id}-mute_control",
                text="Force Unmute",
                command = lambda subject=input.forceunmute_subject, var=forceunmute_var: subject.submit(var.get()),
                variable=forceunmute_var
            ).pack(anchor=tk.CENTER, pady=5)
            input.forceunmute_subject.add_listener(lambda value, var=forceunmute_var: var.set(value))
            
            stereo_index_var = tk.IntVar(name=f"input-{id}-stereo_index", value=input.stereo_index_subject.cached)
            stereo_index_control = tk.Entry(frame, textvariable=stereo_index_var, width=3, name=f"input-{id}-stereo_index_control")
            stereo_index_control.pack(anchor=tk.CENTER, pady=5)
            stereo_index_control.bind("<FocusOut>", lambda event, subject=input.stereo_index_subject, control_var=stereo_index_var: subject.submit(control_var.get()))
            stereo_index_control.bind("<Return>", lambda event, subject=input.stereo_index_subject, control_var=stereo_index_var: subject.submit(control_var.get()))
            input.stereo_index_subject.add_listener(lambda value, var=stereo_index_var: var.set(value))

            volume_var = tk.DoubleVar(name=f"input-{id}-volume", value=input.mix_subject.cached)
            tk.Scale(
                frame,
                from_=1.0, to=0.0, orient=tk.VERTICAL, length=300, digits = 4, resolution = 0.0001,
                name=f"input-{id}-volume-control",
                variable=volume_var,
                command=lambda event, subject=input.mix_subject, var=volume_var: subject.submit(var.get())
            ).pack(anchor=tk.CENTER, pady=5)

            input.mix_subject.add_listener(lambda value, var=volume_var: var.set(value)) # Removed * 255

    def run_forever(self):   
        self.root.mainloop()

    async def async_run_forever(self):
        self.run_forever()

async def main():
    
    websocketWrapper = UiConsoleBroker()

    websocketWrapper.on_ui_command("SETS^i.0.name^brasil")

    websocketWrapper.inputs[0].mix_subject.add_listener(lambda value: _LOGGER.info(f"inputs[0].volume = {value}"))
    websocketWrapper.on_ui_command("SETD^i.0.mix^0.6")
    websocketWrapper.on_ui_command("SETD^i.1.stereoIndex^2")
    websocketWrapper.on_ui_command("SETD^i.2.stereoIndex^1")
    websocketWrapper.inputs[0].mix_subject.submit(0.06)

    app = UiDesktop(websocketWrapper)
    
    websocketWrapper.start()
    t2 = app.async_run_forever()
    
    await t2
    



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    asyncio.run(main())