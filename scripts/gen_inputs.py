#!/usr/bin/env python3
"""Generate the three QE inputs for a material from config/materials.toml.

  runs/<M>/01-pbe-scf/<prefix>.scf.in       PBE SCF (self-built pw.x -> charge-density.dat)
  runs/<M>/p2/eels/<prefix>.scf.in          tight SCF feeding turbo_eels.x
  runs/<M>/p2/ddrshcam/<prefix>.ddrshcam.in DD-RSH-CAM hybrid SCF

For the hybrid input, pass --aexx / --hfscreen (from the turboEELS fit). Without them
the file is written with AEXX_PLACEHOLDER / HFSCREEN_PLACEHOLDER so run_material.sh can
substitute the fitted values in place.

Usage:
    python3 gen_inputs.py <Material> [--which pbe|eels|ddrshcam|all]
                          [--aexx A] [--hfscreen MU] [--stdout]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from matlib import ROOT, eta_tag, kappa_tag, load_materials, pbe_density

BOHR = 0.529177210903


def _species_block(mat: dict) -> str:
    return "\n".join(
        f"{s['symbol']:<3s} {s['mass']:>8.3f}  {s['pseudo']}" for s in mat["species"]
    )


def _positions_block(mat: dict) -> str:
    return "\n".join(
        f"{p['symbol']:<3s} {p['xyz'][0]:>5} {p['xyz'][1]:>5} {p['xyz'][2]:>5}"
        for p in mat["positions"]
    )


def _kline(mesh: list[int]) -> str:
    return f"{mesh[0]} {mesh[1]} {mesh[2]} 0 0 0"


def _header(mat: dict, comment: str) -> str:
    a_ang = mat["celldm1"] * BOHR
    return (
        f"  ibrav       = {mat['ibrav']}\n"
        f"  celldm(1)   = {mat['celldm1']}   ! a = {a_ang:.3f} A (experimental){comment}\n"
        f"  nat         = {mat['nat']}\n"
        f"  ntyp        = {mat['ntyp']}\n"
        f"  ecutwfc     = {mat['ecutwfc']}\n"
        f"  ecutrho     = {mat['ecutrho']}\n"
        f"  occupations = 'fixed'\n"
        f"  nbnd        = {mat['nbnd']}"
    )


def pbe_input(mat: dict) -> str:
    return f"""&control
  calculation = 'scf'
  prefix      = '{mat['prefix']}'
  outdir      = './out'
  pseudo_dir  = '../../../pseudos'
  verbosity   = 'high'
  tprnfor     = .true.
  tstress     = .true.
/
&system
{_header(mat, "")}
/
&electrons
  conv_thr    = 1.0d-10
  mixing_beta = 0.7
/
ATOMIC_SPECIES
{_species_block(mat)}
ATOMIC_POSITIONS crystal
{_positions_block(mat)}
K_POINTS automatic
{_kline(mat['kmesh'])}
"""


def eels_input(mat: dict) -> str:
    return f"""&control
  calculation = 'scf'
  prefix      = '{mat['prefix']}'
  outdir      = './out'
  pseudo_dir  = '../../../../pseudos'
  verbosity   = 'high'
/
&system
{_header(mat, "")}
/
&electrons
  conv_thr    = 1.0d-12
  mixing_beta = 0.7
/
ATOMIC_SPECIES
{_species_block(mat)}
ATOMIC_POSITIONS crystal
{_positions_block(mat)}
K_POINTS automatic
{_kline(mat['kmesh'])}
"""


def hybrid_input(mat: dict, aexx: str, hfscreen: str, bexx: str,
                 prefix_tag: str, outdir: str) -> str:
    """Range-separated DD hybrid SCF (lmodelhf): long-range Fock A = aexx = 1/eps_inf,
    short-range Fock B = bexx, screening mu = hfscreen.

      B = 1.0   -> Chen 2018 DD-RSH-CAM   (full short-range Fock)
      B = 0.25  -> Skone 2016 RS-DDH      (PBE0-like short-range fraction)
    """
    nqx = mat["nqx"]
    return f"""&control
  calculation = 'scf'
  prefix      = '{mat['prefix']}{prefix_tag}'
  outdir      = '{outdir}'
  pseudo_dir  = '../../../../pseudos'
  verbosity   = 'high'
  tstress     = .false.
  tprnfor     = .false.
