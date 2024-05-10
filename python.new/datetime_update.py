import PySimpleGUI as sg
from datetime import datetime
import pytz
import os


WIDTH = 800
HEIGHT = 480
APP_HEIGHT = 300

sg.theme('DarkBlue 15')
ui_font = 'Roboto Black'

# Define the timezones
timezones = {
    'SELECT TIMEZONE': None,
    'Mountain Standard Time': 'US/Mountain',
    'Mountain Daylight Time': 'US/Mountain',
    'Pacific Daylight Time': 'US/Pacific',
    'Eastern Standard Time': 'US/Eastern',
    'Central Standard Time': 'US/Central',
    'Central Daylight Time': 'US/Central'
}



def get_datetime():

    def get_current_time(timezone):
        if timezone:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            return current_time.strftime('%H:%M')
        return ''

    layout = [
        [sg.Column([], size=(WIDTH, (HEIGHT - APP_HEIGHT) // 2))],  # whitespace
        [sg.Column([
            #[sg.Button('other date', size=(15,1), font=(ui_font, 15))],
            [sg.CalendarButton('SELECT DATE', size=(15, 1), font=(ui_font, 15), close_when_date_chosen=True, target='-DATE-', location=(40, 40), no_titlebar=False)],
            [sg.Input(key='-DATE-', size=(10, 1), font=(ui_font, 15), justification='center', enable_events=True)],
            [sg.Text('', size=(10, 1), font=(ui_font, 10))], # whitespace
            [sg.DropDown(list(timezones.keys()), default_value='SELECT TIMEZONE', size=(20, 1), font=(ui_font, 13), key='-TIMEZONE-', enable_events=True, pad=(10, 10))],
            [sg.Input(key='-CURRENT_TIME-', size=(10, 1), font=(ui_font, 15), justification='center', enable_events=True)],
            [sg.Text('', size=(10, 1), font=(ui_font, 10))], # whitespace
            [sg.Button('UPDATE', size=(15, 1), font=(ui_font, 12))],
            [sg.Button('EXIT', size=(10, 1), font=(ui_font, 12))]
        ], pad=(10, 10), element_justification='center')],
        [sg.Column([], size=(WIDTH, (HEIGHT - APP_HEIGHT) // 2))]  # whitespace
    ]

    window = sg.Window('Timezone', layout, size=(WIDTH, HEIGHT), element_justification='center', titlebar_background_color= 'blue', titlebar_text_color='blue',keep_on_top=False,grab_anywhere=True)
    #window.maximize()

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'EXIT'):
            break
            
        elif event == 'other date':
        
            sg.popup_get_date()
            
        elif event == '-DATE-':
            selected_date = values['-DATE-']
            datetime_obj = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
            formatted_date = datetime_obj.strftime('%m/%d/%Y')
            window['-DATE-'].update(formatted_date)

        elif event == '-TIMEZONE-':  # Handle timezone selection event
            timezone = values['-TIMEZONE-']
            current_time = get_current_time(timezones[timezone])
            window['-CURRENT_TIME-'].update(current_time)

        elif event == 'UPDATE':
            # Check if any date values are updated.
            if values['-DATE-']:
                selected_date = values['-DATE-']
                datetime_obj = datetime.strptime(selected_date, '%m/%d/%Y')
                formatted_date = datetime_obj.strftime('%Y-%m-%d')  # Get the date in 'YYYY-MM-DD' format
            else:
                formatted_date = datetime.now().strftime('%Y-%m-%d')  # Get current date in 'YYYY-MM-DD' format

            # Check if any time values are updated.
            if values['-TIMEZONE-']:
                timezone = values['-TIMEZONE-']
                if timezone == 'SELECT TIMEZONE':  # Check if timezone is None
                    current_time = datetime.now().strftime('%H:%M')  # Get current time
                else:
                    current_time = get_current_time(timezones[timezone])
                formatted_time = datetime.strptime(current_time, '%H:%M').strftime('%H:%M')

            # Combine date and time, and set the system date and time
            datetime_str = formatted_date + ' ' + formatted_time
            print(datetime_str)
            #try:
            os.system(f"sudo timedatectl set-ntp false")  # Disable automatic time synchronization
            #except:
            #    pass
            os.system(f"sudo timedatectl set-time '{datetime_str}'")
            break


    window.close()

if __name__ == '__main__':

    get_datetime()
    
    