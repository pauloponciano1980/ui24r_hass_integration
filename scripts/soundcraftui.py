import logging
import websocket
import asyncio
import threading
from dataclasses import dataclass

UI_CMD_PREFIX = "3:::"
ALIVE = "ALIVE"
PING = "2::"

class UiConnection(threading.Thread):
    """
    Manages the connection to the Soundcraft UI24R digital sound console.
    
    Attributes:
        _ui_state (dict): The state of the UI.
        _mixer_ip (str): The IP address of the mixer.
        _is_open (bool): Indicates if the connection is open.
    """
    
    def __init__(self, mixer_ip):
        """
        Initializes the UiConnection with the given mixer IP address.
        
        Args:
            mixer_ip (str): The IP address of the mixer.
        """
        super().__init__()
        self._ui_state = {}
        self._mixer_ip = mixer_ip
        self._is_open = False
        
    def ui_send_command(self, cmd: str):
        """
        Sends a command to the mixer.
        
        Args:
            cmd (str): The command to send.
        """
        self.web_socket_app.send(UI_CMD_PREFIX + cmd)
        if cmd != ALIVE:
            logging.debug(">>" + cmd)
        
    def on_message(self, web_socket_app, message: str):
        """
        Handles incoming messages from the mixer.
        
        Args:
            web_socket_app: The WebSocket application.
            message (str): The incoming message.
        """
        for line in message.split("\n"):
            if line == PING:
                self.ui_send_command(ALIVE)
            else:
                cmd = line.split(":")[-1]
                cmdargs = cmd.split("^")
                if cmdargs[0] not in ["RTA", "VU2", "VUA", "UPDATE_PLAYLIST"]:
                    if cmdargs[0] in ["SETD", "SETS"]:
                        k = "^".join(cmdargs[:-1])
                        v = cmdargs[-1]
                        self._ui_state[k] = v
                        logging.debug("<<" + cmd)
                    else:
                        logging.warn("Unknown received message:" + cmd)

    def on_error(self, web_socket_app, error):
        """
        Handles errors from the WebSocket connection.
        
        Args:
            web_socket_app: The WebSocket application.
            error: The error that occurred.
        """
        logging.error(error)

    def on_close(self, web_socket_app, close_status_code, arg4):
        """
        Handles the closing of the WebSocket connection.
        
        Args:
            web_socket_app: The WebSocket application.
            close_status_code: The status code for the close.
            arg4: Additional argument.
        """
        self._is_open = False
        logging.debug("### closed ###")
        self._reconnect()

    def on_open(self, web_socket_app):
        """
        Handles the opening of the WebSocket connection.
        
        Args:
            web_socket_app: The WebSocket application.
        """
        logging.debug("Connected to the server")
        self._is_open = True
        
    def close(self):
        """
        Closes the WebSocket connection.
        """
        self.web_socket_app.keep_running = False
        self._is_open = False

    def _reconnect(self):
        """
        Attempts to reconnect to the mixer.
        """
        logging.debug("Attempting to reconnect...")
        asyncio.run(self.async_run_forever())

    async def async_run_forever(self):
        """
        Runs the WebSocket connection asynchronously, attempting to reconnect if it closes.
        """
        while True:
            self._is_open = False
            self.web_socket_app = websocket.WebSocketApp(
                f"ws://{self._mixer_ip}:80", 
                on_error=self.on_error, 
                on_close=self.on_close, 
                on_message=self.on_message, 
                on_open=self.on_open
            )
            self.web_socket_app.keep_running = True
            self.wst = threading.Thread(target=self.web_socket_app.run_forever)
            self.wst.daemon = True
            self.wst.start()
            
            while not self._is_open:
                await asyncio.sleep(0.1)
            await asyncio.sleep(1)  # Wait a bit before trying to reconnect

