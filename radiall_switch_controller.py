"""
Created on Fri Jan 21 13:27:57 2022

@author:
"""
import time
import logging
import labjack.ljm.ljm as ljm


class radiall_switch_controller:

    def __init__(self, labjack_instrument=None, labjack_pinnames=None):

        if labjack_instrument:
            self.lj = labjack_instrument
        else:
            self.lj = LJ(device='T4', connection='USB')

        if labjack_pinnames:
            self.lj = labjack_pinnames
        else:
            self.lj_pinnames = {
                'line_1': 'EIO0',
                'line_2': 'EIO1',
                'line_3': 'EIO2',
                'line_4': 'EIO3',
                'line_5': 'EIO4',
                'line_6': 'EIO5',
            }

        self.last_switch_time = 0
        self.minimum_time_between_switches = 30  # seconds

        for port in range(1, 7):
            self.lj.write_name(self.lj_pinnames['line_' + str(port)], 0)

        self.debug = True

    def connect_switch_port(self, port):
        port = int(port)
        self.check_before_switching(port)
        self._do_switch_raw(port, 1)

    def disconnect_switch_port(self, port):
        port = int(port)
        self.check_before_switching(port)
        self._do_switch_raw(port, 0)

    def read_switch_state(self, fig=False):
        switch_state = {}
        for k, v in self.lj_pinnames.items():
            switch_state[k] = int(self.lj.read_dio_state(v))

        if fig:
            self.print_switch_state(switch_state)
        return switch_state

    def check_before_switching(self, port):
        if port < 1 or port > 6:
            raise ValueError(f'ERROR: Port number must be between 1-6, not {port}')
        cur_time = time.time()
        if cur_time - self.last_switch_time < self.minimum_time_between_switches:
            raise Exception(
                f'ERROR: Time since last switch ({cur_time - self.last_switch_time:.1f} s) is less than minimum_time_between_switches ({self.minimum_time_between_switches:.0f} s)')

    def _do_switch_raw(self, port, val):
        lj_pin_name = self.lj_pinnames['line_' + str(port)]
        cur_pin_val = int(self.lj.read_dio_state(lj_pin_name))
        if cur_pin_val == val:
            raise Exception(
                'Current labjack pin value is same as target value, i.e the switch is already in target state, or there is a labjack vs swich state mismatch')

        if self.debug:
            print(f'Current lj pin {lj_pin_name} value = {cur_pin_val}, switching it to {val}')

        print('Switching now')
        self.lj.write_name(lj_pin_name, val)
        self.last_switch_time = time.time()
        print('Switching done')
        print('')

    def print_switch_state(self, sw_state):
        print('')
        print('Switch state')
        for switch in range(1, len(self.lj_pinnames) + 1):
            state = sw_state['line_' + str(switch)]
            if state:
                if switch == 1:
                    print(str(switch) + ' ----' + chr(0x2510))
                else:
                    print(str(switch) + ' ----' + chr(0x2524))
            else:
                print(str(switch) + ' -  -' + chr(0x2502))
        print('      ' + chr(0x2514) + '- IN')
        print('')


class LJ:

    def __init__(self, device='ANY', connection='ANY', identifier='ANY'):
        """
        deviceType: A string containing the type of the device to be
            connected, optionally prepended by "LJM_dt". Possible values
            include "ANY", "T4", "T7", and "DIGIT".
        connectionType: A string containing the type of the connection
            desired, optionally prepended by "LJM_ct". Possible values
            include "ANY", "USB", "TCP", "ETHERNET", and "WIFI".
        identifier: A string identifying the device to be connected or
            "LJM_idANY"/"ANY". This can be a serial number, IP address,
            or device name. Device names may not contain periods.
        """

        logging.info('Connection to the LJ')

        self.initialisation(device, connection, identifier)

        # print('resources = ',self.rm.list_resources())

        logging.info("Initialized")

    def __enter__(self):
        """ Method to allow the use of the with-as statement
        """
        return self

    def __exit__(self, type, value, traceback):
        """ Method to allow the use of the with-as statement
        """
        self.close()

    def close(self):
        logging.info('Disconnecting from LJ')
        ljm.close(self.lj)

    def initialisation(self, device, connection, identifier):
        self.lj = ljm.openS(device, connection, identifier)
        info = ljm.getHandleInfo(self.lj)
        self.deviceType = info[0]
        self.connectionType = info[1]
        logging.info("Opened a LabJack with Device type: %i, Connection type: %i,\n"
                     "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
                     (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

    def read_dio_state(self, channel_name):
        """
        reads a single state of a FIO/EIO/CIO/MIO, without changing its output value if configured as an output
        # https://labjack.com/support/datasheets/t-series/digital-io
        """
        address = ljm.nameToAddress(channel_name)[0]
        dio_idx = address - ljm.nameToAddress('DIO0')[0]
        dio_register_state = int(ljm.eReadAddress(self.lj, 2800, ljm.constants.UINT32))
        dio_state = dio_register_state & 2 ** dio_idx > 0
        return dio_state

    def set_static_ip_address(self, ip_address='192.168.1.177', netmask='255.255.255.0'):
        names = ["ETHERNET_IP_DEFAULT", "ETHERNET_SUBNET_DEFAULT",
                 "ETHERNET_GATEWAY_DEFAULT", "ETHERNET_DHCP_ENABLE_DEFAULT"]
        values = [ljm.ipToNumber(ip_address), ljm.ipToNumber(netmask),
                  ljm.ipToNumber("192.168.1.1"), 0]
        ljm.eWriteNames(self.lj, 4, names, values)

    def read_name(self, channel_name):
        return ljm.eReadName(self.lj, channel_name)

    def write_name(self, channel_name, value):
        ljm.eWriteName(self.lj, channel_name, value)


if __name__ == '__main__':


    # Usage Example

    controller = radiall_switch_controller()  # Create a switch controller instance
    controller.connect_switch_port(1)  # Connects RF input 1 from the common RF terminal
    controller.read_switch_state()  # prints the current switch state
    time.sleep(35)  # Wait at least 30s before the next switching to avoid excessive heating
    controller.disconnect_switch_port(1)  # Disconnect RF input 1 from the common RF terminal
