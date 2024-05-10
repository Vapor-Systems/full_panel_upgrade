# Smart Panel Full Upgrade Procedure

*This document outlines the steps required to update the control panel in a Comfile device, from **any version** to **H**. 

## Update Steps

1. **Get Device Information**:
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
	14. Note the *Device Name*, *Run Cycle Count*, and *Profile*.

2. **Prepare the Environment**:
   
