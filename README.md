# CryoSwitchController

## Project structure

## Getting started

This repository holds the QP-CryoSwitchController compatible software.


## Installation
- Clone the repo
- Run: ```pip install -r requirements.txt```
- Browse the CryoSwitchController.py file for library implementation


## Library Usage
A basic implementation of the CryoSwitchController class can be done with the following functions:
- start() 

        Input: None
        Default: None
        Enables the voltage rails, voltage converter and output channels

- set_output_voltage(Vout)

        Input: Desired output voltage (Vout)
        Default: 5V
        Sets the converter voltage to Vout. The converter voltage is later utilized by the output stage to generate the positive/negative pulses.

- set_pulse_duration_ms(ms_duration)

        Input: Pulse width duration in miliseconds (ms_duration).
        Default: 10ms.
        Sets the the output pulse (positive/negative) duration in miliseconds.

- connect(port, contact)

        Input: Corresponding port and contact to be connected. Port={A, B, C, D}, contact={1,...,6}
        Default: None.
        Connects the specified contact of the specified port (switch).

- disconnect(port, contact)

        Input: Corresponding port and contact to be disconnected. Port={A, B, C, D}, contact={1,...,6}
        Default: None.
        Disconnects the specified contact of the specified port (switch).



## Advanced functions

- set_OCP_mA(OCP_value)

        Input: Overcurrent protection trigger value (OCP_value).
        Default: 100mA.
        Sets the overcurrent protection to the specified value.


- set_OCP_mA(OCP_value)

        Input: Overcurrent protection trigger value (OCP_value).
        Default: 100mA.
        Sets the overcurrent protection to the specified value.

- enable_chopping()

        Input: None.
        Default: None.
        Enables the chopping function. When an overcurrent condition occurs, instead of disabling the output the controller will 'chop' the excess current. Please refer to the installation guide for further information.

- disable_chopping()

        Input: None.
        Default: None.
        Disables the chopping function. When an overcurrent condition occurs, the controller will disable the output voltage. Please refer to the installation guide for further information.


