#!/usr/bin/env python3
"""Regenerate the data tables in results/EFT-ARPES-bench-comparison.md.

The three tables (fit parameters, band gaps, verdict) are computed from:
  * config/materials.toml         -- structure + run parameters (a, ecut)
  * scripts/literature.py BENCHMARK -- experimental + GW/HSE06/PBE0 references
  * runs/<M>/p2/eels/eps_q_clean.dat -- refit (eps_inf, mu, aexx)
  * runs/<M>/01-pbe-scf/*.scf.out    -- PBE fundamental gap
  * runs/<M>/p2/ddrshcam/*.out       -- DD-RSH-CAM (beta=1) fundamental + Gamma-direct gap
  * runs/<M>/p2/rsddh/*.out          -- RS-DDH (beta=0.25) gaps, if present (else "—")
  * runs/<M>/p2/finiteG_a*/*.fg.out  -- finite-G (bexx=B_a) gaps for a=0.5,1.0,2.0, if present

So the prose stays hand-written but every NUMBER is derived from the actual runs and
cannot drift. Tables are spliced between <!-- BEGIN:x -->/<!-- END:x --> markers in the
comparison .md (params, gaps, verdict, fgparams, finiteg, mae) and in README.md (full:
the complete PBE + 5-model + literature table).

Usage:
    python3 write_comparison.py            # print all tables
    python3 write_comparison.py --write    # splice them into the comparison .md + README
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_gap import parse_gaps  # noqa: E402
from fit_mu import best_A, parabolic_vertex  # noqa: E402
from gen_inputs import finiteg_bexx, q_ws, qcloud_bexx  # noqa: E402
from literature import BENCHMARK  # noqa: E402
from matlib import (  # noqa: E402
    ROOT, ddrshcam_out, eels_data, finiteg_out, load_materials, pbe_density,
    pbe_out, qcloud_out, rsddh_out,
)

DOC = ROOT / "results" / "EFT-ARPES-bench-comparison.md"
README = ROOT / "README.md"
DISPLAY = {"C": "C (diamond)", "CaF2": "CaF₂"}
APPROX_REF = {"CaF2"}  # GW/HSE/PBE0 entries are bench estimates -> prefix "~"
FG_AS = (0.5, 1.0, 2.0)              # finite-G global constants
ETAS = (0.5, 0.6, 1.0)              # density-scale (qcloud) global constants
IONIC = {"MgO", "CaF2", "LiF"}      # low-ε∞ strong-ionic wide-gap
COVAL = {"Si", "C", "AlAs"}         # covalent / III-V


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
        fg = {}
        for a in FG_AS:
            p = finiteg_out(name, m, a)
            g = parse_gaps(p) if p.exists() else None
            fg[a] = {
                "fund": g["fundamental"] if g else None,
                "direct": g["gamma_direct"] if g else None,
                "bexx": finiteg_bexx(aexx, a),
            }
        nval, vol = pbe_density(name, m)
        qws = q_ws(nval, vol)
        qc = {}
        for e in ETAS:
            p = qcloud_out(name, m, e)
            g = parse_gaps(p) if p.exists() else None
            qc[e] = {
                "fund": g["fundamental"] if g else None,
                "direct": g["gamma_direct"] if g else None,
                "bexx": qcloud_bexx(aexx, mu, qws, e),
                "q_cloud": e * qws,
            }
        rows[name] = {
            "mat": m, "eps_inf": eps_inf, "mu": mu, "aexx": aexx,
            "nval": nval, "vol": vol, "n_v": nval / vol, "q_ws": qws,
            "pbe_fund": pbe["fundamental"], "pbe_direct": pbe["gamma_direct"],
            "ddh_fund": ddh["fundamental"], "ddh_direct": ddh["gamma_direct"],
            "rs_fund": rs["fundamental"] if rs else None,
            "rs_direct": rs["gamma_direct"] if rs else None,
            "fg": fg, "qc": qc,
        }
    return rows


def model_gap(r, model, kind, fund_kind):
    """Gap for a model on one edge. model: 'ddh', 'rs', a finite-G `a` (float), or a
    qcloud key ('qc', eta)."""
    is_fund = kind == fund_kind
    if model == "ddh":
        return r["ddh_fund"] if is_fund else r["ddh_direct"]
    if model == "rs":
        return r["rs_fund"] if is_fund else r["rs_direct"]
    if isinstance(model, tuple) and model[0] == "qc":
        d = r["qc"][model[1]]
        return d["fund"] if is_fund else d["direct"]
    return r["fg"][model]["fund"] if is_fund else r["fg"][model]["direct"]


def mae(rows, model, matset=None):
    errs = []
    for name, r in rows.items():
        if matset and name not in matset:
            continue
        m = r["mat"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        for kind in m["edges"]:
            g = model_gap(r, model, kind, fund_kind)
            exp = BENCHMARK[name]["edges"][kind]["expt"]
            if g is not None and exp is not None:
                errs.append(abs(g - exp))
    return sum(errs) / len(errs) if errs else None


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
            pbe_cell = fnum(r["pbe_fund"] if kind == fund_kind else r["pbe_direct"])
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


def table_fgparams(rows) -> str:
    """Finite-G endpoints B_a = 1−(1−A)·exp(−a²/4) and the wavevector G = a·μ (bohr⁻¹)
    at which ε⁻¹ is sampled to obtain each B_a (the short-range screening length scale)."""
    out = [
        "| material | A = 1/ε∞ | μ (bohr⁻¹) | G=0.5·μ | B (a=0.5) | G=1.0·μ | B (a=1.0) | "
        "G=2.0·μ | B (a=2.0) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in rows.items():
        mu = r["mu"]
        cells = " | ".join(f"{a * mu:.3f} | {r['fg'][a]['bexx']:.3f}" for a in FG_AS)
        out.append(f"| {disp(name)} | {r['aexx']:.3f} | {mu:.3f} | {cells} |")
    return "\n".join(out)


def inv_q(aexx: float, mu: float, bexx: float) -> float | None:
    """Sampling wavevector q* (bohr⁻¹) with ε⁻¹(q*) = bexx under ε⁻¹(q)=1−(1−A)exp(−q²/4μ²).
    Returns None when bexx ∉ (A, 1): bexx ≤ A means it lies on/below the fully-screened floor
    ε⁻¹(0)=A (no real q), bexx ≥ 1 is the q→∞ limit."""
    if not (aexx < bexx < 1.0):
        return None
    return 2.0 * mu * math.sqrt(math.log((1.0 - aexx) / (1.0 - bexx)))


def table_qcparams(rows) -> str:
    """Density inputs + the sampling wavevector q (bohr⁻¹) finally fed to ε⁻¹ to set each
    model's short-range endpoint, for every material and case: RS-DDH (β=¼, 2nd class),
    finite-G (a=0.5/1.0/2.0, 3rd class) and qcloud (η=0.5/0.6/1.0, 4th class)."""
    out = [
        "| material | N_val | Ω (bohr³) | n_v (bohr⁻³) | q_WS (bohr⁻¹) | μ (bohr⁻¹) | "
        "RS-DDH β=¼ | finite-G a=0.5 | finite-G a=1.0 | finite-G a=2.0 | "
        "qcloud η=0.5 | qcloud η=0.6 | qcloud η=1.0 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: |",
    ]
    for name, r in rows.items():
        A, mu = r["aexx"], r["mu"]
        q_rs = inv_q(A, mu, 0.25)
        fg_q = " | ".join(f"{a * mu:.3f}" for a in FG_AS)
        qc_q = " | ".join(f"{r['qc'][e]['q_cloud']:.3f}" for e in ETAS)
        out.append(
            f"| {disp(name)} | {r['nval']:g} | {r['vol']:.2f} | {r['n_v']:.4f} | "
            f"{r['q_ws']:.4f} | {mu:.3f} | {fnum(q_rs, 3)} | {fg_q} | {qc_q} |"
        )
    out.append("")
    out.append(
        "All model columns are the sampling wavevector q (bohr⁻¹) at which ε⁻¹(q) equals that "
        "model's short-range endpoint bexx (under ε⁻¹(q)=1−(1−A)exp(−q²/4μ²)): "
        "**finite-G** q = a·μ, **qcloud** q = η·q_WS (DD-RSH-CAM β=1 ⇒ q→∞, not shown). "
        "**RS-DDH β=¼** is “—” when 0.25 ≤ A = 1/ε∞: the fixed ¼ then lies on/below the "
        "fully-screened floor ε⁻¹(0)=A, so no real wavevector reproduces it (all the ionic "
        "crystals — MgO, LiCl, NaCl, CaF₂, LiF). The corresponding endpoints bexx=B are in "
        "the gap tables (RS-DDH = 0.25; finite-G B_a; qcloud B_η)."
    )
    return "\n".join(out)


def table_qcloud(rows) -> str:
    """Fourth table: density-scale qcloud results (bexx, gap, error per η) next to expt,
    DD-RSH-CAM (β=1) and RS-DDH (β=¼). The sampling length q_cloud is in table_qcparams."""
    hdr = "| material | gap type | expt | **DD-RSH-CAM** β=1 | RS-DDH β=¼ |"
    sep = "| --- | --- | ---: | ---: | ---: |"
    for e in ETAS:
        hdr += f" qcloud η={e} bexx | qcloud η={e} gap | err η={e} |"
        sep += " ---: | ---: | ---: |"
    out = [hdr, sep]
    for name, r in rows.items():
        m = r["mat"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        for kind in m["edges"]:
            exp = BENCHMARK[name]["edges"][kind]["expt"]
            ddh = model_gap(r, "ddh", kind, fund_kind)
            rs = model_gap(r, "rs", kind, fund_kind)
            cells = []
            for e in ETAS:
                g = model_gap(r, ("qc", e), kind, fund_kind)
                err = g - exp if (g is not None and exp is not None) else None
                cells.append(f"{r['qc'][e]['bexx']:.3f} | {fnum(g)} | {err_fmt(err)}")
            out.append(
                f"| {disp(name)} | {edge_label(name, kind)} | {fnum(exp)} | "
                f"**{fnum(ddh)}** | {fnum(rs)} | " + " | ".join(cells) + " |"
            )
    return "\n".join(out)


def table_finiteg(rows) -> str:
    """Second gaps table: finite-G models next to DD-RSH-CAM and RS-DDH."""
    out = [
        "| material | gap type | expt | **DD-RSH-CAM** (β=1) | RS-DDH (β=¼) | "
        "finite-G a=0.5 | finite-G a=1.0 | finite-G a=2.0 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in rows.items():
        m = r["mat"]
        fund_kind = "indirect" if "indirect" in m["edges"] else "direct"
        for kind in m["edges"]:
            exp = BENCHMARK[name]["edges"][kind]["expt"]
            ddh = model_gap(r, "ddh", kind, fund_kind)
            rs = model_gap(r, "rs", kind, fund_kind)
            fgc = " | ".join(fnum(model_gap(r, a, kind, fund_kind)) for a in FG_AS)
            out.append(
                f"| {disp(name)} | {edge_label(name, kind)} | {fnum(exp)} | "
                f"**{fnum(ddh)}** | {fnum(rs)} | {fgc} |"
            )
    return "\n".join(out)


def table_mae(rows) -> str:
    """MAE per model, overall and split by ionic / covalent subsets."""
    models = [
        ("DD-RSH-CAM (β=1)", "ddh"), ("RS-DDH (β=¼)", "rs"),
        ("finite-G a=0.5", 0.5), ("finite-G a=1.0", 1.0), ("finite-G a=2.0", 2.0),
        ("qcloud η=0.5", ("qc", 0.5)), ("qcloud η=0.6", ("qc", 0.6)),
        ("qcloud η=1.0", ("qc", 1.0)),
    ]
    out = [
        "| model | MAE all (eV) | MAE ionic¹ | MAE covalent² |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, mk in models:
        out.append(
            f"| {label} | {fnum(mae(rows, mk), 3)} | "
            f"{fnum(mae(rows, mk, IONIC), 3)} | {fnum(mae(rows, mk, COVAL), 3)} |"
        )
    out.append("")
    out.append(
        "¹ ionic = MgO, CaF₂, LiF (low-ε∞ strong-ionic wide-gap). "
        "² covalent = Si, C, AlAs (covalent / III–V). "
        "MAE is over all listed edges (fundamental + direct Γ→Γ) where a value exists."
    )
    return "\n".join(out)


def table_full(rows) -> str:
    """Complete per-edge results: PBE baseline + all five computed models + literature."""
    out = [
        "| material | gap type | PBE | **DD-RSH-CAM** β=1 | RS-DDH β=¼ | finite-G a=0.5 | "
        "finite-G a=1.0 | finite-G a=2.0 | expt | G₀W₀ | HSE06 | PBE0 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, r in rows.items():
        m = r["mat"]
        edges = m["edges"]
        fund_kind = "indirect" if "indirect" in edges else "direct"
        pre = "~" if name in APPROX_REF else ""
        for kind in edges:
            ref = BENCHMARK[name]["edges"][kind]
            pbe = r["pbe_fund"] if kind == fund_kind else r["pbe_direct"]
            ddh = model_gap(r, "ddh", kind, fund_kind)
            rs = model_gap(r, "rs", kind, fund_kind)
            fg = [model_gap(r, a, kind, fund_kind) for a in FG_AS]
            out.append(
                f"| {disp(name)} | {edge_label(name, kind)} | {fnum(pbe)} | "
                f"**{fnum(ddh)}** | {fnum(rs)} | {fnum(fg[0])} | {fnum(fg[1])} | {fnum(fg[2])} | "
                f"{fnum(ref['expt'])} | {ref_fmt(ref['gw'], pre)} | "
                f"{ref_fmt(ref['hse06'], pre)} | {ref_fmt(ref['pbe0'], pre)} |"
            )
    return "\n".join(out)


def splice(text: str, tag: str, body: str) -> str:
    a, b = f"<!-- BEGIN:{tag} -->", f"<!-- END:{tag} -->"
    if a not in text or b not in text:
        raise SystemExit(f"marker {a}/{b} not found")
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
        "fgparams": table_fgparams(rows),
        "finiteg": table_finiteg(rows),
        "mae": table_mae(rows),
        "qcparams": table_qcparams(rows),
        "qcloud": table_qcloud(rows),
    }
    readme_tables = {
        "full": table_full(rows),
        "mae": table_mae(rows),
        "qcparams": table_qcparams(rows),
        "qcloud": table_qcloud(rows),
    }
    if not args.write:
        for tag, body in {**tables, **readme_tables}.items():
            print(f"\n===== {tag} =====\n{body}")
        return
    text = DOC.read_text()
    for tag, body in tables.items():
        text = splice(text, tag, body)
    DOC.write_text(text)
    print(f"updated {DOC.relative_to(ROOT)}")
    rtext = README.read_text()
    for tag, body in readme_tables.items():
        rtext = splice(rtext, tag, body)
    README.write_text(rtext)
    print(f"updated {README.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
