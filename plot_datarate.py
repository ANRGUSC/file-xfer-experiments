import json
import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

data_dir = "results/CronTab215"
if len(sys.argv) > 1:
    data_dir = sys.argv[1]

# Collect data from all analyzed JSON files
data_points = []
for filepath in sorted(glob.glob(os.path.join(data_dir, "scp_data_analyzed_*.json"))):
    with open(filepath) as f:
        d = json.load(f)

    # Extract time label from filename
    match = re.search(r'_(\d{4})\.json$', filepath)
    if not match:
        continue
    time_str = match.group(1)
    time_label = time_str[:2] + ":" + time_str[2:]
    time_minutes = int(time_str[:2]) * 60 + int(time_str[2:])

    linear = d.get("functions", {}).get("linear", {})
    coeffs = linear.get("coefficients", {})
    m = coeffs.get("m", 0.0)

    sender_bitrate = d.get("sender_bitrate", 0.0)
    median_latency = d.get("median_latency_ms", 0.0)

    if m and m != 0.0:
        data_points.append({
            "time_label": time_label,
            "time_minutes": time_minutes,
            "m": m,
            "sender_bitrate": sender_bitrate or 0.0,
            "median_latency_ms": median_latency or 0.0,
        })

# Sort by time
data_points.sort(key=lambda dp: dp["time_minutes"])

print(f"Loaded {len(data_points)} data points from {data_dir}")

# m is in seconds/KB (x was FILE_SIZES_KB = [1, 10, 100, 1000, 10000])
# To convert to seconds/bit: m_bits = m / (1024 * 8) = m / 8192
# Data rate = 1/m_bits = 8192/m bits/sec
# In Mbps: 8192 / (m * 1e6)
data_rates_mbps = [8192.0 / (dp["m"] * 1e6) for dp in data_points]
time_labels = [dp["time_label"] for dp in data_points]
iperf_rates = [dp["sender_bitrate"] for dp in data_points]

# Print data for inspection
print(f"\n{'Time':<8} {'m (s/KB)':<16} {'1/m (Mbps)':<14} {'iPerf (Mbps)':<14}")
print("-" * 52)
for dp, rate in zip(data_points, data_rates_mbps):
    print(f"{dp['time_label']:<8} {dp['m']:<16.6e} {rate:<14.4f} {dp['sender_bitrate']:<14.1f}")

# ========== Graph 1: File Data Rate (1/m) vs Time ==========
fig, ax = plt.subplots(figsize=(10, 6))
x_pos = range(len(data_points))
ax.plot(x_pos, data_rates_mbps, 'bo-', markersize=6, label='Data Rate (1/m)')
ax.set_xticks(list(x_pos))
ax.set_xticklabels(time_labels, rotation=45, ha='right')
ax.set_xlabel('Time of Day (Military Time)')
ax.set_ylabel('Data Rate (Mbps)')
ax.set_title('SCP File Transfer Data Rate (1/m) vs Time of Day')
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig('file-data-rate.png', dpi=150)
print("\nSaved: file-data-rate.png")
plt.close()

# ========== Graph 2: SCP Data Rate (1/m) vs iPerf3 Rate ==========
# Filter out points where iperf is missing/zero
valid = [(rate, iperf) for rate, iperf in zip(data_rates_mbps, iperf_rates) if iperf > 0]
if valid:
    scp_r = np.array([v[0] for v in valid])
    iperf_r = np.array([v[1] for v in valid])

    # Linear regression
    slope, intercept = np.polyfit(iperf_r, scp_r, 1)
    y_fit = slope * iperf_r + intercept
    ss_tot = np.sum((scp_r - np.mean(scp_r))**2)
    ss_res = np.sum((scp_r - y_fit)**2)
    r_squared = 1 - (ss_res / ss_tot)

    print(f"\nLinear fit: SCP_rate = {slope:.6f} * iPerf_rate + {intercept:.6f}")
    print(f"R² = {r_squared:.4f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(iperf_r, scp_r, color='blue', s=50, zorder=5, label='Trials')

    # Regression line
    x_line = np.linspace(iperf_r.min(), iperf_r.max(), 100)
    y_line = slope * x_line + intercept
    ax.plot(x_line, y_line, 'r-', linewidth=2, label=f'Linear Fit (R²={r_squared:.4f})')

    ax.set_xlabel('iPerf3 Data Rate (Mbps)')
    ax.set_ylabel('SCP Data Rate from 1/m (Mbps)')
    ax.set_title(f'SCP Data Rate (1/m) vs iPerf3 Measured Rate')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig('datarate-vs-iperf.png', dpi=150)
    print("Saved: datarate-vs-iperf.png")
    plt.close()
else:
    print("\nNo valid data points with both SCP rate and iPerf rate.")

# ========== Graph 3: SCP Data Rate (1/m) vs Median Latency ==========
valid_lat = [(rate, dp["median_latency_ms"]) for rate, dp in zip(data_rates_mbps, data_points) if dp["median_latency_ms"] > 0]
if valid_lat:
    scp_r = np.array([v[0] for v in valid_lat])
    latency = np.array([v[1] for v in valid_lat])

    # Linear regression
    slope, intercept = np.polyfit(latency, scp_r, 1)
    y_fit = slope * latency + intercept
    ss_tot = np.sum((scp_r - np.mean(scp_r))**2)
    ss_res = np.sum((scp_r - y_fit)**2)
    r_squared = 1 - (ss_res / ss_tot)

    print(f"\nData Rate vs Latency:")
    print(f"  Linear fit: SCP_rate = {slope:.6f} * latency + {intercept:.6f}")
    print(f"  R² = {r_squared:.4f}")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(latency, scp_r, color='blue', s=50, zorder=5, label='Trials')

    x_line = np.linspace(latency.min(), latency.max(), 100)
    y_line = slope * x_line + intercept
    ax.plot(x_line, y_line, 'r-', linewidth=2, label=f'Linear Fit (R²={r_squared:.4f})')

    ax.set_xlabel('Median Ping Latency (ms)')
    ax.set_ylabel('SCP Data Rate from 1/m (Mbps)')
    ax.set_title('SCP Data Rate (1/m) vs Median Latency')
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig('datarate-vs-latency.png', dpi=150)
    print("Saved: datarate-vs-latency.png")
    plt.close()
else:
    print("\nNo valid data points with both SCP rate and latency.")
