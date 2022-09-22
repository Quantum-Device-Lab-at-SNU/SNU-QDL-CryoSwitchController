"""
Created on Fri Jan 21 13:27:57 2022

@author:
"""



from radiall_switch_controller import radiall_switch_controller

print('Write \'start\' to begin')

start = False
while not start:
    in_val = input()
    if in_val.upper() == 'START':
        start = True
    else:
        print('Not a valid command')

print('Starting Radiall switch controller')

controller = radiall_switch_controller()
controller.debug = False

print('Ready')

while (True):
    in_val = input()
    command = in_val.split(' ')

    try:
        if command[0].upper() == 'CONNECT' or command[0].upper() == 'DISCONNECT' or command[0].upper() == 'STATE' or \
                command[0].upper() == 'STOP':
            if command[0].upper() == 'CONNECT':
                controller.connect_switch_port(command[1])
            elif command[0].upper() == 'DISCONNECT':
                controller.disconnect_switch_port(command[1])
            elif command[0].upper() == 'STATE':
                controller.read_switch_state(True)

            elif command[0].upper() == 'STOP':
                break

        else:
            print(in_val, 'Is not a valid command')

    except Exception as e:
        print(e)


