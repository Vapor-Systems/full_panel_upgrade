# Smart Panel Full Upgrade Procedure

*This document outlines the steps required to update the control panel in a Comfile device, from **any version** to **H**. 

### Download the Repository:

1. Navigate to the [Panel Upgrade GitHub Repository](https://github.com/Vapor-Systems/full_panel_upgrade.git) 

2. Click the *`Code`* dropdown and select *`Download ZIP`*.

3. Extract the folder somewhere you can keep it on your local PC for good, we will reuse this folder for all future upgrades, this step can be skipped for all other upgrades so long as you still have the files available locally.

### Get Device Information:

1. Navigate to [Soracom.io](https://soracom.io).

2. Click `Login` in the top right corner.

3. Use the following login credentials:
   - *Username*: **`admin@vsthose.com`**
   - *Password*: **`B4ustart!`**

4. Once logged in, click the menu dropdown in the top left corner and select **`SIM Management`**.

5. Select the magnifying glass dropdown in the top left, and check **`Filter by Session Status`**  then select **`Online`**.

6. Locate the device you want to update and check the box to the *left* of it.

7. Scroll to the *right* and select the **`Speed Class`**, on the dropdown select **`s1.4xFast`** and click **`Change Speed Class`**.

8. Now click the **`Actions`** dropdown at the top of the page and select  **`On-demand Remote Access`**.

9. In the overlay popup, change the port to **`5900`**.

10. Find **`VNC`** and click the clipboard to the *right* to copy the URL.

11. Paste the copied URL into *Safari* and hit enter.

12.  Click **`Allow`** when you receive the popup for *Screen Sharing*.

13. On the next screen, enter the password **`b4ustart`** and click *Sign In*, which should open a VNC connection to the device.

14. Note the *`Device Name`*, *`Run Cycle Count`*, and *`Profile`*.
	
## Prepare the Environment:

1. Navigate to the previously extracted repository on your local machine and open it within *`Visual Studio Code`*.

2. In the **`Explorer`** on the *left*, select the arrow beside the **`python.new`** folder, to view the files within.

3. Select *`vst_secrets.py`* to view the file and  update the **`DEVICE_NAME`** to match the name the one previously noted for upgrade (eg. *`CSX-XXXX`*) and save the file.

4. Now, in the same folder, select *`runcycles.json`* and replace this to match the previously noted *`run cycle count`* and save the file.

5. Again, within the same folder,  select *`profiles.json`* and replace this to match the previously noted *`profile`* (eg. *`CSX`*) and save the file.

## SSH Into the Same Device:

1. Head back to Soracom and create a new connection for the same device, this time using *`22`* for the port number.

2. Using **`Termius`** create a new connection, and enter the **`HOSTNAME`** provided by **`Soracom`** into the **`Address`** field, then copy only the digits **after** the semi-colon on the **`IP ADDRESS`** provided by **`Soracom`** and head back to **`Termius`** and paste it into the field following **`SSH on`** and click **`Connect`**.

3. Once connected enter the following command in the terminal and hit enter:

	```bash
    cat /proc/cpuinfo | grep Serial
    ```

4. Highlight the last six digits of the provided serial number.

5. Head back to *`Visual Studio Code`* and open the *`startup.json`* file within the **`python.new`** folder, and replace the current code with the new startup code (this *MUST* be all *CAPS*), then save the file.

## SFTP Into the Device and Update the Files:

1. In **`Termius`** on the *left* select SFTP and pick the connection you just created for ssh above.

2. From your local machine, drag the **`python.new`** and **`services`** folder into the connected device on the *right* (it should be dragged into the *`/home/pi`* directory, which should be shown by default).

3. Reselect the ssh connection on the left to view the terminal again and enter each command below, followed by enter. 

    ```bash
    sudo rm -rf python.bak
    sudo rm -rf python.new/logfile.csv
    cp python/logfile.csv python.new/
    sudo systemctl stop control
    sudo mv python python.bak
    sudo mv python.new python
    cd /home/pi/services
    sudo chown +x updater.sh
    ./updater.sh
    sudo systemctl start control

    ```

### Final Steps:

1. Head back to your VNC window and ensure the version is now **`H`**, the device is **`Unlocked`**, and *`run cycle count`*, *`profile`*, and *`device name`* all appear as intended.

2. **Update Soracom Information**: Make necessary updates to Soracom device details to reflect the H version and change Speed Class back to slow.

3. **Update Zoho Information**: Update Zoho entry for device.