#!/usr/bin/env python3
"""Regenerate the data tables in results/EFT-ARPES-bench-comparison.md.

The three tables (fit parameters, band gaps, verdict) are computed from:
  * config/materials.toml         -- structure + run parameters (a, ecut)
  * scripts/literature.py BENCHMARK -- experimental + GW/HSE06/PBE0 references
  * runs/<M>/p2/eels/eps_q_clean.dat -- refit (eps_inf, mu, aexx)
  * runs/<M>/01-pbe-scf/*.scf.out    -- PBE fundamental gap
  * runs/<M>/p2/ddrshcam/*.out       -- DD-RSH-CAM (beta=1) fundamental + Gamma-direct gap
  * runs/<M>/p2/rsddh/*.out          -- RS-DDH (beta=0.25) gaps, if present (else "—")

So the prose stays hand-written but every NUMBER is derived from the actual runs and
cannot drift. Tables are spliced between <!-- BEGIN:x -->/<!-- END:x --> markers.

Usage:
    python3 write_comparison.py            # print the three tables
    python3 write_comparison.py --write    # splice them into the comparison .md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_gap import parse_gaps  # noqa: E402
from fit_mu import best_A, parabolic_vertex  # noqa: E402
from literature import BENCHMARK  # noqa: E402
from matlib import (  # noqa: E402
    ROOT, ddrshcam_out, eels_data, load_materials, pbe_out, rsddh_out,
)

DOC = ROOT / "results" / "EFT-ARPES-bench-comparison.md"
DISPLAY = {"C": "C (diamond)", "CaF2": "CaF₂"}
APPROX_REF = {"CaF2"}  # GW/HSE/PBE0 entries are bench estimates -> prefix "~"


def disp(name: str) -> str:
    return DISPLAY.get(name, name)


def edge_label(name: str, kind: str) -> str:
    special = {("AlAs", "indirect"): "indirect Γ→X", ("CaF2", "indirect"): "indirect W→Γ"}
    return special.get((name, kind), "indirect" if kind == "indirect" else "direct Γ→Γ")


def fit_eps(path: Path) -> tuple[float, float, float]:
    data = np.loadtxt(path)
    q, y = data[:, 1], data[:, 3]
    mus = np.linspace(0.05, 5.0, 20000)
    rmses = np.array([best_A(q, y, mu)[1] for mu in mus])
    i = int(np.argmin(rmses))
    mu = parabolic_vertex(mus, rmses, i)
    A, _ = best_A(q, y, mu)
    eps_inf = 1.0 / (1.0 - A)
    return eps_inf, mu, 1.0 / eps_inf


def fnum(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def err_fmt(err):
    return "—" if err is None else f"{err:+.2f}".replace("-", "−")


def ref_fmt(x, pre=""):
    """Reference value with minimal but >=1 decimal place (9.0, 5.5, 6.56)."""
    if x is None:
        return "—"
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return pre + s


def collect() -> dict[str, dict]:
    mats = load_materials()
    rows = {}
    for name, m in mats.items():
        eps_inf, mu, aexx = fit_eps(eels_data(name, m))
        pbe = parse_gaps(pbe_out(name, m))
        ddh = parse_gaps(ddrshcam_out(name, m))
        rs_path = rsddh_out(name, m)
        rs = parse_gaps(rs_path) if rs_path.exists() else None
        rows[name] = {
            "mat": m, "eps_inf": eps_inf, "mu": mu, "aexx": aexx,
            "pbe_fund": pbe["fundamental"],
            "ddh_fund": ddh["fundamental"], "ddh_direct": ddh["gamma_direct"],
            "rs_fund": rs["fundamental"] if rs else None,
            "rs_direct": rs["gamma_direct"] if rs else None,
        }
    return rows


def table_params(rows) -> str:
    out = [
        "| material | structure | a (bohr) | ecut (Ry) | ε∞ (fit) | ε∞ (expt) | μ (bohr⁻¹) | aexx = 1/ε∞ |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in rows.items():
        m = r["mat"]
        out.append(
            f"| {disp(name)} | {m['structure']} | {m['celldm1']:g} | {m['ecutwfc']:g} | "
            f"{r['eps_inf']:.2f} | ~{BENCHMARK[name]['eps_inf_expt']:g} | "
            f"{r['mu']:.3f} | {r['aexx']:.3f} |"
        )
    return "\n".join(out)


def table_gaps(rows) -> str:
    out = [
        "| material | gap type | PBE | **DD-RSH-CAM** (β=1) | RS-DDH (β=¼) | expt | "
        "err DDH | err RS | G₀W₀ | HSE06 | PBE0 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in rows.items():
        m = r["mat"]
        edges = m["edges"]
        fund_kind = "indirect" if "indirect" in edges else "direct"
        pre = "~" if name in APPROX_REF else ""
        for kind in edges:
            ref = BENCHMARK[name]["edges"][kind]
            ddh = r["ddh_fund"] if kind == fund_kind else r["ddh_direct"]
            rs = r["rs_fund"] if kind == fund_kind else r["rs_direct"]
            pbe_cell = fnum(r["pbe_fund"]) if kind == fund_kind else "—"
            exp = ref["expt"]
            err_d = ddh - exp if (ddh is not None and exp is not None) else None
            err_r = rs - exp if (rs is not None and exp is not None) else None
            out.append(
                f"| {disp(name)} | {edge_label(name, kind)} | {pbe_cell} | "
                f"**{fnum(ddh)}** | {fnum(rs)} | {fnum(exp)} | "
                f"{err_fmt(err_d)} | {err_fmt(err_r)} | "
                f"{ref_fmt(ref['gw'], pre)} | {ref_fmt(ref['hse06'], pre)} | "
                f"{ref_fmt(ref['pbe0'], pre)} |"
            )
    return "\n".join(out)


def table_verdict(rows) -> str:
    out = [
        "| material | gap type | tol (eV) | DD-RSH-CAM err | pass? | RS-DDH err | pass? |",
        "| --- | --- | ---: | ---: | :--: | ---: | :--: |",
    ]
    npass = ntot = npass_rs = ntot_rs = 0
    for name, r in rows.items():
        m = r["mat"]
        tol = BENCHMARK[name]["tol_eV"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        for kind in m["edges"]:
            ref = BENCHMARK[name]["edges"][kind]
            ddh = r["ddh_fund"] if kind == fund_kind else r["ddh_direct"]
            rs = r["rs_fund"] if kind == fund_kind else r["rs_direct"]
            err = ddh - ref["expt"]
            ok = abs(err) <= tol
            ntot += 1
            npass += ok
            if rs is not None:
                err_r = rs - ref["expt"]
                ok_r = abs(err_r) <= tol
                ntot_rs += 1
                npass_rs += ok_r
                rs_err_cell, rs_pass_cell = err_fmt(err_r), "✅" if ok_r else "❌ (over)"
            else:
                rs_err_cell, rs_pass_cell = "—", "—"
            out.append(
                f"| {disp(name)} | {edge_label(name, kind)} | {tol:.2f} | "
                f"{err_fmt(err)} | {'✅' if ok else '❌ (over)'} | "
                f"{rs_err_cell} | {rs_pass_cell} |"
            )
    out.append("")
    out.append(
        f"**DD-RSH-CAM: {npass} of {ntot} edges within tolerance; "
        f"RS-DDH (β=¼): {npass_rs} of {ntot_rs}.**"
    )
    return "\n".join(out)


def splice(text: str, tag: str, body: str) -> str:
    a, b = f"<!-- BEGIN:{tag} -->", f"<!-- END:{tag} -->"
    if a not in text or b not in text:
        raise SystemExit(f"marker {a}/{b} not found in {DOC}")
    pre, rest = text.split(a, 1)
    _, post = rest.split(b, 1)
    return f"{pre}{a}\n{body}\n{b}{post}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="splice tables into the .md")
    args = ap.parse_args()
    rows = collect()
    tables = {
        "params": table_params(rows),
        "gaps": table_gaps(rows),
        "verdict": table_verdict(rows),
    }
    if not args.write:
        for tag, body in tables.items():
            print(f"\n===== {tag} =====\n{body}")
        return
    text = DOC.read_text()
    for tag, body in tables.items():
        text = splice(text, tag, body)
    DOC.write_text(text)
    print(f"updated {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
