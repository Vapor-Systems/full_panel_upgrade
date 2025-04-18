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
   - Modifies /boot/config.txt to set USB parameters
   - Comments out dwc2 host mode
   - Adds otg_mode and USB power settings
"""

import os
import re
import subprocess
import sys
import time
import shutil
from typing import Callable, List, Optional, Tuple


def run_command(command: str, sudo: bool = False) -> Tuple[bool, str]:
    """
    Run a shell command and return the result.
    
    Args:
        command: Command to run
        sudo: Whether to run the command with sudo
        
    Returns:
        Tuple[bool, str]: Success status and command output
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


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists and print an error if it doesn't."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return False
    return True



def extract_device_name_from_original() -> Tuple[bool, str]:
    """
    Extract the device name from the original vst_secrets.py file.
    
    Returns:
        Tuple[bool, str]: Success status and device name
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
    file_path: str,
    value: str,
    update_function: Callable[[str, str], str]
) -> bool:
    """
    Update a file with a specific value without user input.
    
    Args:
        file_path: Path to the file to update
        value: Value to use for the update
        update_function: Function that takes the file content and value and returns updated content
        
    Returns:
        bool: True if update was successful, False otherwise
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


def copy_file_if_exists(source_path: str, destination_path: str) -> bool:
    """
    Copy a file from source to destination if it exists.
    
    Args:
        source_path: Source file path
        destination_path: Destination file path
        
    Returns:
        bool: True if file was copied or doesn't exist, False if copy failed
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


def validate_number(value: str) -> bool:
    """Validate that input is a number."""
    try:
        int(value)
        return True
    except ValueError:
        print("Error: Please enter a valid number.")
        return False


def update_device_name_content(content: str, new_name: str) -> str:
    """Update the device name in the content string."""
    return re.sub(
        r'("DEVICE_NAME"\s*:\s*")([^"]*)(")',
        f'\\1{new_name}\\3',
        content
    )


def update_simple_value(content: str, new_value: str) -> str:
    """Update a simple value in quotes."""
    return f'"{new_value}"'


def get_rpi_serial() -> Tuple[bool, str]:
    """
    Get the Raspberry Pi serial number from /proc/cpuinfo.
    
    Returns:
        Tuple[bool, str]: Success status and serial number (last 6 digits, uppercase)
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


def update_boot_config() -> bool:
    """
    Update the boot configuration in /boot/config.txt:
    - Comment out 'dtoverlay=dwc2,dr_mode=host'
    - Add 'otg_mode=1'
    - Add USB power parameters
    
    Returns:
        bool: True if the update was successful, False otherwise
    """
    config_path = "/boot/config.txt"
    
    print(f"Updating boot configuration: {config_path}")
    
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
        
        print(f"Boot configuration updated successfully:")
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


def reboot_system() -> bool:
    """
    Reboot the Raspberry Pi system.
    
    Returns:
        bool: True if the reboot command was executed successfully
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


def update_system_services() -> bool:
    """
    Update system services using files from the 'services' directory.
    
    Returns:
        bool: True if all services were updated successfully, False otherwise
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


def perform_system_update() -> bool:
    """
    Perform the system update operations.
    
    Returns:
        bool: True if all operations were successful, False otherwise
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
        print("Could not extract device name from original file. Using default 'CSX-0'.")
        update_file_with_value(
            "python.new/vst_secrets.py",
            "CSX-0",
            update_device_name_content
        )
    
    # Check if runcycles.json already exists in the target folder
    target_runcycles = "python.new/runcycles.json"
    if not os.path.exists(target_runcycles):
        # Check if runcycles.json exists in the current python folder and copy it if it does
        print("\n-- Checking for existing Run Cycle Count --")
        source_runcycles = "/home/pi/python/runcycles.json"
        if not copy_file_if_exists(source_runcycles, target_runcycles):
            # Create default runcycles.json with value "0" if not found
            print("Creating default runcycles.json with value '0'")
            with open(target_runcycles, 'w') as file:
                file.write('"0"')
    else:
        print(f"\n-- Using existing Run Cycle Count file --")
        try:
            with open(target_runcycles, 'r') as file:
                content = file.read().strip()
                print(f"Using existing run cycle count: {content}")
        except Exception:
            print("Using existing run cycle count file. (Content could not be displayed)")
    
    # Check if profile.json already exists in the target folder
    target_profile = "python.new/profile.json"
    if not os.path.exists(target_profile):
        # Check if profile.json exists in the current python folder and copy it if it does
        print("\n-- Checking for existing Profile --")
        source_profile = "/home/pi/python/profile.json"
        if not copy_file_if_exists(source_profile, target_profile):
            # Create default profile.json with value "CS2" if not found
            print("Creating default profile.json with value 'CS2'")
            with open(target_profile, 'w') as file:
                file.write('"CS2"')
    else:
        print(f"\n-- Using existing Profile file --")
        try:
            with open(target_profile, 'r') as file:
                content = file.read().strip()
                print(f"Using existing profile: {content}")
        except Exception:
            print("Using existing profile file. (Content could not be displayed)")
    
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
    print("9. Update boot configuration (/boot/config.txt)")
    print("10. Reboot system")
    
    # Perform system update
    system_update_success = perform_system_update()
    
    # Update boot configuration
    print("\n-- Updating Boot Configuration --")
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
