#!/usr/bin/env python3
"""
Configuration Update Tool

This script performs a complete update of the system:
1. Updates configuration values:
   - Device name in vst_secrets.py
   - Run cycle count in runcycles.json (copied from existing if available)
   - Profile in profile.json (copied from existing if available)
   - RPI serial number (last 6 digits) in startup.json
2. Performs system operations:
   - Removes backup directory
   - Copies log file
   - Stops control service
   - Backs up current Python directory
   - Moves new code into place
   - Updates and starts system services
3. Updates boot configuration:
   - For Compute Module 4: Modifies /boot/config.txt to set USB parameters,
     comments out dwc2 host mode, adds otg_mode and USB power settings
   - For Compute Module 3: Verifies and updates configuration as needed
   - For other models: Exits with error
"""

import os
import re
import subprocess
import sys
import time
import shutil

# Configuration template for Compute Module 3
CM3_CONFIG = """
# For more options and information see
# http://www.raspberrypi.org/documentation/configuration/config-txt.md
# Some settings may impact device functionality. See link above for details

# uncomment if you get no picture on HDMI for a default "safe" mode
#hdmi_safe=1

# uncomment this if your display has a black border of unused pixels visible
# and your display can output without overscan
#disable_overscan=1

# uncomment the following to adjust overscan. Use positive numbers if console
# goes off screen, and negative if there is too much border
#overscan_left=16
#overscan_right=16
#overscan_top=16
#overscan_bottom=16

# uncomment to force a console size. By default it will be display's size minus
# overscan.
#framebuffer_width=1280
#framebuffer_height=720

# uncomment if hdmi display is not detected and composite is being output
hdmi_force_hotplug=1

# uncomment to force a specific HDMI mode (this will force VGA)
#hdmi_group=1
#hdmi_mode=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0

# uncomment to force a HDMI mode rather than DVI. This can make audio work in
# DMT (computer monitor) modes
#hdmi_drive=2

# uncomment to increase signal to HDMI, if you have interference, blanking, or
# no display
#config_hdmi_boost=4

# uncomment for composite PAL
#sdtv_mode=2

#uncomment to overclock the arm. 700 MHz is the default.
#arm_freq=800

# Uncomment some or all of these to enable the optional hardware interfaces
dtparam=i2c_arm=on
#dtparam=i2s=on
dtparam=spi=on
# dtparam=i2c2_iknowwhatimdoing
dtparam=uart0=on
dtparam=i2c_baudrate=400000
# Uncomment this to enable the lirc-rpi module
#dtoverlay=lirc-rpi

# Additional overlays and parameters are documented /boot/overlays/README
enable_uart=1
dtoverlay=uart1,txd1_pin=32,rxd1_pin=33
core_freq=250
#dtoverlay=i2c-gpio,i2c_gpio_sda=0,i2c_gpio_scl=1
dtoverlay=pwm-2chan,pin=40,func=4,pin2=41,func2=4
dtoverlay=i2c-rtc,ds3231

# Enable audio (loads snd_bcm2835)
dtparam=audio=on

desired_osc_freq=3700000

loglevels=1
avoid_warnings=1
disable_splash=1
dtoverlay=w1-gpio
display_lcd_rotate=2
display_hdmi_rotate=2
#dtparam=watchdog=on
dtparam=usb_pwr_en
max_usb_current=1
"""


def run_command(command, sudo = False):
    """
    Run a shell command and return the result.
    
    Args:
        command: Command to run
        sudo: Whether to run the command with sudo
        
    Returns:
        A tuple containing (success status, command output)
    """
    try:
        if sudo and os.geteuid() != 0:
            # Prepend sudo if needed and not already running as root
            full_command = f"sudo {command}"
        else:
            full_command = command
            
        print(f"Executing: {full_command}")
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Command failed with error: {result.stderr}")
            return False, result.stderr
            
        return True, result.stdout.strip()
        
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        return False, str(e)


