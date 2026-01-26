import subprocess
import time
from time import sleep
import os
import sys
import matplotlib.pyplot as plt
import numpy as np 
import statistics
import math


HOST = "root@167.99.128.200"
CONTROL = "/tmp/ssh_ctrl_%h_%p_%r"
SRC_FILES = ["test_1K.bin", "test_10K.bin", "test_100K.bin", "test_1M.bin", "test_10M.bin"]
LABELS = ["1K", "10K", "100K", "1M", "10M"]
RUNS = 10
SLEEP_BETWEEN = 2  # seconds

# --- Checking for files ---
for src in SRC_FILES:
    if not os.path.exists(src):
        print(f"Source file not found: {src}")
        sys.exit(1)

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
with open("output.txt", "w") as f:
    for i in range(5):
        #f.write(f"{LABELS[i]}\n")
        #f.flush()
    
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
        f.write(f"{t:.6f}\n")
        f.flush()
        print(f"Time: {t:.6f}s")

print("All SCP runs complete.")

# GRAPHING
data1k = times[0:10]
data10k = times[10:20]
data100k = times[20:30]
data1m = times[30:40]
data10m = times[40:50]
data = [data1k, data10k, data100k, data1m, data10m]

#BOXPLOT
plt.figure()
plt.boxplot(data, vert=True, patch_artist=True)
plt.xlabel("File Size (KB)")
plt.xticks([1, 2, 3, 4, 5], LABELS)
plt.yscale('log')
plt.ylabel("Elapsed time (seconds)")
plt.title("SCP Transfer Time per File Size")
plt.show()

# REGRESSION ANALYSIS

# Linear
medians = []
for i in range(5):
    medians.append(np.median(data[i]))
fileSizes = np.array([1, 10, 100, 1000, 10000])
x = fileSizes
y = medians
m, b = np.polyfit(x, y, 1)
y_fit = m * x + b
plt.figure()
plt.scatter(x, y)
plt.plot(x, y_fit)
plt.show()

# R squared value
ss_tot = np.sum((y - np.mean(y))**2)
ss_res = np.sum((y - y_fit)**2)
r_squared = 1 - (ss_res / ss_tot)
print(f"linear: R² = {r_squared:.4f}")

# Quadratic 
coeffs = np.polyfit(fileSizes, medians, 2)
a, b, c = coeffs
#print(f"Quadratic coefficients: a={a}, b={b}, c={c}")
x_fit2 = np.linspace(fileSizes[0], fileSizes[-1], 100)
y_fit2 = a * x_fit2**2 + b * x_fit2 + c
plt.figure()
plt.scatter(fileSizes, medians, color='blue', label='Median times')
plt.plot(x_fit2, y_fit2, color='red', label='Quadratic fit')
plt.xscale('log')  # optional, because file sizes vary a lot
plt.xlabel("File size (KB)")
plt.ylabel("Median SCP time (s)")
plt.title("SCP Transfer Time vs File Size (Quadratic Regression)")
plt.legend()
plt.show()

# R squared value
y_pred = a * fileSizes**2 + b * fileSizes + c
ss_res = np.sum((medians - y_pred)**2)
ss_tot = np.sum((medians - np.mean(medians))**2)
r_squared = 1 - (ss_res / ss_tot)
print(f"quadratic: R² for quadratic fit: {r_squared:.4f}")


