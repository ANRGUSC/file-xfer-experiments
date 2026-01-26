import numpy as np
from scipy.optimize import lsq_linear

def monotone_quadratic_fit(x, y, xmin=None, xmax=None):
    x = np.asarray(x).ravel()
    y = np.asarray(y).ravel()
    if xmin is None: xmin = x.min()
    if xmax is None: xmax = x.max()

    # Design matrix for ax^2 + bx + c
    A = np.column_stack([x**2, x, np.ones_like(x)])

    # Enforce: 2a*xmin + b >= 0 and 2a*xmax + b >= 0
    # Put into form: G @ [a,b,c] >= h
    G = np.array([[2*xmin, 1.0, 0.0],
                  [2*xmax, 1.0, 0.0]])
    h = np.array([0.0, 0.0])

    # lsq_linear supports only bounds, not general inequalities.
    # Convert to a small quadratic program by using SLSQP instead:
    from scipy.optimize import minimize

    def obj(p):
        r = A @ p - y
        return 0.5 * np.dot(r, r)

    cons = [
        {"type": "ineq", "fun": lambda p, row=G[0]: row @ p - h[0]},
        {"type": "ineq", "fun": lambda p, row=G[1]: row @ p - h[1]},
    ]

    p0 = np.polyfit(x, y, 2)  # good start
    res = minimize(obj, p0, constraints=cons, method="SLSQP")
    if not res.success:
        raise RuntimeError(res.message)
    a, b, c = res.x
    return a, b, c

# usage:
# a,b,c = monotone_quadratic_fit(x,y)
# p = np.poly1d([a,b,c])
