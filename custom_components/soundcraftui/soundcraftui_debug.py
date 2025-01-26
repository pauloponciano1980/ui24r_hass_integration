import logging
import websocket
import time
import threading
from dataclasses import dataclass
from soundcraftui import SoundcraftuiInstance, UiAuxFader, UiInputFader, UiInputAuxFader

#### 
#### A sessão a seguir é utilizada para tetes e depuração do componente
#### 
#### 

def test_fader(ui_fader):
    ui_fader_mute = ui_fader.mute
    ui_fader_volume = ui_fader.volume
    
    logging.info(f"valores Originais: {ui_fader}")
    
    time.sleep(1)

    logging.info(f"ui_fader.set_mute(True)")
    ui_fader.set_mute(True)
    logging.info(f"ui_fader.mute: {ui_fader.mute}")
    
    time.sleep(1)

    logging.info(f"ui_fader.set_mute(False)")
    ui_fader.set_mute(False)
    logging.info(f"ui_fader.mute: {ui_fader.mute}")

    logging.info(f"valores Originais: {ui_fader}")
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_volume(1)")
    #ui_fader.set_volume(1.0)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_volume(0.8)")
    #ui_fader.set_volume(0.8)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_volume(0.6)")
    #ui_fader.set_volume(0.6)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_volume(0.4)")
    #ui_fader.set_volume(0.4)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_volume(0.2)")
    #ui_fader.set_volume(0.2)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_volume(0)")
    #ui_fader.set_volume(0)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.set_mute(False)")
    #ui_fader.set_mute(False)
    
    #time.sleep(1)
    #logging.info(f"ui_fader.toggle_mute()")
    #ui_fader.toggle_mute()
    
    #time.sleep(1)
    #logging.info(f"ui_fader.toggle_mute()")
    
    #time.sleep(1)
    #ui_fader.set_volume(ui_fader_volume)
    #ui_fader.set_mute(ui_fader_mute)
    
def main():
    MIXER_IP = "192.168.15.103"
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    
    conn=SoundcraftuiInstance(mixer_ip=MIXER_IP)
   
    ui_aux_fader = UiAuxFader(conn = conn, id_aux = 3)
    
    ui_input_fader = UiInputFader(conn = conn, id_input = 4)
    
    ui_input_aux_fader = UiInputAuxFader(conn = conn, id_input = 4, id_aux = 3)
    
    conn.async_run_forever()
    
    
    #await test_fader(ui_aux_fader)
    test_fader(ui_input_fader)
    #await test_fader(ui_input_aux_fader)
        
    conn.close()
    
if __name__ == "__main__": main()