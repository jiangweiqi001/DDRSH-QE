#!/usr/bin/env python3
"""Fit the DD-RSH-CAM model inverse dielectric function

    eps^-1(q) = 1 - A * exp(-q^2 / (4 mu^2)),   A = 1 - 1/eps_inf

to turboEELS data (q in bohr^-1, eps^-1 at omega=0).

For a fixed mu the model is LINEAR in A, so we scan mu on a fine grid and solve
the (1-parameter) linear least squares for A at each mu, then pick the global best
and parabolically refine. numpy only -- no scipy needed.

Usage:
    python3 fit_mu.py eps_q.dat [--fix-eps-inf VALUE]

Input columns (lines starting with # ignored):
    q[2pi/a]   q[bohr^-1]   eps_M(q,0)   eps^-1(q,0)
"""
import sys
import numpy as np


def best_A(q, y, mu):
    """Least-squares A for eps^-1 = 1 - A*exp(-q^2/4mu^2) (or fixed-A residual)."""
    g = np.exp(-(q**2) / (4.0 * mu**2))
    # minimize sum( (1 - A g - y)^2 ) -> A = sum(g(1-y))/sum(g^2)
    A = np.sum(g * (1.0 - y)) / np.sum(g * g)
    resid = (1.0 - A * g) - y
    return A, float(np.sqrt(np.mean(resid**2)))


def rmse_fixed_A(q, y, mu, A):
    """RMSE of eps^-1 = 1 - A*exp(-q^2/4mu^2) for a fixed A."""
    resid = (1.0 - A * np.exp(-(q**2) / (4.0 * mu**2))) - y
    return float(np.sqrt(np.mean(resid**2)))


def parabolic_vertex(mus, rmses, i):
    """Sub-grid minimum via parabolic interpolation of the three points around i.

    Returns the refined mu. Falls back to mus[i] when i is on the grid edge or the
    fitted parabola is not convex (no interior minimum).
    """
    if i <= 0 or i >= len(mus) - 1:
        return float(mus[i])
    y0, y1, y2 = rmses[i - 1], rmses[i], rmses[i + 1]
    denom = y0 - 2.0 * y1 + y2
    if denom <= 0.0:
        return float(mus[i])
    dx = float(mus[1] - mus[0])
    return float(mus[i]) + 0.5 * dx * (y0 - y2) / denom


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    fix_eps = None
    if "--fix-eps-inf" in sys.argv:
        fix_eps = float(sys.argv[sys.argv.index("--fix-eps-inf") + 1])

    data = np.loadtxt(path)
    q = data[:, 1]
    y = data[:, 3]

    mu_lo, mu_hi = 0.05, 5.0
    mus = np.linspace(mu_lo, mu_hi, 20000)
    if fix_eps is None:
        results = [best_A(q, y, mu) for mu in mus]
        As = np.array([r[0] for r in results])
        rmses = np.array([r[1] for r in results])
        i = int(np.argmin(rmses))
        # Parabolic sub-grid refinement (the grid only quantizes mu to ~2.5e-4).
        mu = parabolic_vertex(mus, rmses, i)
        A, rmse = best_A(q, y, mu)
        eps_inf = 1.0 / (1.0 - A)
    else:
        eps_inf = fix_eps
        A = 1.0 - 1.0 / eps_inf
        rmses = np.array([rmse_fixed_A(q, y, mu, A) for mu in mus])
        i = int(np.argmin(rmses))
        mu = parabolic_vertex(mus, rmses, i)
        rmse = rmse_fixed_A(q, y, mu, A)

    if i == 0 or i == len(mus) - 1:
        print(
            f"WARNING: best mu hit the scan boundary [{mu_lo}, {mu_hi}] bohr^-1 "
            "(index {0}); widen the range — the result is not a true minimum.".format(i),
            file=sys.stderr,
        )

    pred = 1.0 - A * np.exp(-(q**2) / (4.0 * mu**2))
    print(f"eps_inf        = {eps_inf:.4f}")
    print(f"mu             = {mu:.4f} bohr^-1")
    print(f"AEXX=1/eps_inf = {1.0/eps_inf:.4f}")
    print(f"RMSE           = {rmse:.5f}")
    print("\n  q[bohr^-1]   eps^-1(data)   eps^-1(fit)   resid")
    for qi, di, pi in zip(q, y, pred):
        print(f"  {qi:9.4f}   {di:11.5f}   {pi:11.5f}   {pi-di:+.5f}")


if __name__ == "__main__":
    main()
