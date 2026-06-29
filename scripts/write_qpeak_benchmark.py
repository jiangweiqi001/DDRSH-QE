#!/usr/bin/env python3
"""Build results/benchmark_qpeak_logcurv.{csv,md} from the qpeak QE runs (if present).

This is the OPTIONAL benchmark table for the density-peak log-curvature finite-q endpoint
(5th model class). It collects, per material/edge:
  * PBE, DD-RSH-CAM β=1, RS-DDH β=¼, finite-G a=0.5, qcloud η=0.5 gaps  (write_comparison.collect)
  * qpeak κ∈{0.25,0.35,0.50}: bexx = ε⁻¹(κ/σ_peak), q_peak, gap, signed error
  * experimental + G₀W₀ / HSE06 / PBE0 references                       (literature.BENCHMARK)
Signed error = E_calc − E_expt; MAE rows use |error|. Materials whose qpeak run is missing
show “—” for that κ. κ is a fixed global constant; the active species is fixed (qpeak.ACTIVE_SPECIES).

Usage:  python3 scripts/write_qpeak_benchmark.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_gap import parse_gaps  # noqa: E402
from literature import BENCHMARK  # noqa: E402
from matlib import ROOT, load_materials, qpeak_out  # noqa: E402
from qpeak import ACTIVE_SPECIES, KAPPAS, qpeak_bexx, species_sigma  # noqa: E402
from write_comparison import (  # noqa: E402
    collect, disp, edge_label, err_fmt, fnum, model_gap, ref_fmt,
)

RESULTS = ROOT / "results"
APPROX_REF = {"CaF2"}


def gather():
    """rows[name] augmented with qpeak[kappa] = {bexx, q_peak, fund, direct}."""
    rows = collect()
    mats = load_materials()
    for name, r in rows.items():
        aexx, mu = r["aexx"], r["mu"]
        sp = ACTIVE_SPECIES[name]
        fit = species_sigma(name, mats[name]["prefix"]).get(sp)
        sigma = fit["sigma"] if fit else None
        qp = {}
        for k in KAPPAS:
            if sigma is None:
                qp[k] = {"bexx": None, "q_peak": None, "fund": None, "direct": None}
                continue
            q_peak, bexx = qpeak_bexx(aexx, mu, sigma, k)
            p = qpeak_out(name, mats[name], k)
            g = parse_gaps(p) if p.exists() else None
            qp[k] = {"bexx": bexx, "q_peak": q_peak,
                     "fund": g["fundamental"] if g else None,
                     "direct": g["gamma_direct"] if g else None}
        r["sigma_peak"], r["active_species"], r["qpeak"] = sigma, sp, qp
    return rows


def qpeak_gap(r, k, kind, fund_kind):
    d = r["qpeak"][k]
    return d["fund"] if kind == fund_kind else d["direct"]


def header():
    cols = ["material", "gap type", "PBE", "DD-RSH-CAM β=1", "RS-DDH β=¼",
            "finite-G a=0.5", "qcloud η=0.5"]
    for k in KAPPAS:
        cols += [f"qpeak κ={k} bexx", f"qpeak κ={k} q_peak",
                 f"qpeak κ={k} gap", f"qpeak κ={k} error"]
    cols += ["expt", "G₀W₀", "HSE06", "PBE0"]
    return cols


def build_rows(rows):
    out = []
    for name, r in rows.items():
        m = r["mat"]
        edges = m["edges"]
        fund_kind = "indirect" if "indirect" in edges else "direct"
        pre = "~" if name in APPROX_REF else ""
        for kind in edges:
            ref = BENCHMARK[name]["edges"][kind]
            exp = ref["expt"]
            pbe = r["pbe_fund"] if kind == fund_kind else r["pbe_direct"]
            row = [disp(name), edge_label(name, kind), fnum(pbe),
                   fnum(model_gap(r, "ddh", kind, fund_kind)),
                   fnum(model_gap(r, "rs", kind, fund_kind)),
                   fnum(model_gap(r, 0.5, kind, fund_kind)),
                   fnum(model_gap(r, ("qc", 0.5), kind, fund_kind))]
            for k in KAPPAS:
                d = r["qpeak"][k]
                g = qpeak_gap(r, k, kind, fund_kind)
                err = g - exp if (g is not None and exp is not None) else None
                row += [fnum(d["bexx"], 3), fnum(d["q_peak"], 3), fnum(g), err_fmt(err)]
            row += [fnum(exp), ref_fmt(ref["gw"], pre), ref_fmt(ref["hse06"], pre),
                    ref_fmt(ref["pbe0"], pre)]
            out.append(row)
    return out


def qpeak_mae(rows, k, matset=None):
    errs = []
    for name, r in rows.items():
        if matset and name not in matset:
            continue
        m = r["mat"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        for kind in m["edges"]:
            g = qpeak_gap(r, k, kind, fund_kind)
            exp = BENCHMARK[name]["edges"][kind]["expt"]
            if g is not None and exp is not None:
                errs.append(abs(g - exp))
    return sum(errs) / len(errs) if errs else None


def main():
    rows = gather()
    hdr = header()
    body = build_rows(rows)
    have = any(r["qpeak"][k]["fund"] is not None for r in rows.values() for k in KAPPAS)

    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "benchmark_qpeak_logcurv.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(body)

    IONIC, COVAL = {"MgO", "CaF2", "LiF"}, {"Si", "C", "AlAs"}
    mae_lines = ["", "MAE (|signed error|) over fundamental + direct Γ→Γ edges:", "",
                 "| model | MAE all (eV) | MAE ionic | MAE covalent |",
                 "| --- | ---: | ---: | ---: |"]
    for k in KAPPAS:
        mae_lines.append(
            f"| qpeak κ={k} | {fnum(qpeak_mae(rows, k), 3)} | "
            f"{fnum(qpeak_mae(rows, k, IONIC), 3)} | {fnum(qpeak_mae(rows, k, COVAL), 3)} |")

    md = ["# Density-peak log-curvature finite-q benchmark (qpeak)", "",
          "B_κ = ε⁻¹(κ/σ_peak) = 1−(1−A)·exp(−q_peak²/4μ²), q_peak = κ/σ_peak, σ_peak from the "
          "log-curvature of the PBE valence-density peak of the fixed active species "
          "(qpeak.ACTIVE_SPECIES). κ is a fixed global constant — not tuned per material, not "
          "fitted to experimental gaps. Signed error = E_calc − E_expt. "
          "Auto-generated by scripts/write_qpeak_benchmark.py.", ""]
    if not have:
        md.append("> No qpeak QE runs found yet — gap/error columns are “—”. "
                  "Populate with `scripts/run_density_qpeak.sh <Material> <kappa>`.")
        md.append("")
    md.append("| " + " | ".join(hdr) + " |")
    md.append("| " + " | ".join("---" for _ in hdr) + " |")
    for row in body:
        md.append("| " + " | ".join(str(c) for c in row) + " |")
    md += mae_lines
    (RESULTS / "benchmark_qpeak_logcurv.md").write_text("\n".join(md) + "\n")
    print("wrote results/benchmark_qpeak_logcurv.csv, results/benchmark_qpeak_logcurv.md",
          "" if have else "(no QE runs yet)")


if __name__ == "__main__":
    main()
