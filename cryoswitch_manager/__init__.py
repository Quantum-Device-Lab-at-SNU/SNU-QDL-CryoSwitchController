from .CryoSwitchController import Cryoswitch
import time

class CryoSwitchConfig:
    def __init__(
        self, name: str, switch_model: str, controller: Cryoswitch,
        controller_port: str, position: int=None
    ):
        self._name = name           # name of the switch. e.g., switch_a_6x1, input_switch_a_2x2

        if switch_model in ['R583423141', 'R577433007']:
            self._switch_model = switch_model
        else:
            print(f'{switch_model} is currently unsupported.')

        self._position = position
        self.controller = controller
        self.controller_port = controller_port

    @property
    def name(self) -> str:
        """Name of the switch

        Returns:
            str: a string that indicates the name of the switch
        """
        return self._name
    
    @property
    def switch_model(self) -> str:
        """Model of the switch

        Returns:
            str: a string that indicates the model of the switch
        """
        return self._switch_model

    def connect(self, value: int):
        """Connect the switch to position specified by the `value`.

        Args:
            value (int): an integer indicating the position to connect to.
        """
        self.controller.connect(self.controller_port[0], value)

    def disconnect(self, value: int):
        """Disconnect the switch from the position specified by the `value`.

        Args:
            value (int): an integer indicating the position to disconnect from.
        """
        self.controller.disconnect(self.controller_port[0], value)

    def initialize(self):
        """Initialize the switch to position 1.
        """
        self.position = 1
        print(f"INFO: Switch {self.name}: position initialized to 1")

    def set_position(self, value: int):
        self.position = value

class Cryo6x1SwitchConfig(CryoSwitchConfig):

    def disconnect_all(self):
        self.controller.disconnect_all(self.controller_port)

    @property
    def position(self) -> int:
        if self._position is not None:
            return self._position
        else:
            print("Switch position unknown")

    @position.setter
    def position(self, value: int):
        if value in [1, 2, 3, 4, 5, 6]:
            init_pos = self.position
            if init_pos == None:
                # initial position unknown. Perform global reset
                self.disconnect_all()
            else:
                # if initial position is known, disconnect that position
                self.disconnect(init_pos)
            time.sleep(1)   # delay between disconnect operation and connect operation

            # connect to the specified position
            self.connect(value)
            self._position = value
        else:
            raise ValueError(f"The specified position {value} is unsettable. You need to specify an integer between 1 and 6.")

    @property
    def connectivity(self) -> tuple[str, str]:
        if self.position is not None:
            return (str(self.position), 'C')
        else:
            return ("Unknown", )

class Cryo2x2SwitchConfig(CryoSwitchConfig):
    @property
    def position(self) -> int:
        if self._position is not None:
            return self._position
        else:
            print("Switch position unknown")

    @position.setter
    def position(self, value: int):
        if value == 1:
            self.connect(int(self.controller_port[1]))
            self._position = value
        elif value == 2:
            self.disconnect(int(self.controller_port[1]))
            self._position = value
        else:
            raise ValueError(f"The specified position {value} is unsettable. You need to specify an integer 1 or 2.")

    @property
    def connectivity(self) -> list[tuple[str, str]]:
        if self.position is not None:
            if self.position == 1:
                return [('1', '3'), ('2', '4')]
            elif self.position == 2:
                return [('1', '2'), ('3', '4')]
        else:
            return ("Unknown", )

class CryoSwitchManager:
    def __init__(
        self, switch_config_list: list[dict], COM_port: str = "COM5",
        initialize_all: bool = True, control_mode: str = "cryo"
    ):

        # establish connection to the QPhoX CryoSwitch Controller
        self.controller = Cryoswitch(COM_port = COM_port)
        self.controller.start()

        self.control_mode = control_mode
        self._switch_list = []

        for switch_config in switch_config_list:
            name = switch_config["name"]
            switch_model = switch_config["name"]
            controller_port = switch_config["controller_port"]
            position = switch_config["controller_port"] if "controller_port" in switch_config.keys() else None
            self.add_switch(name, switch_model, controller_port, position=position)
        
        if initialize_all:
            self.initialize_all()

    def add_switch(self, name: str, switch_model: str, controller_port: str, position: int = None):
        """Add a switch to the manager.

        Args:
            name (str): Unique name of the switch.
            switch_model (str): Model of the switch.
            controller_port (str): Port of the controller connected to the switch.
            position (int, optional): Initial known position of the switch. Defaults to None.

        Raises:
            ValueError: Error is raised when switch models are not 'R583423141' or 'R577433007'.
        """
        if switch_model in ['R583423141']:
            switch = Cryo6x1SwitchConfig(
                name, switch_model, self.controller, controller_port, position=position
            )
        elif switch_model in ['R577433007']:
            switch = Cryo2x2SwitchConfig(
                name, switch_model, self.controller, controller_port, position=position
            )
        else:
            raise ValueError(f"The switch model {switch_model} is currently unsupported.")
        self._switch_list.append(switch)
        setattr(self, name, switch)           

    def get_internal_temperature(self) -> float:
        """Get internal temperature of the controller

        Returns:
            float: internal temperature of the switch controller
        """
        return self.controller.get_internal_temperature()

    def report_connectivity(self) -> None:
        print("Cryo Switch Connectivity Report: ")
        for switch in self.switch_list:
            report_str = f"• {switch.name}: "
            if isinstance(switch.connectivity, tuple):
                report_str += '↔'.join(switch.connectivity)
            elif isinstance(switch.connectivity, list):
                report_str += ', '.join(["↔".join(_connectivity) for _connectivity in switch.connectivity])
            print(report_str)

    def set_OCP_mA(self, OCP_value: float):
        self.controller.set_OCP_mA(OCP_value)

    def set_output_voltage(self, Vout: float):
        self.controller.set_output_voltage(Vout)

    def set_pulse_duration_ms(self, ms_duration):
        self.controller.set_pulse_duration_ms(ms_duration)

    def set_room_temp_mode(self):
        """
        Set the output voltage to 24V for room temp operation
        """
        self.set_output_voltage(24)

    def set_cryo_mode(self):
        """
        Set the output voltage to 5V for cryo operation
        """
        self.set_output_voltage(5)

    def initialize_all(self) -> None:
        for switch in self.switch_list:
            switch.initialize()

    @property
    def control_mode(self) -> str:
        """Control mode of the switch controller. Must be either "room temp" or "cryo"

        Returns:
            str: a string that specifies the control mode.
        """
        return self._control_mode

    @control_mode.setter
    def control_mode(self, mode: str):
        if mode == "cryo":
            self.set_cryo_mode()
        elif mode == "room temp":
            self.set_room_temp_mode()
        else:
            raise ValueError(
                f"The specified control mode {mode} is not available. Control mode must be either 'cryo' or 'room temp'."
            )

    @property
    def switch_list(self) -> list[CryoSwitchConfig]:
        """List of available cryo switches.

        Returns:
            list[CryoSwitchConfig]: list of `CryoSwitchConfig` each representing an available cryo switch.
        """
        return self._switch_list