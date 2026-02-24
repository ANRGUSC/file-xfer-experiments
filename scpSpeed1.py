import subprocess
import time
from time import sleep
import os
import sys
import json
import re
import glob
import socket
from datetime import datetime
import numpy as np
from scipy.optimize import minimize


HOST = "root@167.99.128.200"
CONTROL = "/tmp/ssh_ctrl_%h_%p_%r"
SRC_FILES = ["test_1K.bin", "test_10K.bin", "test_100K.bin", "test_1M.bin", "test_10M.bin"]
LABELS = ["1K", "10K", "100K", "1M", "10M"]
FILE_SIZES_KB = [1, 10, 100, 1000, 10000]
RUNS = 10
SLEEP_BETWEEN = 2  # seconds


def convex_quadratic_fit(x, y):
    """
    Fit a convex quadratic curve y = a*x^2 + b*x + c
    Constraints: a >= 0 (concave up / convex)
    """
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    x_min, x_max = x.min(), x.max()
    x_range = x_max - x_min
    if x_range == 0:
        x_range = 1.0
    x_scaled = (x - x_min) / x_range

    def objective(params):
        a_s, b_s, c_s = params
        y_pred = a_s * x_scaled**2 + b_s * x_scaled + c_s
        return np.sum((y - y_pred)**2)

    initial_params = np.polyfit(x_scaled, y, 2)
    if initial_params[0] < 0:
        initial_params[0] = 0.0

    bounds = [(0, None), (None, None), (None, None)]
    result = minimize(objective, initial_params, method='SLSQP', bounds=bounds, options={'maxiter': 1000})

    a_s, b_s, c_s = result.x
    a = a_s / (x_range ** 2)
    b = -2 * a_s * x_min / (x_range ** 2) + b_s / x_range
    c = a_s * (x_min ** 2) / (x_range ** 2) - b_s * x_min / x_range + c_s

    return a, b, c

# --- Checking for files ---
for src in SRC_FILES:
    if not os.path.exists(src):
        print(f"Source file not found: {src}")
        sys.exit(1)

# Extract receiver IP from HOST (format: user@ip)
receiver_ip = HOST.split("@")[1] if "@" in HOST else HOST

