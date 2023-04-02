# How to Use?

## Har Obtain

### 1. What is HAR?

HAR: <https://toolbox.googleapps.com/apps/har_analyzer/?lang=>

### 2. Packet capture

#### 2.1. Chrome or Edge

1. Press `F12`, `Ctrl + Shift + I`, or from the Chrome menu select `More tools` > `Developer tools`.
2. From the panel that opens at the bottom of your screen, select the `Network tab`.
3. Make sure the `Record` button in the upper left corner of the `Network tab` is shown in **red**.
4. If it's grey, click it once to start recording.
5. Check the box next to `Preserve log`.
   ![Preserve log](/preserve_log.png)
6. Click the `Clear` button to clear out any existing logs from the `Network tab`.
7. Now try to reproduce the task you were trying to do.
8. Once you have reproduced the task, right-click anywhere on the grid of network requests.
9. Select `Save as HAR with Content`.
   ![Save as HAR with Content](/save_har.png)
10. Save the file to your computer.

#### 2.2. Firefox

1. Press `F12` ​(or Go to `Tools` > `Web Developer` > `Network`).
2. Now try to reproduce the task you were trying to do.
3. Right-click on the loaded results.
4. Select Save all as har.

#### 2.3. Windows - Fiddler

1. Open Fiddler, open the `Tools` menu, select `Options`.
2. Select the `HTTPS tab`, check `Capture HTTPS Connects`.
3. Select the `Connections tab`, check `Decrypt HTTPS traffic`.
4. Now try to reproduce the task you were trying to do.
5. export to HAR format - please select HTTPArchive as the export method.

#### 2.4. IOS - Stream

1. Open Stream.
2. Before capture the HTTPS request, you need to install the CA certificate, `setting` > `General` > `About` > `Certificate Trust Settings` to trust the CA certificate.
3. Click the start packet capture button, the phone will automatically pop up the VPN configuration window, and then select Allow.
4. Now try to reproduce the task you were trying to do.
5. On the app page, click Stop Capture to end this capture.
6. export the HAR file.

### 3. Community HAR

1. Click the `Community Template` button to the right of `my template`.
2. Update the repository to get the latest HAR file list.
3. Select the HAR file you want to use and click the `Subscribe` button to subscribe to the template.
4. Modify the template according to your needs.
5. Then jump to `step 5` of [3. Edit the template](#edit-the-template) to continue editing.

## Upload the HAR file

1. Access and login to QD framework.
2. Click the `+` button to the right of `my template`.
3. Upload the HAR file you just saved.
4. Click `upload` to continue.

## Edit the template

::: v-pre

1. Replace the username, password, cookie, header and other parts that change according to the user with a template similar to `{{ username }}`. (templates support **jinja2 syntax**)
2. Use the test panel in request editing to test whether the template is returned correctly, use the correct and wrong user names to test。
3. Fill in `success/failure assertion`, which helps to detect sign-in failures and template failures.
4. When some data from the previous request is needed in the request, variable extraction is used to extract the data through regularization and save it in the environment variable. Use `ab(\w+)cd`, the group selector, to select part of it.
5. Use `__log__` to extract task logs.
6. When all request edits are complete, use `Test` next to the Download button to test the overall.
7. The template being edited will be automatically saved in the browser cache, so don't worry about losing it.
8. Click the `Save` button to save the template.
9. Click the `Download` button to download the template.
:::

## Create scheduled task

1. Click the `+` button to the right of `my task`.
2. Select the template you just created.
3. Fill in the task variables, task interval, task group and task execution time.
4. Click the `Test` button to test the task.
5. Click the Save button to save the task.
