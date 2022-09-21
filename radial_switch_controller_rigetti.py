# -*- coding: utf-8 -*-
"""
Created on Fri Jan 21 13:27:57 2022

@author: 
"""
import time
import logging
import labjack.ljm.ljm as ljm


class radial_switch_controller:

    def __init__(self,labjack_instrument, labjack_pinnames):
        self.lj = labjack_instrument
        self.lj_pinnames = labjack_pinnames
        self.last_switch_time = 0
        self.minimum_time_between_switches = 30  # seconds

    def check_before_switching(self, port):
        if port < 1 or port > 6:
            raise ValueError(f'port number must be between 1-6, not {port}')
        cur_time = time.time()
        if cur_time - self.last_switch_time < self.minimum_time_between_switches:
            raise Exception(
                f'time since last switch ({cur_time - self.last_switch_time:.1f} s) is less than minimum_time_between_switches ({self.minimum_time_between_switches:.0f} s)')

    def connect_switch_port(self, port):
        port = int(port)
        self.check_before_switching(port)
        self._do_switch_raw(port, 1)

    def disconnect_switch_port(self, port):
        port = int(port)
        self.check_before_switching(port)
        self._do_switch_raw(port, 0)
        
    def read_switch_state(self):
        switch_state = {}
        for k,v in self.lj_pinnames.items():
            switch_state[k] = int(self.lj.read_dio_state(v))
        return switch_state

    def _do_switch_raw(self, port, val):
        lj_pin_name = self.lj_pinnames['line_'+str(port)]
        cur_pin_val = int(self.lj.read_dio_state(lj_pin_name))
        if cur_pin_val == val:
            raise Exception(
                'Current labjack pin value is same as target value, i.e the switch is already in target state, or there is a labjack vs swich state mismatch')
        print(
            f'current lj pin {lj_pin_name} value = {cur_pin_val}, switching it to {val}')

        print('switching now')
        self.lj.write_name(lj_pin_name, val)
        self.last_switch_time = time.time()
        print('switching done')


class LJ:
    
    def __init__(self,device='ANY', connection='ANY', identifier = 'ANY'):
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
        
        self.initialisation(device,connection,identifier)
        
        #print('resources = ',self.rm.list_resources())
        
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
        
    def initialisation(self,device,connection,identifier):
        self.lj = ljm.openS(device, connection, identifier)
        info = ljm.getHandleInfo(self.lj)
        self.deviceType=info[0]
        self.connectionType=info[1]
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
        dio_register_state = int(ljm.eReadAddress(self.lj,2800,ljm.constants.UINT32))
        dio_state = dio_register_state & 2**dio_idx > 0
        return dio_state
                       
    def set_static_ip_address(self,ip_address='192.168.1.177',netmask='255.255.255.0'):
        names = ["ETHERNET_IP_DEFAULT", "ETHERNET_SUBNET_DEFAULT",
                 "ETHERNET_GATEWAY_DEFAULT", "ETHERNET_DHCP_ENABLE_DEFAULT"]
        values = [ljm.ipToNumber(ip_address), ljm.ipToNumber(netmask),
                  ljm.ipToNumber("192.168.1.1"), 0]
        ljm.eWriteNames(self.lj, 4, names, values)
        
    def read_name(self,channel_name):
        return ljm.eReadName(self.lj,channel_name)
    
    def write_name(self, channel_name, value):
        ljm.eWriteName(self.lj, channel_name, value)
            

if __name__ == '__main__':
    
    #example of usage
    labjack =  LJ(device = 'T4',connection = 'USB')
    labjack_pins = {
        			'line_1'      : 'EIO0',
                    'line_2'      : 'EIO1',
                    'line_3'      : 'EIO2',
                    'line_4'      : 'EIO3',
                    'line_5'      : 'EIO4',
                    'line_6'      : 'EIO5',
                    }
    
    
    controller = radial_switch_controller(labjack, labjack_pins)
    i=6
    controller.connect_switch_port(i)
    time.sleep(30)
    controller.disconnect_switch_port(i)
    
    