/
&system
{_header(mat, "")}
  input_dft        = 'hse'
  lmodelhf         = .true.
  aexx             = {aexx}
  bexx             = {bexx}
  hfscreen         = {hfscreen}
  exxdiv_treatment = 'gygi-baldereschi'
  nqx1 = {nqx[0]}, nqx2 = {nqx[1]}, nqx3 = {nqx[2]}
/
&electrons
  conv_thr    = 1.0d-8
  mixing_beta = 0.7
/
ATOMIC_SPECIES
{_species_block(mat)}
ATOMIC_POSITIONS crystal
{_positions_block(mat)}
K_POINTS automatic
{_kline(mat['kmesh_hybrid'])}
"""


def ddrshcam_input(mat: dict, aexx: str = "AEXX_PLACEHOLDER",
                   hfscreen: str = "HFSCREEN_PLACEHOLDER", bexx: str = "1.0") -> str:
    """Chen 2018 DD-RSH-CAM: full short-range Fock (bexx = 1.0)."""
    return hybrid_input(mat, aexx, hfscreen, bexx, "6", "./out6")


def rsddh_input(mat: dict, aexx: str = "AEXX_PLACEHOLDER",
                hfscreen: str = "HFSCREEN_PLACEHOLDER", bexx: str = "0.25") -> str:
    """Skone 2016 RS-DDH: PBE0-like short-range Fock (bexx = 0.25)."""
    return hybrid_input(mat, aexx, hfscreen, bexx, "rs", "./out_rs")


def finiteg_bexx(aexx: float, a: float) -> float:
    """Finite-G short-range endpoint B_a = ε⁻¹(G = a·μ) under the single-μ model
    ε⁻¹(G) = 1 − (1−A)·exp(−G²/4μ²), with A = aexx = 1/ε∞. `a` is a global constant
    (same for all materials); B_a is material-dependent through A."""
    return 1.0 - (1.0 - aexx) * math.exp(-(a ** 2) / 4.0)


def finiteg_input(mat: dict, aexx: str, hfscreen: str, a: float) -> str:
    """Finite-G model: single μ, long-range Fock A = 1/ε∞, short-range endpoint
    bexx = B_a = ε⁻¹(a·μ). Same kernel as DD-RSH-CAM/RS-DDH, only bexx changes."""
    bexx = finiteg_bexx(float(aexx), a)
    return hybrid_input(mat, f"{float(aexx):.4f}", hfscreen, f"{bexx:.4f}", "fg", "./out_fg")


def q_ws(nval: float, vol_bohr3: float) -> float:
    """Average-valence-density wavevector q_WS = (4π n_v/3)^(1/3), n_v = N_val/Ω (bohr⁻¹)."""
    n_v = nval / vol_bohr3
    return (4.0 * math.pi * n_v / 3.0) ** (1.0 / 3.0)


def qcloud_bexx(aexx: float, mu: float, qws: float, eta: float) -> float:
    """Density-scale endpoint B_η = ε⁻¹(q_cloud), q_cloud = η·q_WS, under the single-μ
    model ε⁻¹(q) = 1 − (1−A)·exp(−q²/4μ²)."""
    q_cloud = eta * qws
    return 1.0 - (1.0 - aexx) * math.exp(-(q_cloud ** 2) / (4.0 * mu ** 2))


def qcloud_input(mat: dict, name: str, aexx: str, hfscreen: str, eta: float) -> str:
    """Density-scale finite-q model: short-range endpoint bexx = ε⁻¹(η·q_WS), with q_WS
    from the cell's average valence density (N_val, Ω parsed from the PBE SCF output)."""
    nval, vol = pbe_density(name, mat)
    qws = q_ws(nval, vol)
    bexx = qcloud_bexx(float(aexx), float(hfscreen), qws, eta)
    return hybrid_input(mat, f"{float(aexx):.4f}", hfscreen, f"{bexx:.4f}", "qc", "./out_qc")


