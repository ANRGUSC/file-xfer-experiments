Files pertaining to a project to investigate file transfer times initially focusing on scp (how the transfer time depends on file size).

## Scripts

### scpSpeed.py
Data collection script. Runs SCP transfers for various file sizes and saves timing data to JSON.
- Requires test files: `test_1K.bin`, `test_10K.bin`, `test_100K.bin`, `test_1M.bin`, `test_10M.bin`
- Outputs: `results/scp_data{N}.json` (sequentially numbered)

### scpPlot.py
Plotting script. Reads JSON data and generates analysis plots.
- Reads from `results/` folder
- Usage: `python scpPlot.py` (uses latest data) or `python scpPlot.py 3` (uses scp_data3.json)
- Outputs PNG files: `*_boxplot.png`, `*_linear.png`, `*_quadratic.png`

### monotone_quadratic_fit.py
Utility for fitting a monotonically increasing quadratic curve to data points.

### run_scp_collector.sh
Wrapper script for running data collection via cron. See `instructions.txt` for setup.

### plot_datarate.py
Generates data rate analysis plots from the analyzed JSON data. Extracts the linear regression slope `m` (seconds/KB) from each trial's `scp_data_analyzed_*.json`, converts to a data rate via `1/m`, and produces three plots:

1. **`file-data-rate.png`** — SCP data rate (1/m, Mbps) vs time of day
2. **`datarate-vs-iperf.png`** — SCP data rate (1/m) vs iPerf3-measured rate, with linear regression
3. **`datarate-vs-latency.png`** — SCP data rate (1/m) vs median ping latency, with linear regression

**Unit derivation:**
- The linear fit from `scpSpeed1.py` is `y = m*x + b` where `x` is file size in KB and `y` is transfer time in seconds, so `m` has units of seconds/KB.
- Converting to seconds/bit: `m_bits = m / (1024 * 8) = m / 8192`
- Data rate = `1 / m_bits = 8192 / m` bits/sec. Divided by 1e6 gives Mbps.

**Usage:**
```bash
python plot_datarate.py                      # uses results/CronTab215 by default
python plot_datarate.py results/CronTab215   # or specify directory explicitly
```

**Requirements:** Python 3, numpy, matplotlib (install via `pip install numpy matplotlib`).

### plot_graphs.cpp
C++ program that reads `scp_data_analyzed_*.json` files and generates plots via gnuplot. Includes the same data rate graphs (Graphs 8 and 9) plus additional analysis plots (quadratic coefficients, R-squared comparisons, dual-axis time series).

**Usage:**
```bash
g++ -std=c++17 -o plot_graphs plot_graphs.cpp
./plot_graphs                      # uses results/CronTab215 by default
./plot_graphs results/CronTab215   # or specify directory
```

**Requirements:** C++17 compiler, gnuplot.

## Automated Collection

See `instructions.txt` for step-by-step instructions on setting up hourly data collection via cron on macOS.
