Patch Notes:


2024-02-16 - CSX-002H (141)

	- added a save calibration between reboots (per Gonzo)

2024-02-13 - CSX-002H (140)

	- Testing Candidate
	
	- Change fast_timer from 0.010 sec to 0.030 to allow i2c bus to calm down.

	- Addded 10ms timing delays between and after every read / write to the i2c bus and reuqest to turn on and off the relays through the bus.
	This significantly reduced the errors that the try/except has to deal with.

2024-02-12 - CSX-002H (139)

	- Testing a version that successfully heals from all i2c Bus issues and provides decent logging information to determin root cause.
	- Fixed the 5-0 Coountdown in the Functionality Test (was 5 to -2)


2024-01-28 - CSX-002H (138)

	- further attempts to isloate the root cause of the i2c bus abruptly failing

2024-01-28 - CSX-002H (137)

	- attempted to add try/except clauses to relay_on/off functions to add logging data to isloate the underlying problem.


2023-11-16 - CSX-002H (136)

        - commented out the restart function to stop masking the i2c reset
        
2023-11-13 - CSX-002H (135)

        - Added function to functions.py to check i2c viability @
          startup and deliver error message.

        - Added function to reset i2c bus if an error is detected
          when changing the state of the motor and valve relays.

2023-11-01 - CSX-002H (134)

        - Pushing Profile into Soracom upload
        - Putting in various fixes and data points to monitor and correct problems we are seeing at Costco sites.

2023-10-24 - CSX-002H (130)

        - Changed Clean Caninster function to end in 15 minutes
        - Added a LOW_PRESSURE Threshold to keep canister from collapsing
        - added feature in monitor.py to see current relay values from IO Board perspective
        - Added hooks in Soracom.py to accomodate changes in monitor.py
        
