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

    mus = np.linspace(0.05, 5.0, 20000)
    if fix_eps is None:
        rmses = []
        As = []
        for mu in mus:
            A, r = best_A(q, y, mu)
            As.append(A)
            rmses.append(r)
        rmses = np.array(rmses)
        i = int(np.argmin(rmses))
        mu = float(mus[i])
        A = As[i]
        eps_inf = 1.0 / (1.0 - A)
        rmse = float(rmses[i])
    else:
        eps_inf = fix_eps
        A = 1.0 - 1.0 / eps_inf
        rmses = np.array([
            np.sqrt(np.mean(((1.0 - A * np.exp(-(q**2) / (4.0 * mu**2))) - y) ** 2))
            for mu in mus
        ])
        i = int(np.argmin(rmses))
        mu = float(mus[i])
        rmse = float(rmses[i])

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
