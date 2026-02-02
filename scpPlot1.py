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
    - a >= 0 (convexity: curve opens upward)
    
    This allows the optimizer to find the best convex curve without
    forcing monotonicity. Monotonicity is checked visually/interpretively
    after fitting.
    """
    x = np.array(x)
    y = np.array(y)
    
    # Objective: minimize sum of squared residuals
    def objective(params):
        a, b, c = params
        y_pred = a * x**2 + b * x + c
        return np.sum((y - y_pred)**2)
    
    # Initial guess using standard polyfit
    initial_params = np.polyfit(x, y, 2)
    
    # Ensure initial a is non-negative
    if initial_params[0] < 0:
        initial_params[0] = 0.0001
    
    # Constraints: only convexity (a >= 0)
    # No monotonicity constraint - let the optimizer decide
    constraints = []
    
    # Bounds: a >= 0 (convexity), b and c unbounded
    bounds = [(0, None), (None, None), (None, None)]
    
    # Optimize
    result = minimize(
        objective,
        initial_params,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )
    
    if not result.success:
        print(f"Warning: Optimization did not converge: {result.message}")
        print("Using best available solution anyway.")
    
    a, b, c = result.x
    
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
linear_file = os.path.join(results_dir, f"scp_data{data_num}_linear.png")
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
quadratic_file = os.path.join(results_dir, f"scp_data{data_num}_quadratic.png")
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
    print("  ✓ Curve is monotonically increasing over data range")
else:
    print("  ⚠ Curve is not strictly monotonic over data range")

# Logarithmic regression: y = a_log * log(x) + b_log
print("\nFitting logarithmic model: y = a*log(x) + b")
log_x = np.log(fileSizes)
a_log, b_log = np.polyfit(log_x, medians, 1)
y_fit_log = a_log * log_x + b_log

# Create smooth curve for plotting
x_fit_log = np.linspace(fileSizes[0], fileSizes[-1], 100)
y_fit_log_smooth = a_log * np.log(x_fit_log) + b_log

# R squared value for logarithmic fit
ss_res_log = np.sum((medians - y_fit_log)**2)
ss_tot_log = np.sum((medians - np.mean(medians))**2)
log_r_squared = 1 - (ss_res_log / ss_tot_log)

plt.figure()
plt.scatter(fileSizes, medians, color='blue', label='Median times')
plt.plot(x_fit_log, y_fit_log_smooth, color='green', label='Logarithmic fit')
plt.xscale('log')
plt.xlabel("File size (KB)")
plt.ylabel("Median SCP time (s)")
plt.title(f"SCP Transfer Time vs File Size (Logarithmic Regression)\nR² = {log_r_squared:.4f}")
plt.legend()
log_file = os.path.join(results_dir, f"scp_data{data_num}_logarithmic.png")
plt.savefig(log_file)
print(f"Saved {log_file}")
plt.close()

print(f"logarithmic: y = {a_log:.6e}*log(x) + {b_log:.6e}")
print(f"logarithmic: R² = {log_r_squared:.4f}")

# Exponential regression: y = a_exp * exp(b_exp * x)
print("\nFitting exponential model: y = a*exp(b*x)")
# Use log transform: log(y) = log(a) + b*x
# This assumes all y values are positive
if np.all(np.array(medians) > 0):
    log_y = np.log(medians)
    b_exp, log_a_exp = np.polyfit(fileSizes, log_y, 1)
    a_exp = np.exp(log_a_exp)
    y_fit_exp = a_exp * np.exp(b_exp * fileSizes)
    
    # Create smooth curve for plotting
    x_fit_exp = np.linspace(fileSizes[0], fileSizes[-1], 100)
    y_fit_exp_smooth = a_exp * np.exp(b_exp * x_fit_exp)
    
    # R squared value for exponential fit
    ss_res_exp = np.sum((medians - y_fit_exp)**2)
    ss_tot_exp = np.sum((medians - np.mean(medians))**2)
    exp_r_squared = 1 - (ss_res_exp / ss_tot_exp)
    
    plt.figure()
    plt.scatter(fileSizes, medians, color='blue', label='Median times')
    plt.plot(x_fit_exp, y_fit_exp_smooth, color='orange', label='Exponential fit')
    plt.xscale('log')
    plt.xlabel("File size (KB)")
    plt.ylabel("Median SCP time (s)")
    plt.title(f"SCP Transfer Time vs File Size (Exponential Regression)\nR² = {exp_r_squared:.4f}")
    plt.legend()
    exp_file = os.path.join(results_dir, f"scp_data{data_num}_exponential.png")
    plt.savefig(exp_file)
    print(f"Saved {exp_file}")
    plt.close()
    
    print(f"exponential: y = {a_exp:.6e}*exp({b_exp:.6e}*x)")
    print(f"exponential: R² = {exp_r_squared:.4f}")
    
    exp_fit_success = True
else:
    print("Warning: Cannot fit exponential model - some median values are not positive")
    a_exp = None
    b_exp = None
    exp_r_squared = None
    exp_fit_success = False

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
        "r_squared": float(quadratic_r_squared),
        "convexity": "enforced (a >= 0)",
        "monotonicity": "not enforced (checked visually)"
    },
    "logarithmic_regression": {
        "coefficients": {"a": float(a_log), "b": float(b_log)},
        "r_squared": float(log_r_squared),
        "model": "y = a*log(x) + b"
    },
    "exponential_regression": {
        "coefficients": {"a": float(a_exp) if exp_fit_success else None, "b": float(b_exp) if exp_fit_success else None},
        "r_squared": float(exp_r_squared) if exp_fit_success else None,
        "model": "y = a*exp(b*x)",
        "fit_success": exp_fit_success
    }
}

analysis_file = os.path.join(results_dir, f"scp_data_analyzed{data_num}.json")
with open(analysis_file, "w") as f:
    json.dump(analysis_data, f, indent=2)
print(f"\nSaved {analysis_file}")

# Save R-squared summary to a separate JSON file for easy comparison
r_squared_summary = {
    "timestamp": datetime.now().isoformat(),
    "source_data_file": f"scp_data{data_num}.json",
    "r_squared_values": {
        "linear_regression": {
            "r_squared": float(linear_r_squared),
            "model": "y = m*x + b"
        },
        "quadratic_regression": {
            "r_squared": float(quadratic_r_squared),
            "model": "y = a*x² + b*x + c (convex, a >= 0)"
        },
        "logarithmic_regression": {
            "r_squared": float(log_r_squared),
            "model": "y = a*log(x) + b"
        },
        "exponential_regression": {
            "r_squared": float(exp_r_squared) if exp_fit_success else None,
            "model": "y = a*exp(b*x)",
            "fit_success": exp_fit_success
        }
    },
    "best_fit": {
        "model": max(
            [("linear", linear_r_squared), 
             ("quadratic", quadratic_r_squared), 
             ("logarithmic", log_r_squared),
             ("exponential", exp_r_squared if exp_fit_success else -1)],
            key=lambda x: x[1]
        )[0],
        "r_squared": max(linear_r_squared, quadratic_r_squared, log_r_squared, 
                        exp_r_squared if exp_fit_success else -1)
    }
}

r_squared_file = os.path.join(results_dir, f"scp_data_r_squared{data_num}.json")
with open(r_squared_file, "w") as f:
    json.dump(r_squared_summary, f, indent=2)
print(f"Saved R² summary: {r_squared_file}")

