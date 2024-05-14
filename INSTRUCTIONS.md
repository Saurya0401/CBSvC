## Scenario Instructions

### Start Zephyr background process
1. Open an Anaconda prompt
2. Execute `conda activate carlaenv`
3. Execute `cd C:\Users\aicps\WindowsNoEditor\PythonAPI\examples\App_Zephyr_main`
4. Execute `run.cmd`

### Initialize scenario and traffic
_**This step must be completed before starting manual control**_
1. Open an Anaconda prompt
2. Execute `conda activate carlaenv`
3. Execute `cd C:\Users\aicps\CBSvC`
4. (Optional) Execute `python -m src.scenarios.scenario --help` to get info on scenario options
4. Execute `python -m src.scenarios.scenario <scenario_name>`
_NOTE: Don't add_ `--aggression` _or_ `--congestion` _in step 5 as these arguments will override scenario specific settings_

### Start manual control
1. Open an Anaconda prompt
2. Execute `conda activate carlaenv`
3. Execute `cd C:\Users\aicps\CBSvC`
4. Execute `python -m src.driving.manual_control --name <name>`
_NOTE: Using the same name multiple times will override previous files. If_ `--name` _is not provided, the log file's name will be a timestamp of when manual control was started._

### Run each scenario for 10 mins
- Keep an eye out on the biometrics, sometimes it stops working.