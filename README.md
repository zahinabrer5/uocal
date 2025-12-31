# uocal
A Python script that converts your uOttawa schedule into a `.ics` file importable by Google Calendar, Apple Calendar or any other calendar app supporting `.ics` files.

## Usage
0. Install [Python](https://python.org).
1. Clone the repo.
2. Save your schedule from uOZone:
   1. Open the application "My Class Schedule" on uOZone.
   2. Choose your desired semester.
   3. Make sure you use the **List View** option and **NOT** the Weekly Calendar View option.
   4. Right click the page and click "Save as..."
   5. You should see a new folder where you saved the page on your computer.
   6. Inside that folder, there's a file named `SA_LEARNER_SERVICES.SSR_SSENRL_LIST.html`. Rename it to `schedule.html` and move it to the same directory as the Python script.

3. On Ubuntu, WSL or MacOS, do the following. On Windows, replace `pip3` with `pip` and `python3` with `python`.
```
cd uocal
pip3 install -r requirements.txt
python3 main.py schedule.html
```

4. Now, you should see a `schedule.ics` file appear in the same directory as the Python script. This file can be imported into Google Calendar, Apple Calendar or any other calendar app supporting `.ics` files.
