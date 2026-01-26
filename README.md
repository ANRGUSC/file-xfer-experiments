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

## Automated Collection

See `instructions.txt` for step-by-step instructions on setting up hourly data collection via cron on macOS.
