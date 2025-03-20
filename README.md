# Smart Panel Full Upgrade Procedure

*This document outlines the steps required to update the control panel in a Comfile device, from **any version** to **L**. 

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

14. Take note of the *`Device Name`*, *`Run Cycle Count`*, and *`Profile`* (you'll need these later).
	
## SSH Into the Same Device:

1. Head back to Soracom and create a new connection for the same device, this time using *`22`* for the port number.

2. Using **`Termius`** create a new connection, and enter the **`HOSTNAME`** provided by **`Soracom`** into the **`Address`** field, then copy only the digits **after** the semi-colon on the **`IP ADDRESS`** provided by **`Soracom`** and head back to **`Termius`** and paste it into the field following **`SSH on`** and click **`Connect`**.

3. Once connected enter the following command in the terminal and hit enter:

	```bash
    git clone https://github.com/Vapor-Systems/full_panel_upgrade
    ```

4. Once that completes enter the following command and hit enter:
	```bash
    python3 updater.py
    ```

5. You will be prompted for a device name, run cycle count, and profile. Type each one in and hit enter, ensuring that you've typed it in correctly.

### Final Steps:

1. Head back to your VNC window and ensure the version is now **`L`**, the device is **`Unlocked`**, and *`run cycle count`*, *`profile`*, and *`device name`* all appear as intended.

2. **Update Soracom Information**: Make necessary updates to Soracom device details to reflect the H version and change Speed Class back to slow.

3. **Update Zoho Information**: Update Zoho entry for device.