2023-10-10 - CSX-002H (129
        - Forgot to uncomment buzzer.

2023-9-14 - CSX-002H (128)

        - Fixed the Timer for Test Mode - Set to 4 hours
        - Change the buzzer function to determin CPU and change pin correctly
        - Added Efficiency Test Button to all profiles and removed 5 min timer
        - Adding a Clean Canister Button to all Profiles
        - Added a reboot option 
        - Remove Pressure Limits Button on CS2, CS9, CS12 Startup
        - Added "*" for Passcode display
        - Adding a correct Date / Time function	

2023-8-4 - CSX-002G CP2-100.127

        - Added Alarm Display for System Shutdown for CS12
        - Added rengaging CR6 to prevent shutdown if alarms are cleared


2023-06-22 - CSX-002F - CP2-100.125

        - Added Pressure reading for no sensor @ -99.9
        - Added Alaarm J (256) to transmitted alarms

2023-06-21 - CSX-002F - CP2-100.124
        
        - Removed test mode button on CS12
        - added password protection to test mode with code 1111
        
2023-06-20 - CSX-002F - CP2-100.123

        - added password protection to debog mode with code 1111
        - added password protection for profile change with code 4015

2023-06-19 - CSX-002F - CP2-100.122

        - Fixed Leak Timer so that it will actually stop at 0
        - Fixed Setting of "alarm_silenced" to retain previous value
          when coming back from "Faults & Alarms" screen.
        - Fixed Manual Screen to remove Modem indicator and fixed
          spacing of other items.
        - removed silence 

2023-06-09 - CSX-002F - CP2-100.120

        - Added SD_card alarms as a trgger for starting 72 Hour
          Countdown.
        - Added pressure sensor as a trigger for starting 72 hour
          countdown.
        - Removed Redis Bug that delayed rebooting machine after
          profile change.  Saving profile and runcycles to a JSON file instead
        - removed Letter labels on Alarms.


2023-06-07 - CSX-002E - CP2-100.119

        - Added CS12 Prfofile where only the pressure sensor will
          trigger a 72 hour countdown.
        

2023-05-10 - CP2-100.111

        - Modified alarm_updates() and create_faultcodes() to deliver the corect faultcode 
        and display the correct error conditions for CS9 with focus on the Pressure Sensor
        alarm.

2023-03-23 - SOR-100-103, CP2-100.110, SAVE-100.101

        -Modifications to Saving function to remove all saving of
        JSON data and added SAVING constant to control saving
        between modules. In normal circumstances SAVER.py is now
        responsible for saving logfiles but both other programs can
        step in under operator control for now.


2023-02-28 - SAV-100-100*

        -  Added new program to save data independantly of 
        Soracom or Control - saver.py

2023-02-23 - SOR-100-102

        - Noticed that there was no separation between the time data
          was being recorded locally vs being tranmitted.  Change
         soracom program to allow independant control of timings

        - other misc formatting changes
 
2023-02-22 - CP2-100.108

	- Swapped logic to pressure sensor alarm - enabled silence
	 button		

2022-11-28 - CP2-100.107
 
	- Fixed deviceID.  It nom pulls from the modem's IMEI#
	- Added system to mease hydrocarbons, based on the pressure  and outputted 
	to both the display while in maintenance and to console and
	transmitted with the soracom data as a substitude for the
	current.
	- Fixed the function to erxtract proper local IP address
	- Added function under profile to properly rename device
	- replaced timer() function with time.time() function
	- replaced dependancy on pickle with redis throughout
	- fixed alarm value between CS9 and any other profile



    2022-10-26 - CP3-100.106 - Added Efficiency Test for Colorado Costco Site per Doug

	2022-10-24 - CP2-100.105 - Fixed function in save_to_sd() to add correct timestamp to logfile.csv

	2022-10-21 - CP2-100.104 - Rebuilt buzzer function to use multiprocessing (per Tommy).
				- Changed buzzer protocol per Doug
				- Fixed inability to change Profiles (Problem with cont object initialization.  Tommmy and I are scheduling
					to re-build this next
				- Fixed minor screen positioning

    2022-10-18 - CP2-100.103 - Changed Screen timings to their present values to help minimize button latency.

    2022-10-17 - Removed "Nuisance Alarm" from code as it was not actually duing anything.
                Removed several reference to still- lingering Blues modem functions

    2022-09-02 - Extracted modem string from Soracom.py and used it to update mdoem_status

    2022-09-01 - CP2-100.102 - Changing Beep fun ction within the very tight get_pressure and get_current loops that would send a beep command every
                1/10 of a second when there was no pressure sensor or current sensor attached.  Since we no longer run the beep as a separate process and it
                itself takes 1/10 of a second to function, it was getting in the way of keyboard access on the HMI.

    2022-08-11 - CP2-100.100 - Changed version to be a more compatible build system (per Tony)
                Began changing test mode output to curses library.  Curses is not working well with journactl

                removing dependancy on Blues modem

                making external program - soracom.py to transmit data to soracom independaltly of main control program
                


    
    2022-08-11 - CP2-96K - Fixed Tesst mode and dialed in all parameters to Make a forcced purge cycle after every 2 run cycles and changed this
                from 35 sesconds to a fixed # of runs. Misc Fixes of Test Mode Parameters.

                Fixed the saving of the controller.json file to reflect better and faster timings to the remote system

                Made a first attempt to make a terminal base dashboard that can be accesssed from a commandline or terminal.


    2022-07-22 = 96j - Change Beep function to only trigger for CS8 Profile.  
                Also fixed the logging system to not dump so much crap in the error log file.
                Also fixed the CSV file writing to output both CSV and JSON data

    2022-06-13 - 96I - Adding Profile and place holder for  Frankin mini-jet

    2022-03-30 - 96H - Gold Standard for CS8

    2022-03-22 - 96G - Added responses to manual remote controls
                Doubled the manual purge cycle so I can remove the complexity of counting # of runs
                Added Threshold Constants

    2022-03-18 - Using 96F as the basis for anything new.  
                96E was frozen as Gold Standard for CPX-001B

    2022-03-09 - Changed mapping of current sensor to match the 16bit ADS1015 chip on the 3.3B IO Board
                Replaced the controller.obj pickle file with contorller.json and addded ad function that 
                deletes the controller.obj on power up.

    2022-03-07 - Control96 - Merged in Test mode objects to support Test mode from saved version 95X.

    2022-03-01 - 95G - Changed the Current reading portions of the program to read current every 10 ms and do a rolling average
                and check it at the 35 ssecond mark inside a purge cycle and change the current threshold from 6.9a to 5.0a

   2022-02-28 - Changed modem detection in Main() to recognize modem error on startup

   2022-02-21 - Changed logic to disallow running on any screen other than Main or Maintenance
                Changeds do_timer logic to add externally do_timer = 0 before the system starts run mode
                Added Motor Current to Functionality TEst screen and Manual Mode Screen per Doug   

                ###### MAJOR CHANGE: Changed the logic for one_sec_updates.  Changed the heirarcy of the iff statements,  The way it was
                Might have allowed conitiions to bleed through that would allow rthe GM to run even if the vac pump alarm was triggered
                Test now with unit in office as Control92Y

   2022-02-18 - Added code to fix and use API variable to the Hub
                Added code to allow the timings to be changed for # of runs and length of cycle
                
   2022-02-16 - Added 30 second rolling average in one_second_updates for pressure.

   2022-02-16 - Added fix for load_runcycles() in main()

   2022-02-08 - Changed conditinal statement in One_second_updates() to only run when vacpump Alarm is False

   2022-02-02 - Added fix for all_stop() and run_mode bug