@dataclass(frozen=True)
class UiFaderTemplate:
    """
    Template class for fader controls on the Soundcraft UI24R.
    
    Attributes:
        conn (UiConnection): The connection to the UI.
    """
    conn: UiConnection
    
    @staticmethod
    def _ui_to_float(value: str) -> float:
        """
        Converts a UI string value to a float.
        
        Args:
            value (str): The UI string value.
        
        Returns:
            float: The converted float value.
        
        Raises:
            ValueError: If the value is not between 0 and 1.
        """
        float_value = float(value)
        if not (0 <= float_value <= 1):
            raise ValueError("Value must be between 0 and 1")
        return float_value
    
    @staticmethod
    def _float_to_ui(value: float) -> str:
        """
        Converts a float value to a UI string value.
        
        Args:
            value (float): The float value.
        
        Returns:
            str: The UI string value.
        """
        return str(round(value, 11))
    
    @staticmethod
    def _ui_to_bool(value: str) -> bool:
        """
        Converts a UI string value to a boolean.
        
        Args:
            value (str): The UI string value.
        
        Returns:
            bool: The converted boolean value.
        """
        return value == "1"
        
    @staticmethod
    def _bool_to_ui(value: bool) -> str:
        """
        Converts a boolean value to a UI string value.
        
        Args:
            value (bool): The boolean value.
        
        Returns:
            str: The UI string value.
        """
        return "1" if value else "0"

    def ui_retrieve_str(self, path: str) -> str:
        """
        Retrieves a string value from the UI state.
        
        Args:
            path (str): The path to the value in the UI state.
        
        Returns:
            str: The retrieved string value.
        
        Raises:
            ValueError: If there is an error converting the value.
        """
        ui_value = self.conn._ui_state.get(path)
        try:
            return str(ui_value)
        except Exception as e:
            raise ValueError(f"Error converting value for path {path}: {ui_value}") from e
        
    def ui_retrieve_bool(self, path: str) -> bool:
        """
        Retrieves a boolean value from the UI state.
        
        Args:
            path (str): The path to the value in the UI state.
        
        Returns:
            bool: The retrieved boolean value.
        
        Raises:
            ValueError: If there is an error converting the value.
        """
        ui_value = self.conn._ui_state.get(path)
        try:
            return self._ui_to_bool(ui_value)
        except Exception as e:
            raise ValueError(f"Error converting value for path {path}: {ui_value}") from e
        
    def ui_send_bool(self, path: str, value: bool) -> None:
        """
        Sends a boolean value to the UI state.
        
        Args:
            path (str): The path to the value in the UI state.
            value (bool): The boolean value to send.
        """
        ui_value = self._bool_to_ui(value)
        self.conn.ui_send_command(path + "^" + ui_value)
        self.conn._ui_state[path] = value
        
    def ui_retrieve_float(self, path: str) -> float:
        """
        Retrieves a float value from the UI state.
        
        Args:
            path (str): The path to the value in the UI state.
        
        Returns:
            float: The retrieved float value.
        
        Raises:
            ValueError: If there is an error converting the value.
        """
        ui_value = self.conn._ui_state.get(path)
        try:
            return self._ui_to_float(ui_value)
        except Exception as e:
            raise ValueError(f"Error converting value for path {path}: {ui_value}") from e
        
    def ui_send_float(self, path: str, value: float) -> None:
        """
        Sends a float value to the UI state.
        
        Args:
            path (str): The path to the value in the UI state.
            value (float): The float value to send.
        """
        ui_value = self._float_to_ui(value)
        self.conn.ui_send_command(path + "^" + ui_value)
        self.conn._ui_state[path] = value
        
@dataclass(frozen=True)
class UiAuxFader(UiFaderTemplate):
    """
    Represents an auxiliary fader on the Soundcraft UI24R.
    
    Attributes:
        id_aux (int): The ID of the auxiliary fader.
    """
    id_aux: int
        
    @property
    def unique_id(self):
        """
        Returns the unique ID of the auxiliary fader.
        
        Returns:
            str: The unique ID.
        """
        return 'aux' + str(self.id_aux)
        
    @property
    def name(self):
        """
        Returns the name of the auxiliary fader.
        
        Returns:
            str: The name.
        """
        path = f'SETS^a.{self.id_aux}.name'
        nm_aux = self.ui_retrieve_str(path)    
        return nm_aux if nm_aux else f'AUX {str(self.id_aux)}'
        
    @property
    def volume(self):
        """
        Returns the volume of the auxiliary fader.
        
        Returns:
            float: The volume.
        """
        path = f'SETD^a.{self.id_aux}.mix'
        return self.ui_retrieve_float(path)
        
    def set_volume(self, value: float):
        """
        Sets the volume of the auxiliary fader.
        
        Args:
            value (float): The volume to set.
        """
        path = f'SETD^a.{self.id_aux}.mix'
        self.ui_send_float(path, value)
    
    @property
    def mute(self) -> bool:
        """
        Returns whether the auxiliary fader is muted.
        
        Returns:
            bool: True if muted, False otherwise.
        """
        return self.ui_retrieve_bool(f'SETD^a.{self.id_aux}.mute')
        
    def set_mute(self, mute: bool):        
        """
        Sets the mute state of the auxiliary fader.
        
        Args:
            mute (bool): The mute state to set.
        """
        self.ui_send_bool(f'SETD^a.{self.id_aux}.mute', mute)
        
    def toggle_mute(self):
        """
        Toggles the mute state of the auxiliary fader.
        """
        self.set_mute(not self.mute)
    
    def __str__(self):
        """
        Returns a string representation of the auxiliary fader.
        
        Returns:
            str: The string representation.
        """
        return f'{self.__class__.__name__}[id_aux: {self.id_aux}, unique_id: {self.unique_id}, name: {self.name}, mute: {self.mute}, volume: {self.volume}]'