def qpeak_input(mat: dict, name: str, aexx: str, hfscreen: str, kappa: float) -> str:
    """Density-peak log-curvature finite-q model: short-range endpoint bexx = ε⁻¹(κ/σ_peak),
    with σ_peak from the log-curvature of the PBE valence-density peak of the active species."""
    from qpeak import ACTIVE_SPECIES, qpeak_bexx, species_sigma
    sp = ACTIVE_SPECIES[name]
    fit = species_sigma(name, mat["prefix"]).get(sp)
    if fit is None or fit["sigma"] is None:
        raise SystemExit(f"qpeak σ_peak fit failed for {name}/{sp}: "
                         f"{fit['status'] if fit else 'species missing'}")
    _q, bexx = qpeak_bexx(float(aexx), float(hfscreen), fit["sigma"], kappa)
    return hybrid_input(mat, f"{float(aexx):.4f}", hfscreen, f"{bexx:.4f}", "qp", "./out_qp")


def _dest(name: str, mat: dict, which: str, a: float | None = None,
          eta: float | None = None, kappa: float | None = None) -> Path:
    p = mat["prefix"]
    if which == "finiteg":
        return ROOT / "runs" / name / "p2" / f"finiteG_a{a:.1f}" / f"{p}.fg.in"
    if which == "qcloud":
        return ROOT / "runs" / name / "p2" / f"qcloud_eta{eta_tag(eta)}" / f"{p}.qc.in"
    if which == "qpeak":
        return ROOT / "runs" / name / "p2" / f"qpeak_kappa{kappa_tag(kappa)}" / f"{p}.qp.in"
    return {
        "pbe": ROOT / "runs" / name / "01-pbe-scf" / f"{p}.scf.in",
        "eels": ROOT / "runs" / name / "p2" / "eels" / f"{p}.scf.in",
        "ddrshcam": ROOT / "runs" / name / "p2" / "ddrshcam" / f"{p}.ddrshcam.in",
        "rsddh": ROOT / "runs" / name / "p2" / "rsddh" / f"{p}.rsddh.in",
    }[which]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("material")
    ap.add_argument("--which",
                    choices=["pbe", "eels", "ddrshcam", "rsddh", "finiteg", "qcloud",
                             "qpeak", "all"],
                    default="all")
    ap.add_argument("--aexx", default="AEXX_PLACEHOLDER")
    ap.add_argument("--hfscreen", default="HFSCREEN_PLACEHOLDER")
    ap.add_argument("--bexx", default=None,
                    help="short-range Fock fraction (default 1.0 for ddrshcam, 0.25 for rsddh)")
    ap.add_argument("--a", type=float, default=None,
                    help="finite-G constant a (B_a = 1-(1-A)exp(-a^2/4)); required for finiteg")
    ap.add_argument("--eta", type=float, default=None,
                    help="density-scale constant η (q_cloud = η·q_WS); required for qcloud")
    ap.add_argument("--kappa", type=float, default=None,
                    help="density-peak constant κ (q_peak = κ/σ_peak); required for qpeak")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing files")
    args = ap.parse_args()

    mats = load_materials()
    if args.material not in mats:
        ap.error(f"unknown material {args.material!r}; have {', '.join(mats)}")
    mat = mats[args.material]

    if args.which == "finiteg" and args.a is None:
        ap.error("--which finiteg requires --a")
    if args.which == "qcloud" and args.eta is None:
        ap.error("--which qcloud requires --eta")
    if args.which == "qpeak" and args.kappa is None:
        ap.error("--which qpeak requires --kappa")

    builders = {
        "pbe": lambda: pbe_input(mat),
        "eels": lambda: eels_input(mat),
        "ddrshcam": lambda: ddrshcam_input(mat, args.aexx, args.hfscreen, args.bexx or "1.0"),
        "rsddh": lambda: rsddh_input(mat, args.aexx, args.hfscreen, args.bexx or "0.25"),
        "finiteg": lambda: finiteg_input(mat, args.aexx, args.hfscreen, args.a),
        "qcloud": lambda: qcloud_input(mat, args.material, args.aexx, args.hfscreen, args.eta),
        "qpeak": lambda: qpeak_input(mat, args.material, args.aexx, args.hfscreen, args.kappa),
    }
    which = ["pbe", "eels", "ddrshcam"] if args.which == "all" else [args.which]
    for w in which:
        content = builders[w]()
        if args.stdout:
            print(f"===== {w} =====\n{content}")
            continue
        dest = _dest(args.material, mat, w, args.a, args.eta, args.kappa)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
