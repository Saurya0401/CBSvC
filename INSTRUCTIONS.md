## Scenario Instructions

### Start Zephyr background process
1. Open an Anaconda prompt
3. Execute `cd C:\Users\aicps\CBSvC\src\zephyr`
4. Execute `./run.cmd`

### Wait for biometrics to stabilize
1. Open an Anaconda prompt
2. Execute `conda activate carlaenv`
3. Execute `cd C:\Users\aicps\CBSvC`
4. Execute `python -m src.driving.zephyr_stream`
5. Check console output and wait until biometrics are accurate and stable
6. Once stable, `Ctrl+C` to stop program and continue with next steps

### Initialize scenario and traffic
_**This step must be completed before starting manual control**_
1. Open an Anaconda prompt
2. Execute `conda activate carlaenv`
3. Execute `cd C:\Users\aicps\CBSvC`
4. (Optional) Execute `python -m src.scenarios.scenario --help` to get info on scenario options
4. Execute `python -m src.scenarios.scenario <scenario_name>`
<br>_NOTE: Don't add_ `--aggression` _or_ `--congestion` _in step 5 as these arguments will override scenario specific settings_

### Start manual control
1. Open an Anaconda prompt
2. Execute `conda activate carlaenv`
3. Execute `cd C:\Users\aicps\CBSvC`
4. Execute `python -m src.driving.manual_control --name <name>`
<br>_NOTE: Using the same name multiple times will override previous files_

### Run each scenario for 10 mins
- Keep an eye out on the biometrics, sometimes it stops working.


## Data Instructions

Data logs are stored in `src/logs` as `.csv` files.

### Filter redundant data
Execute `python -m src.data.filter_data`
- Run without any arguments to filter all logs from `src\logs`
- Use `-d <directory>` to filter all logs from `<directory>`. Filtered logs will be stored in `src\logs\filtered`.
- Use `-f <log file>` to filter `<log file>`. Filtered log file will be stored as `<log file>_filtered.csv`.
- Use `-i` to interpolate zero values in heart rate and breathing rate. **USE ONLY IF NECESSARY**.
- Execute `python -m src.data.filter_data --help` for more info on command line args.

### Plot data
Execute `python -m src.data.plot_data <log_file_pattern>`
- The program will plot all files whose names have `<log_file_pattern>` in them.
<br>E.g.: `python -m src.data.plot_data person_1` will plot all log files associated with person_1.
- The default directory for log files is `src/logs/filtered`, can be changed by with `--dir <directory>`
- Use `--all` to plot all data in separate graphs
- Use `-d <data 1> <data 2> ...` to plot multiple data in separate graphs.
<br>E.g.: `-d speed throttle` will produce two graphs, time vs speed and time vs throttle.
- Use `-c <data 1> <data 2> ...` to plot multiple data in the same graph.
<br>E.g.: `-c speed throttle` will plot time vs speed and time vs throttle on the same graph.
- Execute `python -m src.data.plot_data --help` for more info on command line args.

### Cluster data
Execute `python -m src.data.cluster_data <scenario_name> <clustering_algorithm>`
- The program will cluster data from all files that have `<scenario_name>` in their name.
<br>E.g.: `python -m src.data.cluster_data night dbscan` will cluster all night driving data with the DBSCAN algorithm.
- Include `--pca <n_components>` to do dimensionality reduction with PCA before clustering. PCA is not performed by default.
- Use `--plot_clustering` to display the data clusters in a scatter plot. Useful for visualizing what the clusters look like.
- Use `--data_cols` to specify which data columns to include while clustering. The default is `speed`, `heart_rate`, `breathing_rate`.
<br>E.g.: `--data_cols speed brake throttle` will include only speed, brake, and throttle data while clustering.
- The default logs directory to take data from is `src/logs/filtered`, can be changed by with `--dir <directory>`
- Use `--parallel` to do KMeans++ optimal cluster detection with parallel computing. This speeds up the process but may cause crashes if there are resource shortages.
- Execute `python -m src.data.cluster_data --help` for more info on command line args.
