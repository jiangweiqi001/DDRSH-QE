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
from pathlib import Path

from matlib import ROOT, load_materials

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


def _dest(name: str, mat: dict, which: str) -> Path:
    p = mat["prefix"]
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
                    choices=["pbe", "eels", "ddrshcam", "rsddh", "all"], default="all")
    ap.add_argument("--aexx", default="AEXX_PLACEHOLDER")
    ap.add_argument("--hfscreen", default="HFSCREEN_PLACEHOLDER")
    ap.add_argument("--bexx", default=None,
                    help="short-range Fock fraction (default 1.0 for ddrshcam, 0.25 for rsddh)")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing files")
    args = ap.parse_args()

    mats = load_materials()
    if args.material not in mats:
        ap.error(f"unknown material {args.material!r}; have {', '.join(mats)}")
    mat = mats[args.material]

    builders = {
        "pbe": lambda: pbe_input(mat),
        "eels": lambda: eels_input(mat),
        "ddrshcam": lambda: ddrshcam_input(mat, args.aexx, args.hfscreen, args.bexx or "1.0"),
        "rsddh": lambda: rsddh_input(mat, args.aexx, args.hfscreen, args.bexx or "0.25"),
    }
    which = ["pbe", "eels", "ddrshcam"] if args.which == "all" else [args.which]
    for w in which:
        content = builders[w]()
        if args.stdout:
            print(f"===== {w} =====\n{content}")
            continue
        dest = _dest(args.material, mat, w)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
