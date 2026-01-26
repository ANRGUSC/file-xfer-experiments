import json
import os
import re
import glob
import sys
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from monotone_quadratic_fit import monotone_quadratic_fit

results_dir = "results"

# Determine which data file to use
if len(sys.argv) > 1:
    # Use specified number
    data_num = int(sys.argv[1])
else:
    # Find the latest (highest numbered) JSON file
    existing_files = glob.glob(os.path.join(results_dir, "scp_data*.json"))
    if not existing_files:
        print("No data files found in results folder.")
        sys.exit(1)
    max_num = 0
    for f in existing_files:
        match = re.search(r'scp_data(\d+)\.json$', f)
        if match:
            max_num = max(max_num, int(match.group(1)))
    data_num = max_num

data_file = os.path.join(results_dir, f"scp_data{data_num}.json")
if not os.path.exists(data_file):
    print(f"Data file not found: {data_file}")
    sys.exit(1)

print(f"Reading data from {data_file}")

# Load data from JSON
with open(data_file, "r") as f:
    data = json.load(f)

times = data["times"]
labels = data["labels"]
file_sizes_kb = data["file_sizes_kb"]
runs_per_file = data["runs_per_file"]

# Split times into groups by file size
data_by_size = []
for i in range(5):
    start = i * runs_per_file
    end = start + runs_per_file
    data_by_size.append(times[start:end])

# BOXPLOT
plt.figure()
plt.boxplot(data_by_size, vert=True, patch_artist=True)
plt.xlabel("File Size (KB)")
plt.xticks([1, 2, 3, 4, 5], labels)
plt.yscale('log')
plt.ylabel("Elapsed time (seconds)")
plt.title("SCP Transfer Time per File Size")
boxplot_file = os.path.join(results_dir, f"scp_data{data_num}_boxplot.png")
plt.savefig(boxplot_file)
print(f"Saved {boxplot_file}")
plt.close()

# REGRESSION ANALYSIS

# Calculate medians
medians = [np.median(d) for d in data_by_size]
fileSizes = np.array(file_sizes_kb)

# Linear regression
x = fileSizes
y = np.array(medians)
m, b = np.polyfit(x, y, 1)
y_fit = m * x + b

plt.figure()
plt.scatter(x, y)
plt.plot(x, y_fit)
plt.xlabel("File size (KB)")
plt.ylabel("Median SCP time (s)")
plt.title("SCP Transfer Time vs File Size (Linear Regression)")
linear_file = os.path.join(results_dir, f"scp_data{data_num}_linear.png")
plt.savefig(linear_file)
print(f"Saved {linear_file}")
plt.close()

# R squared value for linear fit
ss_tot = np.sum((y - np.mean(y))**2)
ss_res = np.sum((y - y_fit)**2)
linear_r_squared = 1 - (ss_res / ss_tot)
print(f"linear: R² = {linear_r_squared:.4f}")

# Quadratic regression using monotone quadratic fit
a, b_coef, c = monotone_quadratic_fit(fileSizes, medians)
x_fit2 = np.linspace(fileSizes[0], fileSizes[-1], 100)
y_fit2 = a * x_fit2**2 + b_coef * x_fit2 + c

plt.figure()
plt.scatter(fileSizes, medians, color='blue', label='Median times')
plt.plot(x_fit2, y_fit2, color='red', label='Quadratic fit')
plt.xscale('log')
plt.xlabel("File size (KB)")
plt.ylabel("Median SCP time (s)")
plt.title("SCP Transfer Time vs File Size (Quadratic Regression)")
plt.legend()
quadratic_file = os.path.join(results_dir, f"scp_data{data_num}_quadratic.png")
plt.savefig(quadratic_file)
print(f"Saved {quadratic_file}")
plt.close()

# R squared value for quadratic fit
y_pred = a * fileSizes**2 + b_coef * fileSizes + c
ss_res = np.sum((np.array(medians) - y_pred)**2)
ss_tot = np.sum((np.array(medians) - np.mean(medians))**2)
quadratic_r_squared = 1 - (ss_res / ss_tot)
print(f"quadratic: R² for quadratic fit: {quadratic_r_squared:.4f}")

# Save analysis results to JSON
analysis_data = {
    "timestamp": datetime.now().isoformat(),
    "source_data_file": f"scp_data{data_num}.json",
    "medians": medians,
    "file_sizes_kb": file_sizes_kb,
    "linear_regression": {
        "coefficients": {"m": float(m), "b": float(b)},
        "r_squared": float(linear_r_squared)
    },
    "quadratic_regression": {
        "coefficients": {"a": float(a), "b": float(b_coef), "c": float(c)},
        "r_squared": float(quadratic_r_squared)
    }
}

analysis_file = os.path.join(results_dir, f"scp_data_analyzed{data_num}.json")
with open(analysis_file, "w") as f:
    json.dump(analysis_data, f, indent=2)
print(f"Saved {analysis_file}")
