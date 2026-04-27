#!/usr/bin/env python3
"""
Graph SCP transfer times (median per file size) vs time of day for each origin.
Produces 4 PNG files saved to the results/ directory.
"""

import json
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

ORIGINS = ["london", "amsterdam", "nyc", "toronto"]
DESTINATIONS = ["london", "amsterdam", "nyc", "toronto"]

DEST_COLORS = {
    "london":    "#1f77b4",  # blue
    "amsterdam": "#ff7f0e",  # orange
    "nyc":       "#2ca02c",  # green
    "toronto":   "#d62728",  # red
}

SIZE_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


def load_route_data(origin, destination):
    """Return sorted list of {timestamp, medians} dicts for a route."""
    route_dir = os.path.join(RESULTS_DIR, f"{origin}_to_{destination}")
    if not os.path.isdir(route_dir):
        return []

    files = glob.glob(os.path.join(route_dir, "**", "scp_data*.json"), recursive=True)
    records = []
    for path in files:
        with open(path) as f:
            data = json.load(f)
        ts = datetime.fromisoformat(data["timestamp"])
        n = data.get("runs_per_file", 10)
        labels = data.get("labels", ["1K", "10K", "100K", "1M", "10M"])
        times = data["times"]
        medians = [
            float(np.median(times[i * n:(i + 1) * n]))
            for i in range(len(labels))
        ]
        records.append({"timestamp": ts, "medians": medians, "labels": labels})

    records.sort(key=lambda r: r["timestamp"])
    return records


def plot_origin(origin):
    destinations = [d for d in DESTINATIONS if d != origin]

    # Determine file size labels from first available data
    all_labels = ["1K", "10K", "100K", "1M", "10M"]
    for dest in destinations:
        records = load_route_data(origin, dest)
        if records:
            all_labels = records[0]["labels"]
            break

    n_dests = len(destinations)
    fig, axes = plt.subplots(1, n_dests, figsize=(5 * n_dests, 4), sharey=False)
    if n_dests == 1:
        axes = [axes]

    fig.suptitle(f"SCP Transfer Times — Origin: {origin.capitalize()}", fontsize=13, fontweight="bold")

    any_data = False
    for ax, dest in zip(axes, destinations):
        records = load_route_data(origin, dest)
        if not records:
            ax.set_title(f"→ {dest.capitalize()}", fontsize=10)
            continue
        any_data = True
        timestamps = [r["timestamp"] for r in records]
        for i, label in enumerate(all_labels):
            medians = [r["medians"][i] for r in records]
            ax.plot(
                timestamps, medians,
                marker="o", linewidth=1.5, markersize=6,
                label=label, color=SIZE_COLORS[i]
            )
        ax.set_title(f"→ {dest.capitalize()}", fontsize=10)
        ax.set_xlabel("Time of Day")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.tick_params(axis="x", rotation=45)
        ax.legend(title="File Size", fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Median SCP Time (s)")

    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, f"scp_times_{origin}.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    status = "saved" if any_data else "no data yet"
    print(f"{origin.capitalize()}: {out_path} ({status})")
    plt.close()


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    for origin in ORIGINS:
        plot_origin(origin)


if __name__ == "__main__":
    main()
