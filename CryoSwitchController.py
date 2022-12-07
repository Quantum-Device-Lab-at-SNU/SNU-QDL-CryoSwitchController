import time
import matplotlib.pyplot as plt
from libphox import Labphox
import numpy as np

from datetime import datetime


class Cryoswitch:

    def __init__(self, debug=False, port=''):
        self.debug = debug
        self.port = port

        self.labphox = Labphox(self.port, debug=self.debug)
        self.wait_time = 0.5
        self.converter_voltage = 5
        self.MEASURED_converter_voltage = None
        self.decimals = 2

        self.plot = True


    def reset(self):
        self.labphox.reset_cmd('reset')
        time.sleep(1)

    def reconnect(self):
        self.labphox.connect()

    def enable_output_channels(self):
        self.labphox.IO_expander_cmd('on')

    def disable_output_channels(self):
        self.labphox.IO_expander_cmd('off')

    def enable_5V(self):
        self.labphox.gpio_cmd('EN_5V', 1)

    def disable_5V(self):
        self.labphox.gpio_cmd('EN_5V', 0)

    def enable_3V3(self):
        self.labphox.gpio_cmd('EN_3V3', 1)

    def disable_3V3(self):
        self.labphox.gpio_cmd('EN_3V3', 0)


    def get_converter_voltage(self):
        converter_gain = self.labphox.adc_ref * 11 / 4095
        self.labphox.ADC_cmd('select', 10)
        converter_voltage = self.labphox.ADC_cmd('get') * converter_gain
        return converter_voltage


    def get_bias_voltage(self):
        bias_gain = self.labphox.adc_ref*(168/68)/(4095)
        bias_offset = self.labphox.adc_ref*100/68

        self.labphox.ADC_cmd('select', 3)
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


    def set_output_voltage(self, Vout, verbose=False):
        if Vout <= 28 and Vout >= 5:
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
            code = int((VREF - (Vout - VREF * (1 + (R1 / R2)))*(Rf/R1))*(4096/self.labphox.adc_ref))

            if code < 550 or code > 1500:
                return False
            else:
                self.labphox.DAC_cmd('set', DAC=1, value=code)

                time.sleep(1)
                measured_voltage = self.get_converter_voltage()
                tolerance = 0.1
                time.sleep(0.5)
                if verbose:
                    self.check_voltage(measured_voltage, Vout, tolerance=0.1, pre_str='CONVERTER:')
                return measured_voltage

        else:
            print('Voltage outside of range (5-28V)')



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
        DAC_reg = int(value*(20*4096/(2*1000*self.labphox.adc_ref)))
        self.labphox.DAC_cmd('set', DAC=2, value=DAC_reg)


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

    def set_pulse_duration_ms(self, ms_duration):
        pulse_offset = 100
        self.labphox.timer_cmd('duration', round(ms_duration*100 + pulse_offset))

    def send_pulse(self, plot=False):

        sampling_freq = 28000
        sampling_period = 1/sampling_freq
        current_gain = 1000 * self.labphox.adc_ref / (1 * 20 * 255)

        current_data = np.round_(np.array(self.labphox.application_cmd('pulse', 1)), self.decimals)

        if plot or self.plot:
            edge = np.argmax(current_data>0)
            current_data = current_data[edge:]
            data_points = len(current_data)
            x_axis = np.linspace(0, data_points*sampling_period, data_points)*1000
            plt.plot(x_axis, current_data*current_gain)
            plt.xlabel('Time [ms]')
            plt.ylabel('Current [mA]')
            plt.grid()
            plt.show()
        return current_data*current_gain


    def select_output_channel(self, port, number, polarity):
        if (0 < number < 7):
            number = number - 1
            if polarity:
                self.labphox.IO_expander_cmd('connect', port, number)
            else:
                self.labphox.IO_expander_cmd('disconnect', port, number)
        else:
            print('SW out of range')

    def select_and_pulse(self, port, number, polarity):
        if polarity:
            self.select_output_channel(port, number, 1)
        else:
            self.select_output_channel(port, number, 0)

        time.sleep(1)
        current_profile = self.send_pulse()

        self.disable_output_channels()

        return current_profile


    def connect(self, port, sw):

        self.ports_enabled = self.labphox.N_channel
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

        if send_pulse and (0 < sw < 7):
            if self.debug:
                print('Switching port:', port, 'SW:', sw)

            current_profile = self.select_and_pulse(port, sw, 1)
            return current_profile
        else:
            print('Out of range: Port', port)
            return None


    def disconnect(self, port, sw):
        self.ports_enabled = self.labphox.N_channel
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

        if send_pulse and (0 < sw < 7):
            if self.debug:
                print('Switching port:', port, 'SW:', sw)

            current_profile = self.select_and_pulse(port, sw, 0)
            return current_profile
        else:
            print('Out of range: Port', port)


    def set_FW_upgrade_mode(self):
        self.labphox.reset_cmd('boot')
        time.sleep(0.1)
        self.labphox.reset_cmd('reset')


    def get_power_status(self):
        return self.labphox.gpio_cmd('PWR_STATUS')



    def start(self):
        print('Initialization...')
        self.labphox.ADC_cmd('start')

        self.enable_3V3()
        self.enable_5V()
        self.enable_OCP()
        self.disable_chopping()

        self.enable_output_channels()
        self.enable_converter()
        self.set_output_voltage(5)

        time.sleep(0.5)
        if not self.get_power_status():
            print('PWR_STAT: Output not enabled')
        else:
            print('Ready')




if __name__ == "__main__":

    switch = Cryoswitch() ## -> CryoSwitch class declaration and USB connection
    switch.start() ## -> Initialization of the internal hardware
    switch.plot = False ## -> Disable the current plotting function
    switch.set_output_voltage(5) ## -> Set the output pulse function to 5V (depending on the line/fridge resistance)

    switch.connect('A', 1) ## Connect switch 1 of port A to the common terminal
    switch.disconnect('A', 1) ## Disconnects contact 1 of port A from the common terminal
