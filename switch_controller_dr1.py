from CryoSwitchManager import CryoSwitchManager

cryoswitch_config_dr1 = [
    {
        "name": "switch_A_6x1",
        "switch_model": "R583423141",
        "controller_port": "A",
        "position": None
    },
    {
        "name": "switch_B_6x1",
        "switch_model": "R583423141",
        "controller_port": "B",
        "position": None
    },
    {
        "name": "input_switch_A_2x2",
        "switch_model": "R577433007",
        "controller_port": "C12",  # switch terminal 1 and 2 connected to port C line 1 and 2, respectively
        "position": None
    },
    {
        "name": "switch_A_6x1",
        "switch_model": "R577433007",
        "controller_port": "C34",  # switch terminal 3 and 3 connected to port C line 3 and 4, respectively
        "position": None
    },
]

switch_manager = CryoSwitchManager(cryoswitch_config_dr1, COM_port = "COM5")