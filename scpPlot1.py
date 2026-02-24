import json
import os
import re
import glob
import sys
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize

def convex_quadratic_fit(x, y):
    """
    Fit a convex quadratic curve y = a*x^2 + b*x + c

    Constraints:
    - a >= 0 (concave up / convex: parabola opens upward)

    This allows the optimizer to find the best convex curve without
    forcing monotonicity. Monotonicity is checked visually/interpretively
    after fitting.

    Note: Internally scales x to [0,1] range for numerical stability,
    then converts coefficients back to original scale.
    """
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    # Scale x to [0, 1] for numerical stability
    x_min, x_max = x.min(), x.max()
    x_range = x_max - x_min
    if x_range == 0:
        x_range = 1.0  # Avoid division by zero
    x_scaled = (x - x_min) / x_range

    # Objective: minimize sum of squared residuals (on scaled x)
    def objective(params):
        a_s, b_s, c_s = params
        y_pred = a_s * x_scaled**2 + b_s * x_scaled + c_s
        return np.sum((y - y_pred)**2)

    # Initial guess using standard polyfit on scaled data
    initial_params = np.polyfit(x_scaled, y, 2)

    # Ensure initial a is non-negative
    if initial_params[0] < 0:
        initial_params[0] = 0.0

    # Bounds: a >= 0 (concave up), b and c unbounded
    bounds = [(0, None), (None, None), (None, None)]

    # Optimize
    result = minimize(
        objective,
        initial_params,
        method='SLSQP',
        bounds=bounds,
        options={'maxiter': 1000}
    )

    if not result.success:
        print(f"Warning: Optimization did not converge: {result.message}")
        print("Using best available solution anyway.")

    a_s, b_s, c_s = result.x

    # Convert coefficients back to original scale
    # If y = a_s * ((x - x_min)/x_range)^2 + b_s * ((x - x_min)/x_range) + c_s
    # Expanding: y = (a_s/x_range^2)*x^2 + (-2*a_s*x_min/x_range^2 + b_s/x_range)*x
    #              + (a_s*x_min^2/x_range^2 - b_s*x_min/x_range + c_s)
    a = a_s / (x_range ** 2)
    b = -2 * a_s * x_min / (x_range ** 2) + b_s / x_range
    c = a_s * (x_min ** 2) / (x_range ** 2) - b_s * x_min / x_range + c_s

    # Check monotonicity visually (for reporting, not enforcing)
    x_check = np.linspace(x.min(), x.max(), 100)
    y_check = a * x_check**2 + b * x_check + c
    derivatives = 2 * a * x_check + b

    if np.all(derivatives >= 0):
        monotonicity_status = "monotonically increasing"
    elif np.all(derivatives <= 0):
        monotonicity_status = "monotonically decreasing"
    else:
        # Find turning point
        if a > 0:
            turning_x = -b / (2 * a)
            monotonicity_status = f"non-monotonic (minimum at x ≈ {turning_x:.2f})"
        else:
            monotonicity_status = "approximately linear"

    print(f"Fitted convex quadratic: a={a:.6e}, b={b:.6e}, c={c:.6e}")
    print(f"Curve shape: {monotonicity_status}")

    return a, b, c

results_dir = "results"

# Determine which data file to use
if len(sys.argv) > 1:
    # Use specified timestamp (e.g., "1423" for 14:23)
    time_stamp = sys.argv[1]
    data_file = os.path.join(results_dir, f"scp_data_{time_stamp}.json")
else:
    # Find the most recently modified JSON file
    existing_files = glob.glob(os.path.join(results_dir, "scp_data_*.json"))
    if not existing_files:
        print("No data files found in results folder.")
        sys.exit(1)
    # Sort by modification time, get the latest
    data_file = max(existing_files, key=os.path.getmtime)
    # Extract timestamp from filename for plot naming
    match = re.search(r'scp_data_(\d{4})\.json$', data_file)
    time_stamp = match.group(1) if match else "unknown"
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
boxplot_file = os.path.join(results_dir, f"scp_data{time_stamp}_boxplot.png")
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

