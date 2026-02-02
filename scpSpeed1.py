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

# Find next sequential number
existing_files = glob.glob(os.path.join(results_dir, "scp_data*.json"))
max_num = 0
for f in existing_files:
    match = re.search(r'scp_data(\d+)\.json$', f)
    if match:
        max_num = max(max_num, int(match.group(1)))
next_num = max_num + 1

# Get sender IP address
try:
    sender_ip = socket.gethostbyname(socket.gethostname())
except:
    sender_ip = "unknown"

# Extract receiver IP from HOST (format: user@ip)
receiver_ip = HOST.split("@")[1] if "@" in HOST else HOST

# Save data to JSON
data = {
    "timestamp": datetime.now().isoformat(),
    "sender_ip": sender_ip,
    "receiver_ip": receiver_ip,
    "host": HOST,
    "runs_per_file": RUNS,
    "sleep_between": SLEEP_BETWEEN,
    "labels": LABELS,
    "file_sizes_kb": [1, 10, 100, 1000, 10000],
    "times": times
}

output_file = os.path.join(results_dir, f"scp_data{next_num}.json")
with open(output_file, "w") as f:
    json.dump(data, f, indent=2)

print(f"Data saved to {output_file}")

