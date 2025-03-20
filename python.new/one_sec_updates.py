def one_sec_updates():

    '''These are all the things to do once every second'''
   
    global cont
    global dt
    global run_cyc
    global alarms
    global locked
    global kickstart_timer
    global kickstart_time
    global run_step
    global run_timer
    global run_steps
    global step_count
    global accum_time
    global mode
    global run_mode
    global cycle_time
    global reboot_time
    global elapsed_test_time
    global manual_purge_mode
    global manual_purge_count
    global event
    global special_run_count
     
    cycle_timer = time.time()

    try: event
    except NameError: event = "None"

    try: critical
    except NameError: critical = False

    cur_mode = 0
    step_time = 0

    reboot_time = check_reboot(reboot_time)

    cont2 = load_controller()

    if alarms['sd_card_alarm']:
        logging.error("USB Flash media not found.")
        #beep()

        if profile == 'CS8': 
            if alarms['buzzer_silenced'] == False:
                beep()
                window['sb'].update(visible=True)
                window.read(timeout=1)

      
    dt = datetime.now()

    window['datetime'].update(dt.strftime("%m/%d/%Y %H:%M"))
    window.read(timeout=1)

    if 'test_purge_mode' not in cont2:
        cont2['test_purge_mode'] = None
        save_cont(cont2)

    elif cont['test_mode'] == True:
        if DEBUGGING:

            print(f'##########################')    
            print(f'## Test Mode ACTIVATED. ##')
            print(f'##########################')  

    else:
        if DEBUGGING:

            print(f'##############################')  
            print(f'## Normal Mode:             ##')  
            print(f'## Test Mode NOT Activated. ##')
            print(f'##############################')  


    if cont2['test_purge_mode'] and not cont['test_purge_mode']:
        if DEBUGGING:

            print(f'#########################################')  
            print(f'## Purge Mode:                         ##')  
            print(f'## Test Mode NOT Activated.            ##')
            print(f'## Entering PURGE Mode from Remote...  ##')
            print(f'#########################################') 

        cont['test_purge_mode'] = True
        manual_purge_on()

    if cont['test_purge_mode'] == True and cont2['test_purge_mode'] == False:
        if DEBUGGING:

            print(f'#########################################')  
            print(f'## Purge Mode:                         ##')  
            print(f'## Test Mode NOT Activated.            ##')
            print(f'## Exiting PURGE Mode from Remote...   ##')
            print(f'#########################################') 

        cont['test_purge_mode'] = False
        manual_purge_off()
        save_cont(cont2)

    pressure_sensor_alarm(cont['pressure'])

    if cont["test_mode"]:
    
        if time.time() - alarms['test_start_timer'] < HOURS4:
            #cont['was_test_mode'] = cont['test_mode']
            test_mode()

        else:
            alarms['test_start_timer'] = 0.0
            cont['test_mode'] = False
            #cont['was_test_mode'] = False
            all_stop()

    else:
        pass

    if profile == 'CS8' or profile == 'CS12':
        zero_pressure_alarm(cont['pressure'])
        low_pressure_alarm(cont['pressure'])
        high_pressure_alarm(cont['pressure'])
        var_pressure_alarm(cont['pressure'])

        alarms = check_alarms(alarms)

    cont['faults'] = create_faultcode(alarms)

    alarms = check_buzzer(cont,alarms)

    ### I am changing this logic because I think the else clauses in 92X and below might be allowng the GM to run even if there is a vacpump failure.

    critical = critical_alarm()

    if not critical and cont["pressure"] > LOW_PRESSURE_THRESHOLD:

        if run_cyc:   
        
            if run_timer == 0:
                run_timer = time.time()

            ## returns an array of steps consisting of mode and time

            run_steps = run_cycle(run_mode)

            print(f'\n')

            print(f'Step: {bcolors.HEADER}{run_step}{bcolors.ENDC}', end = ' ')
            print(f'Duration: {bcolors.HEADER}{step_time}{bcolors.ENDC}', end = ' ') 
            print(f'Elapsed: {bcolors.HEADER}{accum_time}{bcolors.ENDC}')
            print(f'Mode: {bcolors.HEADER}{cont["mode"]}{bcolors.ENDC}', end = ' ') 
            print(f'Pressure: {bcolors.HEADER}{cont["pressure"]}{bcolors.ENDC}', end = ' ') 
            print(f'Current: {bcolors.HEADER}{cont["current"]}{bcolors.ENDC}', end = ' ') 
            print(f'Faults....: {bcolors.HEADER}{cont["faults"]}{bcolors.ENDC}')
            #print(f'Counter...: {bcolors.HEADER}{cont["curr_counter"]}{bcolors.ENDC}')

            #print(f'\nelapsed: run_step / cycle /  step time : {run_step} / {accum_time} / {step_time}\n')   

            #print(f'Cycle Time: {round(time.time() - cycle_time,2)} sec')
            
            '''
            print(f'\n')
            print(f"Pressure: {cont['pressure']}, Threshold: {LOW_PRESSURE_THRESHOLD}")
            print(f'##########################')
            print(f'## {bcolors.HEADER} Run Mode: {bcolors.WARNING} {run_mode} {bcolors.ENDC}')
            print(f'##########################\n')
            '''
            
            step_count = len(run_steps)
                
            cur_mode,step_time = run_steps[run_step]

            ### Set Vac Pump Alarm Checked 
            if cur_mode == 1:
                cont['vac_pump_alarm_checked'] = False

            accum_time = int(time.time()-run_timer)
            cycle_time = int(time.time()-cycle_timer)

            if 'curr_counter' not in cont:
                cont['curr_counter'] = 0

            logging.info(f'Run Mode: {run_mode}, Relay Mode: {cur_mode}, Run Step: {run_step}, Runcycle: {run_cyc}')
            set_relays(cur_mode)
            
            if time.time() - run_timer > step_time:
                
                print(f'\n### End of Step: {run_step}.')

                if cont["test_mode"]:
                    if (run_mode == 'special_purge') or (run_mode == 'manual_purge'):
                    
                        print(f'Test Mode: Special Purge')
                        
                        special_run_count = 0 

                run_step = run_step + 1

                if run_step >= step_count:


                    ### Probably unnecessary

                    if run_mode == 'manual_purge':
                        run_cyc = False
                        run_step = 0
                        run_timer = 0     

                    #  This section is what to do after the system runs out of steps in a run sequence
                    #  Reset everything
                
                    set_mode(0)  ### reset mode to idle
                    set_relays(0)
                    run_timer = 0
                    run_step = 0         

                    #  Increment the runcycle counter
                    
                    cont['runcycles'] = cont['runcycles'] + 1
                    kickestart_timer = time.time()

                    # store the current runcycle
                    
                    save_runcycles(cont['runcycles'])
                
                    if continuous_mode == True:
                        run_steps = run_cycle(run_mode) ## returns an array of steps consisting of mode and time
                        step_count = len(run_steps)
                        run_step = 0
                        cur_mode,step_time = run_steps[run_step]
                    else:
                        run_cyc = False
                    
                run_timer = time.time()    

        ###  This directive establishes a normal RUN mode

        elif not locked and not run_cyc and (cont['pressure'] >= cont['pressure_set_point']):
            kickstart_timer = time.time() #  Reset Kickstart Timer

            ##  Keep system from running on any screen other than Main or Alarm
            if ((screen_name == "Main Screen") or (screen_name == "Alarm Screen")):

                run_cyc = True
                run_mode = 'run'
                run_step = 0
                run_timer = 0


        elif not run_cyc and time.time() - kickstart_timer > kickstart_elapsed:
            kickstart_timer = time.time() #  Reset Kickstart Timer

            ### Run a complete cycle every 12 hours to keep the Vacuum pump vanes from seizing

            if ((screen_name == "Main Screen") or (screen_name == "Alarm Screen")):
            
                run_cyc = True
                run_mode = 'run'
                run_step = 0
                run_timer = 0

                print(f'{bcolors.HEADER}12-Hour Kickstart: {bcolors.ENDC}') 
                logging.info("12-Hour Kickstart Triggered")

        else:
            pass
            #all_stop()


    ### Save date for interupted run - 10/31/2023
    save_restart(run_cyc, run_step, run_timer, run_mode)

    ##  Added 2022-08-21 to save controller condition to redis on every pass

    save_controller(cont)
    save_alarms(alarms)