# R squared value for linear fit
ss_tot = np.sum((y - np.mean(y))**2)
ss_res = np.sum((y - y_fit)**2)
linear_r_squared = 1 - (ss_res / ss_tot)

plt.figure()
plt.scatter(x, y)
plt.plot(x, y_fit)
plt.xlabel("File size (KB)")
plt.ylabel("Median SCP time (s)")
plt.title(f"SCP Transfer Time vs File Size (Linear Regression)\nR² = {linear_r_squared:.4f}")
linear_file = os.path.join(results_dir, f"scp_data{time_stamp}_linear.png")
plt.savefig(linear_file)
print(f"Saved {linear_file}")
plt.close()

print(f"linear: R² = {linear_r_squared:.4f}")

# Quadratic regression using convex quadratic fit (no monotonicity constraint)
print("\nFitting convex quadratic (convexity only, no monotonicity constraint):")
a, b_coef, c = convex_quadratic_fit(fileSizes, medians)

x_fit2 = np.linspace(fileSizes[0], fileSizes[-1], 100)
y_fit2 = a * x_fit2**2 + b_coef * x_fit2 + c

# R squared value for quadratic fit
y_pred = a * fileSizes**2 + b_coef * fileSizes + c
ss_res = np.sum((np.array(medians) - y_pred)**2)
ss_tot = np.sum((np.array(medians) - np.mean(medians))**2)
quadratic_r_squared = 1 - (ss_res / ss_tot)

plt.figure()
plt.scatter(fileSizes, medians, color='blue', label='Median times')
plt.plot(x_fit2, y_fit2, color='red', label='Convex quadratic fit')
plt.xscale('log')
plt.xlabel("File size (KB)")
plt.ylabel("Median SCP time (s)")
plt.title(f"SCP Transfer Time vs File Size (Convex Quadratic)\nR² = {quadratic_r_squared:.4f}")
plt.legend()
quadratic_file = os.path.join(results_dir, f"scp_data{time_stamp}_quadratic.png")
plt.savefig(quadratic_file)
print(f"Saved {quadratic_file}")
plt.close()

print(f"quadratic: R² for quadratic fit: {quadratic_r_squared:.4f}")

# Visual monotonicity check across the data range
derivatives_at_data = 2 * a * fileSizes + b_coef
print(f"\nMonotonicity check (derivative at data points):")
print(f"  Min derivative: {derivatives_at_data.min():.6e}")
print(f"  Max derivative: {derivatives_at_data.max():.6e}")
if derivatives_at_data.min() >= -1e-10:  # Allow small numerical errors
    print("  [OK] Curve is monotonically increasing over data range")
else:
    print("  [WARN] Curve is not strictly monotonic over data range")

# Add analysis results to the original data file
data["analysis"] = {
    "analysis_timestamp": datetime.now().isoformat(),
    "medians": medians,
    "linear_regression": {
        "coefficients": {"m": float(m), "b": float(b)},
        "r_squared": float(linear_r_squared),
        "model": "y = m*x + b"
    },
    "quadratic_regression": {
        "coefficients": {"a": float(a), "b": float(b_coef), "c": float(c)},
        "r_squared": float(quadratic_r_squared),
        "model": "y = a*x² + b*x + c (convex, a >= 0)"
    },
    "best_fit": {
        "model": max(
            [("linear", linear_r_squared),
             ("quadratic", quadratic_r_squared)],
            key=lambda x: x[1]
        )[0],
        "r_squared": max(linear_r_squared, quadratic_r_squared)
    }
}

# Save back to the same file
with open(data_file, "w") as f:
    json.dump(data, f, indent=2)
print(f"\nUpdated {data_file} with analysis results")