def get_raspberry_pi_model():
    """
    Determine the Raspberry Pi model by checking hardware information.
    
    Returns:
        The Raspberry Pi model: "CM3", "CM4", or "OTHER"
    """
    try:
        success, model_info = run_command("cat /proc/cpuinfo | grep Model")
        if not success or not model_info:
            print("Warning: Could not determine Raspberry Pi model.")
            return "OTHER"
        
        # Check for Compute Module 4
        if "Compute Module 4" in model_info:
            print("Detected Raspberry Pi Compute Module 4")
            return "CM4"
        
        # Check for Compute Module 3
        if "Compute Module 3" in model_info or "Compute Module 3+" in model_info:
            print("Detected Raspberry Pi Compute Module 3")
            return "CM3"
        
        # If we get here, it's some other model
        print(f"Detected Raspberry Pi model: {model_info}")
        return "OTHER"
        
    except Exception as e:
        print(f"Error detecting Raspberry Pi model: {str(e)}")
        return "OTHER"


def check_file_exists(file_path):
    """Check if a file exists and print an error if it doesn't."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return False
    return True


def extract_device_name_from_original():
    """
    Extract the device name from the original vst_secrets.py file.
    
    Returns:
        A tuple containing (success status, device name)
    """
    original_file = "/home/pi/python/vst_secrets.py"
    
    if not os.path.exists(original_file):
        print(f"Warning: Original file '{original_file}' not found.")
        return False, ""
    
    try:
        with open(original_file, 'r') as file:
            content = file.read()
            
        # Extract device name using regex
        match = re.search(r'"DEVICE_NAME"\s*:\s*"([^"]*)"', content)
        if not match:
            print("Error: Could not extract device name from original file.")
            return False, ""
            
        device_name = match.group(1)
        print(f"Extracted device name from original file: {device_name}")
        return True, device_name
        
    except Exception as e:
        print(f"Error reading original vst_secrets.py: {str(e)}")
        return False, ""


def update_file_with_value(
    file_path,
    value,
    update_function
):
    """
    Update a file with a specific value without user input.
    
    Args:
        file_path: Path to the file to update
        value: Value to use for the update
        update_function: Function that takes the file content and value and returns updated content
        
    Returns:
        True if update was successful, False otherwise
    """
    if not check_file_exists(file_path):
        return False
    
    try:
        # Read current content
        try:
            with open(file_path, 'r') as file:
                current_content = file.read()
        except UnicodeDecodeError:
            current_content = ""
        
        # Get updated content
        updated_content = update_function(current_content, value)
        
        # Write updated content
        with open(file_path, 'w') as file:
            file.write(updated_content)
        
        print(f"Updated successfully to: {value}")
        return True
        
    except Exception as e:
        print(f"Error updating file: {str(e)}")
        return False


def copy_file_if_exists(source_path, destination_path):
    """
    Copy a file from source to destination if it exists.
    
    Args:
        source_path: Source file path
        destination_path: Destination file path
        
    Returns:
        True if file was copied or doesn't exist, False if copy failed
    """
    if not os.path.exists(source_path):
        print(f"File '{source_path}' does not exist. Prompting for input instead.")
        return False
    
    try:
        shutil.copy2(source_path, destination_path)
        
        # Read the content to display what was copied
        try:
            with open(source_path, 'r') as file:
                content = file.read().strip()
                print(f"Copied from existing file: {content}")
        except Exception:
            print(f"Copied from existing file. (Content could not be displayed)")
        
        return True
    except Exception as e:
        print(f"Error copying file: {str(e)}")
        return False


def validate_number(value):
    """Validate that input is a number."""
    try:
        int(value)
        return True
    except ValueError:
        print("Error: Please enter a valid number.")
        return False


def update_device_name_content(content, new_name):
    """Update the device name in the content string."""
    return re.sub(
        r'("DEVICE_NAME"\s*:\s*")([^"]*)(")',
        f'\\1{new_name}\\3',
        content
    )


def update_simple_value(content, new_value):
    """Update a simple value in quotes."""
    return f'"{new_value}"'


def get_rpi_serial():
    """
    Get the Raspberry Pi serial number from /proc/cpuinfo.
    
    Returns:
        A tuple containing (success status, serial number (last 6 digits, uppercase))
    """
    success, output = run_command("cat /proc/cpuinfo | grep Serial")
    if not success or not output:
        print("Error: Could not read Raspberry Pi serial number.")
        return False, ""
    
    # Extract the serial number
    match = re.search(r'Serial\s*:\s*(\w+)', output)
    if not match:
        print("Error: Serial number format not recognized.")
        return False, ""
    
    # Get the last 6 characters and convert to uppercase
    full_serial = match.group(1)
    last_six = full_serial[-6:].upper()
    
    return True, last_six


def update_boot_config_cm4():
    """
    Update the boot configuration in /boot/config.txt for Compute Module 4:
    - Comment out 'dtoverlay=dwc2,dr_mode=host'
    - Add 'otg_mode=1'
    - Add USB power parameters
    
    Returns:
        True if the update was successful, False otherwise
    """
    config_path = "/boot/config.txt"
    
    print(f"Updating boot configuration for CM4: {config_path}")
    
    try:
        # Read the current content
        success, content = run_command(f"cat {config_path}", sudo=True)
        if not success:
            print(f"Error: Could not read {config_path}")
            return False
        
        # Process the lines
        new_lines = []
        dwc2_line_found = False
        
        for line in content.splitlines():
            # Comment out the dtoverlay=dwc2,dr_mode=host line
            if "dtoverlay=dwc2,dr_mode=host" in line and not line.strip().startswith('#'):
                new_lines.append(f"#{line}")
                dwc2_line_found = True
            else:
                new_lines.append(line)
        
        # Add the new configuration lines
        new_lines.append("otg_mode=1")
        new_lines.append("dtparam=usb_pwr_en")
        new_lines.append("max_usb_current=1")
        
        # Create the new content
        new_content = "\n".join(new_lines)
        
        # Create a temporary file
        temp_file = "/tmp/config.txt.new"
        with open(temp_file, 'w') as file:
            file.write(new_content)
        
        # Move the temporary file to the actual location
        move_success, _ = run_command(f"mv {temp_file} {config_path}", sudo=True)
        if not move_success:
            print(f"Error: Could not update {config_path}")
            return False
        
        print(f"Boot configuration for CM4 updated successfully:")
        if dwc2_line_found:
            print("- Commented out 'dtoverlay=dwc2,dr_mode=host'")
        else:
            print("- Note: 'dtoverlay=dwc2,dr_mode=host' was not found in the config")
        print("- Added 'otg_mode=1'")
        print("- Added USB power parameters")
        
        return True
        
    except Exception as e:
        print(f"Error updating boot configuration: {str(e)}")
        return False


def update_boot_config_cm3():
    """
    Update the boot configuration in /boot/config.txt for Compute Module 3.
    Verifies and ensures the configuration matches the required CM3 configuration.
    
    Returns:
        True if the update was successful, False otherwise
    """
    config_path = "/boot/config.txt"
    
    print(f"Updating boot configuration for CM3: {config_path}")
    
    try:
        # Create a temporary file with the CM3 configuration
        temp_file = "/tmp/config.txt.new"
        with open(temp_file, 'w') as file:
            file.write(CM3_CONFIG)
        
        # Move the temporary file to the actual location
        move_success, _ = run_command(f"mv {temp_file} {config_path}", sudo=True)
        if not move_success:
            print(f"Error: Could not update {config_path}")
            return False
        
        print(f"Boot configuration for CM3 updated successfully with required configuration")
        return True
        
    except Exception as e:
        print(f"Error updating boot configuration for CM3: {str(e)}")
        return False


def update_boot_config():
    """
    Update the boot configuration based on the Raspberry Pi model.
    
    Returns:
        True if the update was successful, False otherwise
    """
    model = get_raspberry_pi_model()
    
    if model == "CM4":
        return update_boot_config_cm4()
    elif model == "CM3":
        return update_boot_config_cm3()
    else:
        print("Error: Cannot update boot configuration - this script only supports Compute Module 3 and 4")
        return False


def reboot_system():
    """
    Reboot the Raspberry Pi system.
    
    Returns:
        True if the reboot command was executed successfully
    """
    print("Preparing to reboot the system...")
    
    try:
        # Execute the reboot command
        success, _ = run_command("reboot", sudo=True)
        if not success:
            print("Error: Failed to reboot the system")
            return False
        
        print("Reboot command executed successfully. System will restart now.")
        return True
        
    except Exception as e:
        print(f"Error during reboot: {str(e)}")
        return False


def update_system_services():
    """
    Update system services using files from the 'services' directory.
    
    Returns:
        True if all services were updated successfully, False otherwise
    """
    src_dir = "services"
    target_dir = "/etc/systemd/system"
    services = ["soracom.service", "saver.service"]
    
    if not os.path.exists(src_dir):
        print(f"Error: Services directory '{src_dir}' does not exist.")
        return False
    
    success = True
    for service in services:
        src_path = os.path.join(src_dir, service)
        if not os.path.exists(src_path):
            print(f"Error: Service file '{src_path}' does not exist.")
            success = False
            continue
        
        # Move service file
        cmd_move = f"cp -f {src_path} {target_dir}/{service}"
        move_success, _ = run_command(cmd_move, sudo=True)
        if not move_success:
            print(f"Failed to move {service}")
            success = False
            continue
        
        print(f"Successfully moved {service} to {target_dir}")
        
        # Reload systemd daemon
        daemon_success, _ = run_command("systemctl daemon-reload", sudo=True)
        if not daemon_success:
            print("Failed to reload systemd daemon")
            success = False
            continue
        
        # Enable service
        enable_success, _ = run_command(f"systemctl enable {service}", sudo=True)
        if not enable_success:
            print(f"Failed to enable {service}")
            success = False
            continue
        
        print(f"{service} enabled successfully")
        
        # Start service
        start_success, _ = run_command(f"systemctl start {service}", sudo=True)
        if not start_success:
            print(f"Failed to start {service}")
            success = False
            continue
        
        print(f"{service} started successfully")
    
    return success


def perform_system_update():
    """
    Perform the system update operations.
    
    Returns:
        True if all operations were successful, False otherwise
    """
    operations = [
        {
            "description": "Removing backup directory",
            "command": "rm -rf /home/pi/python.bak",
            "sudo": False
        },
        {
            "description": "Copying log file",
            "command": "cp /home/pi/python/logfile.csv python.new",
            "sudo": False
        },
        {
            "description": "Stopping control service",
            "command": "systemctl stop control",
            "sudo": True
        },
        {
            "description": "Backing up current Python directory",
            "command": "mv /home/pi/python /home/pi/python.bak",
            "sudo": False
        },
        {
            "description": "Moving new code into place",
            "command": "mv python.new /home/pi/python",
            "sudo": False
        },
        {
            "description": "Truncating first log file",
            "command": "truncate -s 0 /home/pi/python/cp2.log",
            "sudo": False
        },
        {
            "description": "Truncating second log file",
            "command": "truncate -s 0 /home/pi/python/cp2.log",
            "sudo": False
        }
    ]
    
    success = True
    for op in operations:
        print(f"\n-- {op['description']} --")
        op_success, _ = run_command(op["command"], op["sudo"])
        if not op_success:
            print(f"Warning: {op['description']} failed, but continuing with next operation")
            success = False
        time.sleep(1)  # Small delay between operations
    
    # Update system services
    print("\n-- Updating system services --")
    services_success = update_system_services()
    if not services_success:
        print("Warning: Some services could not be updated")
        success = False
    
    # Start control service
    print("\n-- Starting control service --")
    control_success, _ = run_command("systemctl start control", sudo=True)
    if not control_success:
        print("Warning: Failed to start control service")
        success = False
    
    return success


def main():
    """Main function to update all configuration files and perform system update."""
    print("=== Device Configuration and System Update Tool ===")
    
    # Check if running as root for system commands that require sudo
    if os.geteuid() != 0:
        print("Note: Some operations require sudo privileges. You may be prompted for your password.")
    
    # First, check the Raspberry Pi model
    model = get_raspberry_pi_model()
    if model not in ["CM3", "CM4"]:
        print("\nERROR: This update tool only works on Raspberry Pi Compute Module 3 or 4.")
        print("Current device is not a supported model.")
        sys.exit(1)
    
    # First, update the device name by extracting from original file
    print("\n-- Updating Device Name --")
    success, device_name = extract_device_name_from_original()
    
    if success and device_name:
        update_file_with_value(
            "python.new/vst_secrets.py",
            device_name,
            update_device_name_content
        )
    else:
        # Use default name if original not found
        print("Could not extract device name from original file. Using default 'CSX-0000'.")
        update_file_with_value(
            "python.new/vst_secrets.py",
            "CSX-0000",
            update_device_name_content
        )
    
    # Always try to copy from the original, regardless if target already exists
    print("\n-- Copying Run Cycle Count from original --")
    target_runcycles = "python.new/runcycles.json"
    source_runcycles = "/home/pi/python/runcycles.json"
    
    # Remove any existing file in the target directory first
    if os.path.exists(target_runcycles):
        os.remove(target_runcycles)
    
    # Try to copy from original
    if not copy_file_if_exists(source_runcycles, target_runcycles):
        # Create default runcycles.json with value "0" if original not found
        print("Original run cycles not found. Creating default with value '0'")
        with open(target_runcycles, 'w') as file:
            file.write('"0"')
    
    source_profile = "python/profile.json"
    target_profile = "python.new/profile.json"

    # Always try to copy profile.json from python to python.new
    print("\n-- Copying Profile --")
    if os.path.exists(source_profile):
        os.makedirs(os.path.dirname(target_profile), exist_ok=True)
        shutil.copy2(source_profile, target_profile)
        print(f"Copied profile from {source_profile} to {target_profile}")
    else:
        # If source doesn't exist, create default in target
        print(f"{source_profile} not found. Creating default profile in {target_profile} with value 'CS2'")
        os.makedirs(os.path.dirname(target_profile), exist_ok=True)
        with open(target_profile, 'w') as file:
            file.write('"CS8"')
    
    # Handle the Raspberry Pi serial number
    print("\n-- Updating Startup with Raspberry Pi Serial --")
    success, serial = get_rpi_serial()
    if success and serial:
        update_file_with_value(
            "python.new/startup.json",
            serial,
            update_simple_value
        )
    
    # Print informational message about system update operations
    print("\n=== System Update Operations ===")
    print("The following operations will be performed:")
    print("1. Remove backup directory: /home/pi/python.bak")
    print("2. Copy log file to python.new")
    print("3. Stop control service")
    print("4. Backup current Python directory")
    print("5. Move new code into place")
    print("6. Truncate log files")
    print("7. Update system services")
    print("8. Start control service")
    print(f"9. Update boot configuration (/boot/config.txt) for {model}")
    print("10. Reboot system")
    
    # Perform system update
    system_update_success = perform_system_update()
    
    # Update boot configuration
    print(f"\n-- Updating Boot Configuration for {model} --")
    boot_config_success = update_boot_config()
    if not boot_config_success:
        print("Warning: Boot configuration update failed")
        system_update_success = False
    
    if system_update_success:
        print("\nSystem update completed successfully.")
    else:
        print("\nSystem update completed with some warnings or errors.")
    
    # Automatically reboot
    print("\nRebooting the system...")
    reboot_system()


if __name__ == "__main__":
    main()
