#!/usr/bin/env python3
"""Build results/benchmark_densitymu.{csv,md} for the density-peak range-separation model.

Model (6th class): keep DD-RSH-CAM β=1 (short-range Fock = 1, long-range Fock A = 1/ε∞) but
replace the EELS-fitted screening μ by a density-derived one,

    μ_eff = c / σ_peak     (σ_peak = log-curvature width of the active species' PBE valence
                            density peak; c a single GLOBAL constant, here 0.45/0.55/0.65)

Only `hfscreen` changes vs the β=1 run; aexx = A and bexx = 1 are reused. This table lists the
three c results for every material NEXT TO the previously computed models (PBE, β=1, β=¼,
finite-G a=0.5, qcloud η=0.5, qpeak κ=0.25) and the literature references. Existing results are
read, never modified. Signed error = E_calc − E_expt; MAE rows use |error|.

Usage:  python3 scripts/write_densitymu_benchmark.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_gap import parse_gaps  # noqa: E402
from literature import BENCHMARK  # noqa: E402
from matlib import ROOT, densmu_out, load_materials, qpeak_out  # noqa: E402
from qpeak import ACTIVE_SPECIES, qpeak_bexx, species_sigma  # noqa: E402
from write_comparison import (  # noqa: E402
    collect, disp, edge_label, err_fmt, fnum, model_gap, ref_fmt,
)

RESULTS = ROOT / "results"
APPROX_REF = {"CaF2"}
CS = (0.45, 0.50, 0.55, 0.65)
IONIC, COVAL = {"MgO", "CaF2", "LiF"}, {"Si", "C", "AlAs"}


def gather():
    rows = collect()
    mats = load_materials()
    for name, r in rows.items():
        sp = ACTIVE_SPECIES[name]
        sig = species_sigma(name, mats[name]["prefix"])[sp]["sigma"]
        r["active_species"], r["sigma_peak"] = sp, sig
        # qpeak κ=0.25 (for the comparison column), if its run exists
        qp = qpeak_out(name, mats[name], 0.25)
        g = parse_gaps(qp) if qp.exists() else None
        r["qpeak025"] = {"fund": g["fundamental"] if g else None,
                         "direct": g["gamma_direct"] if g else None}
        dm = {}
        for c in CS:
            mu_eff = c / sig if sig else None
            p = densmu_out(name, mats[name], c)
            g = parse_gaps(p) if p.exists() else None
            dm[c] = {"mu_eff": mu_eff,
                     "fund": g["fundamental"] if g else None,
                     "direct": g["gamma_direct"] if g else None}
        r["dm"] = dm
    return rows


def edge_val(d, kind, fund_kind):
    return d["fund"] if kind == fund_kind else d["direct"]


def header():
    cols = ["material", "gap type", "PBE", "DD-RSH-CAM β=1", "RS-DDH β=¼",
            "finite-G a=0.5", "qcloud η=0.5", "qpeak κ=0.25"]
    for c in CS:
        cols += [f"density-μ c={c} gap", f"density-μ c={c} err"]
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
                   fnum(model_gap(r, ("qc", 0.5), kind, fund_kind)),
                   fnum(edge_val(r["qpeak025"], kind, fund_kind))]
            for c in CS:
                g = edge_val(r["dm"][c], kind, fund_kind)
                err = g - exp if (g is not None and exp is not None) else None
                row += [fnum(g), err_fmt(err)]
            row += [fnum(exp), ref_fmt(ref["gw"], pre), ref_fmt(ref["hse06"], pre),
                    ref_fmt(ref["pbe0"], pre)]
            out.append(row)
    return out


def dm_mae(rows, c, matset=None):
    errs = []
    for name, r in rows.items():
        if matset and name not in matset:
            continue
        m = r["mat"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        for kind in m["edges"]:
            g = edge_val(r["dm"][c], kind, fund_kind)
            exp = BENCHMARK[name]["edges"][kind]["expt"]
            if g is not None and exp is not None:
                errs.append(abs(g - exp))
    return sum(errs) / len(errs) if errs else None


def md_table(rows, header_cells):
    out = ["| " + " | ".join(header_cells) + " |",
           "| " + " | ".join("---" for _ in header_cells) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return out


def splice(text: str, tag: str, body: str) -> str:
    a, b = f"<!-- BEGIN:{tag} -->", f"<!-- END:{tag} -->"
    if a not in text or b not in text:
        raise SystemExit(f"marker {a}/{b} not found in README")
    pre, rest = text.split(a, 1)
    _, post = rest.split(b, 1)
    return f"{pre}{a}\n{body}\n{b}{post}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="splice the tables into README.md (between BEGIN/END:densmu* markers)")
    args = ap.parse_args()
    rows = gather()
    hdr = header()
    body = build_rows(rows)
    have = any(r["dm"][c]["fund"] is not None for r in rows.values() for c in CS)

    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "benchmark_densitymu.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(body)

    # σ_peak / μ_eff params table
    phdr = ["material", "active sp.", "A=1/ε∞", "μ_fit"] + \
           [f"μ_eff (c={c})" for c in CS]
    prows = []
    for name, r in rows.items():
        prows.append([disp(name), r["active_species"], f"{r['aexx']:.3f}",
                      f"{r['mu']:.3f}"] + [f"{c / r['sigma_peak']:.3f}" for c in CS])

    # MAE table
    mhdr = ["model", "MAE all (eV)", "MAE ionic¹", "MAE covalent²"]
    mrows = [[f"density-μ c={c}", fnum(dm_mae(rows, c), 3),
              fnum(dm_mae(rows, c, IONIC), 3), fnum(dm_mae(rows, c, COVAL), 3)]
             for c in CS]

    md = ["# Density-peak range-separation benchmark (density-μ, β=1)", "",
          "Keep DD-RSH-CAM **β=1** (short-range Fock = 1, long-range Fock A = 1/ε∞) but use a "
          "**density-derived screening** μ_eff = c / σ_peak, where σ_peak is the log-curvature "
          "width of the active species' PBE valence-density peak (qpeak.ACTIVE_SPECIES) and c "
          "is a single GLOBAL constant. Larger μ ⇒ smaller gap; the ionic anions (smallest "
          "σ_peak) get the largest μ_eff ⇒ biggest gap reduction. Signed error = E_calc − "
          "E_expt. Existing β=1 / β=¼ / finite-G / qcloud / qpeak results are reused unchanged. "
          "Auto-generated by scripts/write_densitymu_benchmark.py.", ""]
    if not have:
        md += ["> No density-μ QE runs found yet — gap/err columns are “—”. "
               "Run scripts/run_density_mu.sh <Material> <c>.", ""]
    md += md_table(body, hdr)
    md += ["", "Screening inputs (μ_eff = c/σ_peak, bohr⁻¹):", ""]
    md += md_table(prows, phdr)
    md += ["", "MAE (|signed error|) over fundamental + direct Γ→Γ edges:", ""]
    md += md_table(mrows, mhdr)
    md += ["", "¹ ionic = MgO, CaF₂, LiF.  ² covalent = Si, C, AlAs."]
    (RESULTS / "benchmark_densitymu.md").write_text("\n".join(md) + "\n")
    print("wrote results/benchmark_densitymu.csv, results/benchmark_densitymu.md",
          "" if have else "(no QE runs yet)")
    for c in CS:
        print(f"  density-μ c={c}: MAE all={fnum(dm_mae(rows, c), 3)}  "
              f"ionic={fnum(dm_mae(rows, c, IONIC), 3)}  "
              f"covalent={fnum(dm_mae(rows, c, COVAL), 3)}")

    if args.write:
        readme = ROOT / "README.md"
        text = readme.read_text()
        text = splice(text, "densmu", "\n".join(md_table(body, hdr)))
        text = splice(text, "densmu_params", "\n".join(md_table(prows, phdr)))
        text = splice(text, "densmu_mae", "\n".join(md_table(mrows, mhdr)))
        readme.write_text(text)
        print(f"spliced densmu tables into {readme.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
