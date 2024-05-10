#!/bin/bash

# Define the source and target directories.
src_dir="services/"
target_dir="/etc/systemd/system/"

# Define the services.
services=("soracom.service" "saver.service")

# Loop over the services.
for service in "${services[@]}"; do
    # Move or replace the service files
    if mv -f "$src_dir/$service" "$target_dir/$service"; then
        echo "Successfully moved $service to $target_dir"
    else
        echo "Failed to move $service"
        continue
    fi

    # Enable and start the services.
    if systemctl enable "$service"; then
        echo "$service enabled successfully"
    else
        echo "Failed to enable $service"
        continue
    fi

    if systemctl start "$service"; then
        echo "$service started successfully"
    else
        echo "Failed to start $service"
    fi
done

# Reload the systemd daemon.
systemctl daemon-reload