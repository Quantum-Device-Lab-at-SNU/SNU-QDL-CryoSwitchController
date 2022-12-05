import serial
import serial.tools.list_ports
import time
import json



class Labphox:


  def __init__(self, port ='', debug=False):
    self.debug = debug
    self.port = port
    self.time_out = 10
    self.log = True

    self.adc_ref = 3.3
    self.N_channel = 0
    self.connect()

  def connect(self):
    if self.port == '':
      for device in serial.tools.list_ports.comports():
        if device.pid == 1812:
          self.PID = device.pid
          if self.debug:
            for i in device:
              print(i)

          try:
            self.serial_com = serial.Serial(device.device)

            self.board_info = ''
            self.board_SN = None
            self.utility_cmd('info')
            print('Connected to LabPHOX', ', PID:', str(self.PID) + ',', self.board_SN)
          except:
            print('ERROR: Couldn\'t connect')

  def input_buffer(self):
    return self.serial_com.inWaiting()

  def flush_input_buffer(self):
    return self.serial_com.flushInput()

  def write(self, cmd):
    if self.log:
      self.logging('actions', cmd)
    self.serial_com.write(cmd)

  def read(self, size):
    data_back = self.serial_com.read(size)
    return data_back

  def read_buffer(self):
    return self.read(self.input_buffer())

  def decode_buffer(self):
    return list(self.read_buffer())

  def debug_func(self, line):
    for i in line:
      print('Debug:', i)


  def read_line(self):
    return self.serial_com.readline()

  def query_line(self, cmd):
    self.write(cmd)
    return self.serial_com.readline()

  def compare_cmd(self, cmd1, cmd2):
    if cmd1.upper() == cmd2.upper():
      return True
    else:
      return False

  def encode(self, value):
    return str(value).encode()

  def check_cmd_OK(self):
    if self.input_buffer():
      if 'K' in self.read(self.input_buffer()).decode().strip():
        return 'OK'

    return False

  def decode_simple_response(self, response):
    return response.decode('UTF-8').strip()

  def parse_response(self):
    ##time.sleep(1)

    initial_time = time.time()
    input_buffer = 0
    while input_buffer == 0:
      input_buffer = self.input_buffer()
      time.sleep(0.1)

      if(time.time() - initial_time) > self.time_out:
        raise Exception("LABPHOX time out exceeded", self.time_out, 's')
    response = self.read_buffer()
    ## possible implementation, but it could break: response.decode().strip('\x00')
    start = 0
    end = 0
    reply_start = 0
    for idx, possible_char in enumerate(response):
      if chr(possible_char) == 'R' or chr(possible_char) == 'W' and not start:
        start = idx
      elif chr(possible_char) == ':':
        reply_start = idx
      elif chr(possible_char) == ';' and not end:
        end = idx
        break

    full_cmd = response[start:end + 1].decode()
    command = response[start:reply_start + 1].decode()
    value = response[reply_start + 1:end].decode()
    if self.debug:
      self.debug_func([full_cmd, value])

    if self.log:
      self.logging('received', full_cmd)

    return {'reply': full_cmd, 'command': command,'value': value}


  def raise_value_mismatch(self):
    print('VALUE MISMATCH!!!')

  def utility_cmd(self, cmd, value=0):
    response = False
    if self.compare_cmd(cmd, 'info'):

      response = self.decode_simple_response(self.query_line(b'W:2:I:;'))
      if 'LabphoX'.upper() in response.upper():
        time.sleep(0.4)
        self.data = self.decode_simple_response(self.read_buffer()).replace('\x00', '').split(';')
        self.board_info = self.data

        for info in self.data:
          if 'HW' in info:
            self.HW = info
          elif 'SN' in info:
            self.board_SN = info
          elif 'SW' in info:
            self.board_FW = info
          elif 'Channels' in info:
            self.N_channel = int(info.split()[1])

    elif self.compare_cmd(cmd, 'connected'):
      self.write(b'W:2:C:;')
      response = self.parse_response()
      return response['value']




    if self.compare_cmd(cmd, 'sleep'):
      self.write(b'W:2:S:' + self.encode(value) + b';')
      response = self.parse_response()




  def DAC_cmd(self, cmd, DAC=1,  value=0):
    response = False

    if DAC == 1:
      sel_DAC = 5
    elif DAC == 2:
      sel_DAC = 8

    if self.compare_cmd(cmd, 'on'):
      self.write(b'W:' + self.encode(sel_DAC) + b':T:1;')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'off'):
      self.write(b'W:' + self.encode(sel_DAC) + b':T:0;')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'set'):
      self.write(b'W:' + self.encode(sel_DAC) + b':S:' + self.encode(value) + b';')
      time.sleep(value/1000)
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'buffer'):
      self.write(b'W:' + self.encode(sel_DAC) + b':B:' + self.encode(value) + b';')
      response = self.parse_response()



  def application_cmd(self, cmd, value=0):
    response = False
    if self.compare_cmd(cmd, 'pulse'):
      self.serial_com.flushInput()
      self.write(b'W:3:T:' + self.encode(value) + b';')
      ##response = self.parse_response()
      time.sleep(3)
      response = self.read_buffer()

      index = 0
      for idx, item in enumerate(response):
        if b'W:3:T:3' in response[:idx]:
          index = idx
          break

      return list(response[index+1:])


    elif self.compare_cmd(cmd, 'acquire'):
      self.write(b'W:3:Q:' + self.encode(value) + b';')
      response = self.parse_response()


    elif self.compare_cmd(cmd, 'voltage'):
      self.write(b'W:3:V:' + self.encode(value) + b';')
      response = self.parse_response()






  def timer_cmd(self, cmd, value=0):
    response = False
    if self.compare_cmd(cmd, 'duration'):

      self.write(b'W:0:A:' + self.encode(value) + b';')
      response = self.parse_response()
      if int(response['value']) != int(value):
        self.raise_value_mismatch()



    # response = self.check_cmd_OK()
    #
    # if self.debug and response:
    #   self.debug_func(response)
    #
    # if response:
    #   return response

  def ADC_cmd(self, cmd, value=0):
    response = False
    if self.compare_cmd(cmd, 'channel'):
      self.write(b'W:4:C:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'start'):
      self.write(b'W:4:T:1;')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'stop'):
      self.write(b'W:4:T:0;')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'select'): ##Select and sample
      self.write(b'W:4:S:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'get'):
      cmd = 'W:4:G:'
      self.flush_input_buffer()
      self.write(cmd.encode() + b';')
      adc_value = -1
      response = self.parse_response()
      if response['command'] == cmd:
        adc_value = int(response['value'])

      return adc_value


    return None



  def gpio_cmd(self, cmd, value=0):
    response = False
    if self.compare_cmd(cmd, 'EN_3V3'):
      self.write(b'W:1:A:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'EN_5V'):
      self.write(b'W:1:B:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'EN_CHGP'):
      self.write(b'W:1:C:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'FORCE_PWR_EN'):
      self.write(b'W:1:D:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'PWR_EN'):
      self.write(b'W:1:E:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'DCDC_EN'):
      self.write(b'W:1:F:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'CHOPPING_EN'):
      self.write(b'W:1:G:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'PWR_STATUS'):
      self.write(b'W:1::3;')
      response = self.parse_response()
      return int(response['value'])

    return None

  def scanI2C(self):
    self.write(b'R:4:T:1;')
    time.sleep(5)
    res = self.read_buffer()
    print(res.decode().strip('-').split('&'))

  def IO_expander_cmd(self, cmd, port='A', value=0):
    response = False
    if self.compare_cmd(cmd, 'connect'):
      self.write(b'W:' + self.encode(port) + b':C:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'disconnect'):
      self.write(b'W:' + self.encode(port) + b':D:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'on'):
      self.write(b'W:6:O:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'off'):
      self.write(b'W:6:U:' + self.encode(value) + b';')
      response = self.parse_response()

    return None


  def reset_cmd(self, cmd):
    if self.compare_cmd(cmd, 'reset'):
      self.write(b'W:7:R:;')
      ##response = self.parse_response()

    elif self.compare_cmd(cmd, 'boot'):
      self.write(b'W:7:B:;')
      response = self.parse_response()

  def EEPROM_cmd(self, cmd, value=0):
    if self.compare_cmd(cmd, 'read'):
      self.write(b'W:9:R:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'read_page'):
      self.write(b'W:9:P:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'write'):
      self.write(b'R:9:W:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'protect'):
      self.write(b'W:9:Q:' + self.encode(value) + b';')
      response = self.parse_response()

    elif self.compare_cmd(cmd, 'cursor'):
      self.write(b'W:9:C:' + self.encode(value) + b';')
      response = self.parse_response()

  def logging(self, list_name, cmd):
    with open('history.json', "r") as history_file:
      data = json.load(history_file)

    if type(cmd) == str:
      data_to_append = cmd
    elif type(cmd) == bytes:
      data_to_append = cmd.decode()

    if list_name in data.keys():
      data[list_name].append({'data': data_to_append, 'date': time.time()})
    else:
      data[list_name] = [{'data': data_to_append, 'date': time.time()}]


    with open('history.json', "w") as file:
      json.dump(data, file)

if __name__ == "__main__":

  cryoswitch = Labphox()



  current_data = cryoswitch.application_cmd('pulse')

  cryoswitch.timer_cmd('duration', 1002)
  cryoswitch.DAC_cmd('on')
  cryoswitch.DAC_cmd('set', 1000)
  cryoswitch.application_cmd('pulse', 1)

  cryoswitch.ADC_cmd('select', 11)
  time.sleep(1)
  print(cryoswitch.ADC_cmd('get'))
  print()
