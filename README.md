# Radial Switch Controller

## Project structure



## Getting started

This repository holds the QP-CryoSwitch Controller commpatible software. It is designed to be used with the QP-CryoSwitch Controller and Labjack T4.


## Installation
- First, install the [LJM](https://labjack.com/support/software/installers/ljm) labjack software on your computer. A copy is saved 

- Second, install the python "labjack-ljm" package. You can do so by running the folowing pip command:

```
pip install labjack-ljm 
```
For more details, please visit the Labjack-python [Support Page](https://labjack.com/support/software/examples/ljm/python).

## Library Usage

The radial_switch_controller class is an easy way of interfacing between the QP-CryoSwitch Controller and the Labjack T4.

**_NOTE:_** Since the Radiall switch [R583423141](https://www.radiall.com/cryogenic-sp6t-ramses-sma-18ghz-latching-28vdc-d-sub-male-connector-bipolar-actuator-command-r583423141.html) has a latching actuator, it's important to start the program with the switches in a known state. By default, the program assumes all actuators are in open or disconnected state.


The class contains 3 main functions:
- connect_switch_port(port) 

        Input: port => int or str (1..6)
        Connects the RF input (1..6) to the common terminal

- disconnect_switch_port(port) 

        Input: port => int or str (1..6)
        Disconnects the RF input (1..6) to the common terminal

- read_switch_state() 

        returns: switch states => dictionary containing the state of each switch (1..6) 
