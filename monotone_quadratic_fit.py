import numpy as np
from scipy.optimize import minimize

def monotone_quadratic_fit(x, y, xmin=None, xmax=None):
    """
    Fit p(x)=a x^2 + b x + c with constraints:
      - convex (concave up): a >= 0
      - monotone increasing on [xmin, xmax] by forcing the vertex at/before xmin:
            p'(xmin) = 2*a*xmin + b >= 0
        (with a>=0, this implies p'(x) >= 0 for all x >= xmin, hence for [xmin, xmax])
    Returns (a, b, c).
    """
    x = np.asarray(x).ravel()
    y = np.asarray(y).ravel()

    if xmin is None:
        xmin = float(np.min(x))
    if xmax is None:
        xmax = float(np.max(x))  # kept for API compatibility; not needed for constraints

    A = np.column_stack([x**2, x, np.ones_like(x)])

    def obj(p):
        r = A @ p - y
        return 0.5 * (r @ r)

    cons = [
        {"type": "ineq", "fun": lambda p: p[0]},                  # a >= 0
        {"type": "ineq", "fun": lambda p: 2*p[0]*xmin + p[1]},    # p'(xmin) >= 0
    ]

    p0 = np.polyfit(x, y, 2)
    res = minimize(obj, p0, constraints=cons, method="SLSQP")

    if not res.success:
        raise RuntimeError(res.message)

    a, b, c = res.x
    return a, b, c


# usage:
# a,b,c = monotone_quadratic_fit(x,y)
# p = np.poly1d([a,b,c])