@dataclass(frozen=True)
class UiInputFader(UiFaderTemplate):
    """
    Represents an input fader on the Soundcraft UI24R.
    
    Attributes:
        id_input (int): The ID of the input fader.
    """
    id_input: int
        
    @property
    def unique_id(self):
        """
        Returns the unique ID of the input fader.
        
        Returns:
            str: The unique ID.
        """
        return 'input' + str(self.id_input)
        
    @property
    def name(self):
        """
        Returns the name of the input fader.
        
        Returns:
            str: The name.
        """
        nm_aux = self.ui_retrieve_str(f'SETS^i.{self.id_input}.name')
        return nm_aux if nm_aux else f'CH {self.id_input}'
        
    @property
    def volume(self):
        """
        Returns the volume of the input fader.
        
        Returns:
            float: The volume.
        """
        return self.ui_retrieve_float(f'SETD^i.{self.id_input}.mix')
            
    def set_volume(self, value: float):
        """
        Sets the volume of the input fader.
        
        Args:
            value (float): The volume to set.
        """
        path = f'SETD^i.{self.id_input}.mix'
        self.ui_send_float(path, value)
        
    @property
    def mute(self):
        """
        Returns whether the input fader is muted.
        
        Returns:
            bool: True if muted, False otherwise.
        """
        return not self.ui_retrieve_bool(f'SETD^i.{self.id_input}.forceunmute')
        
    def set_mute(self, mute: bool):
        """
        Sets the mute state of the input fader.
        
        Args:
            mute (bool): The mute state to set.
        """
        self.ui_send_bool(f'SETD^i.{self.id_input}.forceunmute', not mute)
        
    def toggle_mute(self):
        """
        Toggles the mute state of the input fader.
        """
        self.set_mute(not self.mute)
    
    def __str__(self):
        """
        Returns a string representation of the input fader.
        
        Returns:
            str: The string representation.
        """
        return f'{self.__class__.__name__}[id_input: {self.id_input}, unique_id: {self.unique_id}, name: {self.name}, mute: {self.mute}, volume: {self.volume}]'

@dataclass(frozen=True)
class UiInputAuxFader(UiFaderTemplate):
    """
    Represents an input to auxiliary fader on the Soundcraft UI24R.
    
    Attributes:
        id_input (int): The ID of the input fader.
        id_aux (int): The ID of the auxiliary fader.
    """
    id_input: int
    id_aux: int
        
    @property
    def unique_id(self) -> str:
        """
        Returns the unique ID of the input to auxiliary fader.
        
        Returns:
            str: The unique ID.
        """
        return 'input' + str(self.id_input) + 'aux' + str(self.id_aux)
        
    @property
    def name(self) -> str:
        """
        Returns the name of the input to auxiliary fader.
        
        Returns:
            str: The name.
        """
        nm_input = self.ui_retrieve_str(f'SETS^i.{self.id_input}.name')
        if not nm_input:
            nm_input = f'CH {self.id_input}'
        
        nm_aux = self.ui_retrieve_str(f'SETS^a.{self.id_aux}.name')
        if not nm_aux:
            nm_aux = f'AUX {self.id_aux}'
        
        return f'{nm_input} em {nm_aux}'
        
    @property
    def volume(self) -> float:
        """
        Returns the volume of the input to auxiliary fader.
        
        Returns:
            float: The volume.
        """
        return self.ui_retrieve_float(f'SETD^i.{self.id_input}.aux.{self.id_aux}.value')
            
    def set_volume(self, value: float) -> None:
        """
        Sets the volume of the input to auxiliary fader.
        
        Args:
            value (float): The volume to set.
        """
        path = f'SETD^i.{self.id_input}.aux.{self.id_aux}.value'
        self.ui_send_float(path, value)
        
    @property
    def mute(self) -> bool:
        """
        Returns whether the input to auxiliary fader is muted.
        
        Returns:
            bool: True if muted, False otherwise.
        """
        return self.ui_retrieve_bool(f'SETD^i.{self.id_input}.aux.{self.id_aux}.mute')
    
    def set_mute(self, value: bool) -> None:
        """
        Sets the mute state of the input to auxiliary fader.
        
        Args:
            value (bool): The mute state to set.
        """
        self.ui_send_bool(f'SETD^i.{self.id_input}.aux.{self.id_aux}.mute', value)
        
    def toggle_mute(self) -> None:
        """
        Toggles the mute state of the input to auxiliary fader.
        """
        self.set_mute(not self.mute)
    
    def __str__(self) -> str:
        """
        Returns a string representation of the input to auxiliary fader.
        
        Returns:
            str: The string representation.
        """
        return f'{self.__class__.__name__}[id_input: {self.id_input}, id_aux: {self.id_aux}, unique_id: {self.unique_id}, name: {self.name}, mute: {self.mute}, volume: {self.volume}]'
