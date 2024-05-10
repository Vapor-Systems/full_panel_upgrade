import PySimpleGUI as sg
import redis
import subprocess
import re
import shutil
import os
import json

config_file = '/home/pi/python/vst_secrets.py'

def change_hostname(new_hostname):
    # Change the hostname using the hostnamectl command
    subprocess.run(['sudo', 'hostnamectl', 'set-hostname', new_hostname], check=True)
    
    # Update the hostname in the /etc/hostname file
    subprocess.run(['sudo', 'sh', '-c', f'echo "{new_hostname}" > /etc/hostname'], check=True)
    
    # Update the hostname in the /etc/hosts file
    subprocess.run(['sudo', 'sed', '-i', f's/127.0.1.1.*/127.0.1.1\t{new_hostname}/', '/etc/hosts'], check=True)


def update_config(file_path, new_device_name):
    # Create a temporary file
    temp_file_path = file_path + ".tmp"

    # Open the original file for reading
    with open(file_path, 'r') as original_file:
        # Open the temporary file for writing
        with open(temp_file_path, 'w') as temp_file:
            # Iterate over the lines of the original file
            for line in original_file:
                # Find and update the DEVICE_NAME line
                if 'DEVICE_NAME' in line:
                    updated_line = re.sub(r'("DEVICE_NAME"\s*:\s*")[^"]*(")',f'"DEVICE_NAME" : "{new_device_name}"', line)
                    temp_file.write(updated_line)
                else:
                    temp_file.write(line)

    # Replace the original file with the temporary file
    shutil.move(temp_file_path, file_path)

    
    
def name_function(arg):
    # Get hostname
    res = subprocess.run(['hostname'], capture_output=True, text=True)
    hostname = res.stdout.strip()

    name = arg

    if 'RND' in hostname and 'CSX' not in name:
        pass
    else:
        if 'CS12' in name:
            device_name = 'CSX' + name[4:]
        elif 'RND' in name:
            device_name = 'RND' + name[3:]
        else:
            device_name = 'CSX' + name[3:]

        print(f'Changing device name to {device_name}')
        update_config(config_file, device_name)
    if 'CS12' in name:
        profile = 'CS12'
    elif 'CSX' in name or 'RND' in name:
        profile = 'CS8'
    else:
        profile = name[:-5]
            
    r.set('profile', f'{profile}')

    # Added by TEA, 6/14/2023  To more accurately save profile now in a JSON file
    with open('/home/pi/python/profile.json', 'w') as outfile:
        json.dump(profile, outfile)

    try:
        change_hostname(device_name)
    except:
        pass

    exit()


def main():
    sg.theme('DarkBlue 15')
    bfont = 'Roboto Black'
    
    profiles = ['CSX-', 'CS2-', 'RND-', 'CS8-', 'CS9-', 'CS12-']
    keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

    layout = [
        [sg.Text('', font=(bfont, 1), size=(1,2))],
        [sg.Column(
            [[sg.Button('Go Back', button_color=('white', 'darkblue'), size=(7, 1), font=(bfont, 12), key='go_back')]],
            expand_x=True, pad=(0, 0))
        ],
        [sg.Text('ENTER PROFILE & DEVICE NAME:', font=(bfont, 18))],
            [sg.Input(size=(22, 3),font=(bfont, 17), justification='center', key='input')],
            [[sg.Button(x, button_color=(y), size=(6, 1), font=(bfont, 18)) for x, y in [('CSX-', 'black'), ('CS2-', 'midnight blue'), ('RND-', 'darkorange3')]]],
            [[sg.Button(x, button_color=(y), size=(6, 1), font=(bfont, 18)) for x, y in [('CS8-', 'tan4'), ('CS9-', 'springgreen4'), ('CS12-', 'brown')]]],
            [[sg.Button(x, size=(6, 1), disabled=True, font=(bfont, 18)) for x in ('1', '2', '3')]],
            [[sg.Button(x, size=(6, 1), disabled=True, font=(bfont, 18)) for x in ('4', '5', '6')]],
            [[sg.Button(x, size=(6, 1), disabled=True, font=(bfont, 18)) for x in ('7', '8', '9')]],
            [[sg.Button(x, size=(6, 1), disabled=True, font=(bfont, 18)) for x in ('SUBMIT', '0', '⌫')]],
            [sg.Text(size=(15, 0), font=(bfont, 18), text_color='red', key='out')]
            ]

    window = sg.Window(
        'Keypad', 
        layout, 
        size=(800,480),
        default_button_element_size=(5, 2), 
        auto_size_buttons=False, element_justification='c', 
        keep_on_top=True, no_titlebar=True
        )

    keys_entered = ''
    
    while True:
        event, values = window.read()
        
        if event == sg.WIN_CLOSED:
            break

        if event == 'go_back':
            exit()
        
        if event == '⌫':
            keys_entered = keys_entered[:-1]
            if 'CS12' in keys_entered and len(keys_entered) < 5:
                keys_entered =''
                [window[x].update(disabled=False) for x in profiles]
                [window[number].update(disabled=True) for number in keys]
            elif 'CS12' not in keys_entered and len(keys_entered) < 4:
                keys_entered = ''
                [window[x].update(disabled=False) for x in profiles]
                [window[number].update(disabled=True) for number in keys]
            window['SUBMIT'].update(disabled=True)
            
        elif event in profiles:
            keys_entered = values['input']
            keys_entered += event
            window['⌫'].update(disabled=False)
            [window[x].update(disabled=True) for x in profiles]
            [window[number].update(disabled=False) for number in keys]
            
        elif event in keys:
            keys_entered = values['input']
            keys_entered += event

            if 'CS12' in keys_entered:
                if len(keys_entered) == 9:
                    [window[x].update(disabled=True) for x in profiles]
                    [window[number].update(disabled=True) for number in keys]
                    window['SUBMIT'].update(disabled=False)

            else:
                if len(keys_entered) == 8:
                    [window[x].update(disabled=True) for x in profiles]
                    [window[number].update(disabled=True) for number in keys]
                    window['SUBMIT'].update(disabled=False)
            
        elif event == 'SUBMIT':
            keys_entered = values['input']
            window['out'].update(keys_entered) 
            name_function(keys_entered)
        window['input'].update(keys_entered)  
        
if __name__ == '__main__':
    r = redis.Redis('localhost', decode_responses=True)
    main()
