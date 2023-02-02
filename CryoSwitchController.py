import time
import matplotlib.pyplot as plt
from libphox import Labphox
import numpy as np
import pandas as pd
import json


class Cryoswitch:

    def __init__(self, debug=False, COM_port='', IP=None, SN=None):
        self.debug = debug
        self.port = COM_port
        self.IP = IP

        self.labphox = Labphox(self.port, debug=self.debug, IP=self.IP, SN=SN)
        self.ports_enabled = self.labphox.N_channel
        self.SN = self.labphox.board_SN

        self.wait_time = 0.1
        self.pulse_duration_ms = 10
        self.converter_voltage = 5
        self.MEASURED_converter_voltage = None
        self.decimals = 2

        self.current_switch_model = 'R583423141'


        self.plot = False
        self.log_wav = False
        self.pulse_logging = True
        self.pulse_logging_filename = 'pulse_logging.txt'
        self.log_pulses_to_display = 2
        self.warning_threshold_current = 60

        self.track_states = True
        self.track_states_file = 'states.json'

        self.__constants()

        if self.track_states:
            self.tracking_init()


    def tracking_init(self):
        file = open(self.track_states_file)
        states = json.load(file)
        file.close()
        if self.SN not in states.keys():
            states[self.SN] = states['SN']

            with open(self.track_states_file, 'w') as outfile:
                json.dump(states, outfile)

    def __constants(self):
        self.ADC_12B_res = 4095

        self.bv_R1 = 68
        self.bv_R2 = 100
        self.bv_ADC = 3

        self.converter_divider = 11
        self.converter_ADC = 10

        self.current_sense_R = 1

    def set_FW_upgrade_mode(self):
        self.labphox.reset_cmd('boot')

    def flash(self):
        reply = input('Are you sure you want to flash the device?')
        if 'Y' in reply.upper():
            self.set_FW_upgrade_mode()
            time.sleep(5)
            self.labphox.FLASH_utils()
        else:
            print('Aborting flash sequence...')

    def reset(self):
        self.labphox.reset_cmd('reset')
        time.sleep(3)

    def reconnect(self):
        self.labphox.connect()

    def enable_5V(self):
        self.labphox.gpio_cmd('EN_5V', 1)

    def disable_5V(self):
        self.labphox.gpio_cmd('EN_5V', 0)

    def enable_3V3(self):
        self.labphox.gpio_cmd('EN_3V3', 1)

    def disable_3V3(self):
        self.labphox.gpio_cmd('EN_3V3', 0)

    def get_converter_voltage(self):
        converter_gain = self.labphox.adc_ref * self.converter_divider / self.ADC_12B_res
        self.labphox.ADC_cmd('select', self.converter_ADC)
        converter_voltage = round(self.labphox.ADC_cmd('get') * converter_gain, self.decimals)
        self.MEASURED_converter_voltage = converter_voltage
        return converter_voltage

    def get_bias_voltage(self):
        bias_gain = self.labphox.adc_ref * ((self.bv_R2 + self.bv_R1) / self.bv_R1) / self.ADC_12B_res
        bias_offset = self.labphox.adc_ref*self.bv_R2/self.bv_R1

        self.labphox.ADC_cmd('select', self.bv_ADC)
        time.sleep(self.wait_time)
        bias_voltage = self.labphox.ADC_cmd('get')*bias_gain-bias_offset

        return bias_voltage

    def check_voltage(self, measured_voltage, target_voltage, tolerance=0.1, pre_str=''):
        error = abs((measured_voltage-target_voltage)/target_voltage)
        if error > tolerance:
            print(pre_str, 'failed to set voltage, measured voltage', round(measured_voltage, self.decimals))
            return False
        else:
            print(pre_str, 'voltage set to', round(measured_voltage, self.decimals), 'V')
            return True

    def get_HW_revision(self):
        pass

    def enable_negative_supply(self, verbose=False):
        self.labphox.gpio_cmd('EN_CHGP', 1)
        time.sleep(2)
        bias_voltage = self.get_bias_voltage()
        if verbose:
            self.check_voltage(bias_voltage, -5, tolerance=0.1, pre_str='BIAS:')
        return bias_voltage

    def disable_negative_supply(self):
        self.labphox.gpio_cmd('EN_CHGP', 0)
        return self.get_bias_voltage()

    def set_output_voltage(self, Vout, verbose=False):
        if 5 <= Vout <= 28:
            self.converter_voltage = Vout
            if Vout > 10:
                self.disable_negative_supply()
            else:
                self.enable_negative_supply()

            self.labphox.DAC_cmd('on', DAC=1)

            VREF = 1.23
            R1 = 500000
            R2 = 500000
            Rf = 15000
            code = int((VREF - (Vout - VREF * (1 + (R1 / R2)))*(Rf/R1))*(self.ADC_12B_res/self.labphox.adc_ref))

            if code < 550 or code > 1500:
                return False
            else:
                self.labphox.DAC_cmd('set', DAC=1, value=code)

                time.sleep(1)
                measured_voltage = self.get_converter_voltage()
                tolerance = 0.1
                if verbose:
                    self.check_voltage(measured_voltage, Vout, tolerance=0.1, pre_str='CONVERTER:')
                print("CONVERTER_STAT:", str(measured_voltage) + 'V')
                return measured_voltage

        else:
            print('Voltage outside of range (5-28V)')

    def enable_output_channels(self):
        self.labphox.IO_expander_cmd('on')

    def disable_output_channels(self):
        self.labphox.IO_expander_cmd('off')

    def enable_converter(self):
        self.labphox.DAC_cmd('set', DAC=1, value=1500)
        self.labphox.DAC_cmd('on', DAC=1)
        self.labphox.gpio_cmd('PWR_EN', 1)
        self.labphox.gpio_cmd('DCDC_EN', 1)

        self.set_output_voltage(self.converter_voltage)

    def disable_converter(self):
        self.labphox.gpio_cmd('DCDC_EN', 0)
        self.labphox.DAC_cmd('set', DAC=1, value=1500)

        self.labphox.gpio_cmd('PWR_EN', 0)

    def enable_OCP(self):
        self.labphox.DAC_cmd('set', DAC=2, value=1500)

        self.labphox.DAC_cmd('on', DAC=2)
        self.set_OCP_mA(100)

    def reset_OCP(self):
        self.labphox.gpio_cmd('CHOPPING_EN', 1)
        self.labphox.gpio_cmd('CHOPPING_EN', 0)

    def set_OCP_mA(self, value):
        DAC_reg = int(value*(self.current_sense_R*20*self.ADC_12B_res/(2*1000*self.labphox.adc_ref)))

        if 0 < DAC_reg < 4095:
            self.labphox.DAC_cmd('set', DAC=2, value=DAC_reg)
        else:
            print('Over current protection outside of range')

    def enable_chopping(self):
        self.labphox.gpio_cmd('CHOPPING_EN', 1)

    def disable_chopping(self):
        self.labphox.gpio_cmd('CHOPPING_EN', 0)

    def reset_output_supervisor(self):
        self.disable_converter()
        self.labphox.gpio_cmd('FORCE_PWR_EN', 1)
        time.sleep(1)
        self.labphox.gpio_cmd('FORCE_PWR_EN', 0)
        self.enable_converter()

    def get_output_state(self):
        return self.labphox.gpio_cmd('PWR_STATUS')

    def set_pulse_duration_ms(self, ms_duration):
        self.pulse_duration_ms = ms_duration
        pulse_offset = 100
        self.labphox.timer_cmd('duration', round(ms_duration*100 + pulse_offset))

    def send_pulse(self, plot=False):

        sampling_freq = 28000
        sampling_period = 1/sampling_freq
        current_gain = 1000 * self.labphox.adc_ref / (self.current_sense_R * 20 * 255)

        current_data = self.labphox.application_cmd('pulse', 1)

        if plot or self.plot:
            edge = np.argmax(current_data>0)
            current_data = current_data[edge:]
            data_points = len(current_data)
            x_axis = np.linspace(0, data_points*sampling_period, data_points)*1000
            plt.plot(x_axis, current_data*current_gain)
            plt.xlabel('Time [ms]')
            plt.ylabel('Current [mA]')

            # if self.current_switch_model == 'R583423141':
            #     plt.ylim(0, 100)
            # elif self.current_switch_model == 'R573423600':
            #     plt.ylim(0, 200)
            plt.grid()
            plt.show()
        return current_data*current_gain


    def select_switch_model(self, model='R583423141'):

        if model.upper() == 'R583423141'.upper():
            self.current_switch_model = 'R583423141'
            self.labphox.IO_expander_cmd('type', value=1)
            self.enable_output_channels()

        elif model.upper() == 'R573423600'.upper():
            self.current_switch_model = 'R573423600'
            self.labphox.IO_expander_cmd('type', value=2)
            self.enable_output_channels()


    def select_output_channel(self, port, number, polarity):
        if 0 < number < 7:
            number = number - 1
            if polarity:
                self.labphox.IO_expander_cmd('connect', port, number)
            else:
                self.labphox.IO_expander_cmd('disconnect', port, number)
        else:
            print('SW out of range')

    def select_and_pulse(self, port, contact, polarity):
        if self.track_states:
            self.save_switch_state(port, contact, polarity)

        if polarity:
            self.select_output_channel(port, contact, 1)
        else:
            self.select_output_channel(port, contact, 0)

        ##time.sleep(1)
        current_profile = self.send_pulse()
        self.disable_output_channels()

        if self.pulse_logging:
            self.log_pulse(port, contact, polarity, current_profile.max())
        if self.log_wav:
            self.log_waveform(port, contact, polarity, current_profile)
        return current_profile

    def save_switch_state(self, port, contact, polarity):
        file = open(self.track_states_file)
        states = json.load(file)
        file.close()

        SN = self.SN
        port = 'port_' + str(port)
        contact = 'contact_' + str(contact)
        if SN in states.keys():
            states[SN][port][contact] = polarity

            with open(self.track_states_file, 'w') as outfile:
                json.dump(states, outfile)


    def log_waveform(self, port, contact, polarity, current_profile):
        current_data = pd.DataFrame({'current_wav': current_profile})
        current_data.to_csv(
            'data/' + str(int(time.time())) + '_' + str(int(self.MEASURED_converter_voltage)) + '_' + str(port) + str(
                contact) + '_' + str(polarity) + '.csv')

    def log_pulse(self, port, contact, polarity, max_current):
        if polarity:
            direction = 'Connect   '
        else:
            direction = 'Disconnect'

        pulse_string = direction + '-> Port:' + port + '-' + str(contact) + ', CurrentMax:' + str(round(max_current)) + ' Timestamp:' + str(int(time.time()))

        if max_current < self.warning_threshold_current:
            warning_string = ' *Warnings: Low current detected!'
        else:
            warning_string = ''

        with open(self.pulse_logging_filename, 'a') as logging_file:
            logging_file.write(pulse_string + warning_string + '\n')

    def get_pulse_history(self, port=None, number_pulses=None):
        if not number_pulses:
            number_pulses = self.log_pulses_to_display

        with open(self.pulse_logging_filename, 'r') as logging_file:
            pulse_info = logging_file.readlines()

        list_for_display = []
        counter = 0
        for idx, pulse in enumerate(pulse_info):
            pulse = pulse_info[-idx-1]
            if port:
                if "Port:" + port + "-" in pulse:
                    list_for_display.append(pulse)
                    ##print(pulse, end='')
                    counter += 1
            else:
                ##print(pulse, end='')
                list_for_display.append(pulse)
                counter += 1

            if counter >= number_pulses:
                break

        for idx, pulse in enumerate(list_for_display):
            raw_data = list_for_display[-idx - 1].split(',')
            if '*' in raw_data[-1]:
                extra_text = raw_data[1].split('*')[-1].strip()
                pulse_time = time.localtime(int(raw_data[1].split('*')[0].split(':')[-1].strip()))
            else:
                extra_text = ''
                pulse_time = time.localtime(int(raw_data[1].split(':')[-1].strip()))


            print(raw_data[0] + ', ' + time.strftime("%a %b-%m %H:%M:%S%p", pulse_time) + ' ' + extra_text)

    def connect(self, port, contact):

        send_pulse = False

        if port == 'A' and self.ports_enabled >= 1:
            send_pulse = True
        elif port == 'B' and self.ports_enabled >= 2:
            send_pulse = True
        elif port == 'C' and self.ports_enabled >= 3:
            send_pulse = True
        elif port == 'D' and self.ports_enabled >= 4:
            send_pulse = True
        else:
            print('Port', port, 'not enabled')

        if send_pulse and (0 < contact < 7):
            if self.debug:
                print('Switching port:', port, 'SW:', contact)

            current_profile = self.select_and_pulse(port, contact, 1)
            return current_profile
        else:
            print('Out of range: Port', port)
            return None

    def disconnect(self, port, contact):
        send_pulse = False

        if port == 'A' and self.ports_enabled >= 1:
            send_pulse = True
        elif port == 'B' and self.ports_enabled >= 2:
            send_pulse = True
        elif port == 'C' and self.ports_enabled >= 3:
            send_pulse = True
        elif port == 'D' and self.ports_enabled >= 4:
            send_pulse = True
        else:
            print('Port', port, 'not enabled')

        if send_pulse and (0 < contact < 7):
            if self.debug:
                print('Switching port:', port, 'SW:', contact)

            current_profile = self.select_and_pulse(port, contact, 0)
            return current_profile
        else:
            print('Out of range: Port', port)

    def get_power_status(self):
        return self.labphox.gpio_cmd('PWR_STATUS')

    def set_ip(self, add="192.168.1.6"):
        add = add.split('.')
        ip_num_value = 16777216 * int(add[3]) + 65536 * int(add[2]) + 256 * int(add[1]) + int(add[0])
        self.labphox.ETHERNET_cmd('set_ip', ip_num_value)

    def get_ip(self):
        response = self.labphox.ETHERNET_cmd('get_ip')
        add = [0, 0, 0, 0]
        # ip_num_value = 16777216 * int(add[3]) + 65536 * int(add[2]) + 256 * int(add[1]) + int(add[0])
        # self.labphox.ETHERNET_cmd('set_ip', ip_num_value)
        int_ip = int(response['value'])
        add[3] = int(int_ip / 16777216)
        int_ip -= 16777216*add[3]
        add[2] = int(int_ip / 65536)
        int_ip -= 65536 * add[2]
        add[1] = int(int_ip / 256)
        int_ip -= 256 * add[1]
        add[0] = int(int_ip)
        return add

    def start(self):
        print('Initialization...')
        self.labphox.ADC_cmd('start')

        self.enable_3V3()
        self.enable_5V()
        self.enable_OCP()
        self.set_OCP_mA(80)
        self.enable_chopping()

        self.set_pulse_duration_ms(15)

        self.enable_output_channels()
        self.enable_converter()
        self.set_output_voltage(5)

        time.sleep(0.5)
        if not self.get_power_status():
            print('PWR_STAT: Output not enabled')
        else:
            print('PWR_STAT: Ready')




if __name__ == "__main__":

    switch = Cryoswitch() ## -> CryoSwitch class declaration and USB connection
    switch.get_ip()
    switch.get_pulse_history(number_pulses=5, port='A')
    switch.start() ## -> Initialization of the internal hardware
    switch.plot = True ## -> Disable the current plotting function
    switch.set_output_voltage(5) ## -> Set the output pulse voltage to 5V

    switch.connect(port='A', contact=1) ## Connect contact 1 of port A to the common terminal
    switch.disconnect(port='A', contact=1) ## Disconnects contact 1 of port A from the common terminal




