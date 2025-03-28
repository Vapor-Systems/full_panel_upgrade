#!/usr/bin/env python3
"""
Configuration Update Tool

This script performs a complete update of the system:
1. Updates configuration values:
   - Device name in vst_secrets.py
   - Run cycle count in runcycles.json
   - Profile in profile.json
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


def update_file(
    file_path: str,
    prompt: str,
    update_function: Callable[[str, str], Optional[str]],
    validator: Optional[Callable[[str], bool]] = None
) -> bool:
    """
    Generic function to update a file based on user input.
    
    Args:
        file_path: Path to the file to update
        prompt: Text to display when asking for user input
        update_function: Function that takes the file content and user input and returns updated content
        validator: Optional function to validate user input
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if not check_file_exists(file_path):
        return False
    
    try:
        # Get user input
        user_input = input(prompt)
        
        # Validate input if a validator was provided
        if validator and not validator(user_input):
            return False
        
        # Read current content if needed by the update function
        try:
            with open(file_path, 'r') as file:
                current_content = file.read()
        except UnicodeDecodeError:
            current_content = ""
        
        # Get updated content
        updated_content = update_function(current_content, user_input)
        
        # Write updated content
        with open(file_path, 'w') as file:
            file.write(updated_content)
        
        print(f"Updated successfully to: {user_input}")
        return True
        
    except Exception as e:
        print(f"Error updating file: {str(e)}")
        return False


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
    
    # Define the files and update operations for user input
    operations = [
        {
            "title": "Updating Device Name",
            "file_path": "python.new/vst_secrets.py",
            "prompt": "Enter new device name: ",
            "function": update_device_name_content,
            "validator": None
        },
        {
            "title": "Updating Run Cycle Count",
            "file_path": "python.new/runcycles.json",
            "prompt": "Enter new run cycle count: ",
            "function": update_simple_value,
            "validator": validate_number
        },
        {
            "title": "Updating Profile",
            "file_path": "python.new/profile.json",
            "prompt": "Enter new profile value: ",
            "function": update_simple_value,
            "validator": None
        }
    ]
    
    # Execute each configuration operation
    for op in operations:
        print(f"\n-- {op['title']} --")
        update_file(
            op["file_path"],
            op["prompt"],
            op["function"],
            op["validator"]
        )
    
    # Handle the Raspberry Pi serial number
    print("\n-- Updating Startup with Raspberry Pi Serial --")
    success, serial = get_rpi_serial()
    if success and serial:
        update_file_with_value(
            "python.new/startup.json",
            serial,
            update_simple_value
        )
    
    # Confirm before proceeding with system update
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
    
    proceed = input("\nDo you want to proceed with system update? (y/n): ")
    if proceed.lower() != 'y':
        print("System update cancelled. Configuration changes have been applied.")
        return
    
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
    
    # Ask if user wants to reboot now
    reboot_now = input("\nDo you want to reboot the system now? (y/n): ")
    if reboot_now.lower() == 'y':
        print("\nRebooting the system...")
        reboot_system()
    else:
        print("\nUpdate process completed. Please reboot the system manually to apply all changes.")


if __name__ == "__main__":
    main()