# --- Ping to measure latency (before SCP transfers) ---
print("Measuring latency with ping...")
PING_COUNT = 10
ping_result = subprocess.run(
    ["ping", "-c", str(PING_COUNT), receiver_ip],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

latency_values = []
if ping_result.returncode == 0:
    # Parse ping output to extract RTT values (time=XX.XX ms)
    for line in ping_result.stdout.split('\n'):
        match = re.search(r'time=(\d+\.?\d*)\s*ms', line)
        if match:
            latency_values.append(float(match.group(1)))

if latency_values:
    median_latency_ms = float(np.median(latency_values))
    print(f"Collected {len(latency_values)} ping values")
    print(f"Median latency: {median_latency_ms:.2f} ms\n")
else:
    median_latency_ms = None
    print("Warning: Could not collect ping latency values\n")

# --- iperf3 to measure bandwidth (before SCP transfers) ---
print("Measuring bandwidth with iperf3...")
iperf_result = subprocess.run(
    ["iperf3", "-c", receiver_ip],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

sender_bitrate = None
sender_bitrate_unit = None
if iperf_result.returncode == 0:
    # Parse iperf3 output to extract sender bitrate (first of two summary lines at bottom)
    lines = iperf_result.stdout.strip().split('\n')
    for line in lines:
        if 'sender' in line.lower():
            # Match bitrate value and unit (e.g., "943 Mbits/sec" or "1.23 Gbits/sec")
            match = re.search(r'(\d+\.?\d*)\s*([GMK]?bits/sec)', line)
            if match:
                sender_bitrate = float(match.group(1))
                sender_bitrate_unit = match.group(2)
                break
    if sender_bitrate:
        print(f"Sender bitrate: {sender_bitrate} {sender_bitrate_unit}\n")
    else:
        print("Warning: Could not parse iperf3 sender bitrate\n")
else:
    print(f"Warning: iperf3 failed - {iperf_result.stderr}\n")

# --- Open SSH connection ---
print("Opening persistent SSH connection...")
start1 = time.monotonic()
subprocess.run(
    [
        "ssh",
        "-MNf",
        "-o", "ControlMaster=yes",
        "-o", f"ControlPath={CONTROL}",
        "-o", "ControlPersist=120s",
        HOST
    ],
    check=True
)
elapsed1 = time.monotonic() - start1
print("SSH control connection established\n")

# Running SCP
times = []
for i in range(5):
    for j in range(RUNS):
        dst = f"{HOST}:/tmp/{SRC_FILES[i]}"
        print(f"Starting SCP run {j} for {LABELS[i]}...")
        start2 = time.monotonic()
        result = subprocess.run([
            "scp",
            "-o", f"ControlPath={CONTROL}",
            "-o", "Compression=no",
            f"{SRC_FILES[i]}",
            dst
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
        )
        elapsed2 = time.monotonic() - start2
        time1to2 = elapsed1+elapsed2
        times.append(time1to2)

        if result.returncode != 0:
            print("SCP failed!")
            print(result.stderr)
            break
        time.sleep(SLEEP_BETWEEN)

print("\nClosing SSH control connection...")
start3 = time.monotonic()
# --- Close persistent SSH connection ---
subprocess.run(
    [
        "ssh",
        "-O", "exit",
        "-o", f"ControlPath={CONTROL}",
        HOST
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
elapsed3 = time.monotonic() - start3
times = [t + elapsed3 for t in times]

for t in times:
    print(f"Time: {t:.6f}s")

print("All SCP runs complete.")

# Create results folder if it doesn't exist
results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

# Generate timestamp for filename (military time: HHMM)
time_stamp = datetime.now().strftime("%H%M")

# Get sender IP address
try:
    sender_ip = socket.gethostbyname(socket.gethostname())
except:
    sender_ip = "unknown"

# Split times into groups by file size for analysis
data_by_size = []
for i in range(5):
    start = i * RUNS
    end = start + RUNS
    data_by_size.append(times[start:end])

# Calculate medians for regression
medians = [float(np.median(d)) for d in data_by_size]
file_sizes = np.array(FILE_SIZES_KB)

# Linear regression: y = m*x + b
m, b_lin = np.polyfit(file_sizes, medians, 1)
y_fit_linear = m * file_sizes + b_lin
ss_tot = np.sum((np.array(medians) - np.mean(medians))**2)
ss_res_linear = np.sum((np.array(medians) - y_fit_linear)**2)
linear_r_squared = float(1 - (ss_res_linear / ss_tot))

# Quadratic regression: y = a*x^2 + b*x + c (convex)
a_quad, b_quad, c_quad = convex_quadratic_fit(file_sizes, medians)
y_pred_quad = a_quad * file_sizes**2 + b_quad * file_sizes + c_quad
ss_res_quad = np.sum((np.array(medians) - y_pred_quad)**2)
quadratic_r_squared = float(1 - (ss_res_quad / ss_tot))

print(f"Linear R²: {linear_r_squared:.4f}")
print(f"Quadratic R²: {quadratic_r_squared:.4f}")

# Determine best fit
best_fit_name = max(
    [("linear", linear_r_squared), ("quadratic", quadratic_r_squared)],
    key=lambda x: x[1]
)[0]

timestamp_iso = datetime.now().isoformat()

# File 1: scp_data_r_squared.json - R-squared values and timestamp
r_squared_data = {
    "timestamp": timestamp_iso,
    "r_squared_values": {
        "linear": linear_r_squared,
        "quadratic": quadratic_r_squared
    },
    "best_fit": best_fit_name
}

r_squared_file = os.path.join(results_dir, f"scp_data_r_squared_{time_stamp}.json")
with open(r_squared_file, "w") as f:
    json.dump(r_squared_data, f, indent=2)
print(f"R-squared data saved to {r_squared_file}")

# File 2: scp_data_analyzed.json - Full analysis data
analyzed_data = {
    "timestamp": timestamp_iso,
    "sender": sender_ip,
    "receiver": receiver_ip,
    "host": HOST,
    "runs_per_file": RUNS,
    "sleep_between": SLEEP_BETWEEN,
    "labels": LABELS,
    "median_latency_ms": median_latency_ms,
    "latency_values": latency_values,
    "sender_bitrate": sender_bitrate,
    "sender_bitrate_unit": sender_bitrate_unit,
    "times": times,
    "medians": medians,
    "functions": {
        "linear": {
            "coefficients": {"m": float(m), "b": float(b_lin)},
            "r_squared": linear_r_squared,
            "formula": "y = m*x + b"
        },
        "quadratic": {
            "coefficients": {"a": float(a_quad), "b": float(b_quad), "c": float(c_quad)},
            "r_squared": quadratic_r_squared,
            "formula": "y = a*x^2 + b*x + c"
        }
    },
    "best_fit": best_fit_name
}

analyzed_file = os.path.join(results_dir, f"scp_data_analyzed_{time_stamp}.json")
with open(analyzed_file, "w") as f:
    json.dump(analyzed_data, f, indent=2)
print(f"Analyzed data saved to {analyzed_file}")

