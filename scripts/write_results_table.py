#!/usr/bin/env python3
"""Write a compact QE DDRSH-approximation summary table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from extract_qe_summary import parse_pw_gap
from literature import LITERATURE


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "pending"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def gap_from(out_path: Path | None) -> float | None:
    if out_path is None:
        return None
    parsed = parse_pw_gap(out_path)
    if parsed:
        return parsed.get("gap_eV")
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--material", default="MgO")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--ddh-out", type=Path, help="pw.x output of the DDH (PBE0) run")
    parser.add_argument("--hse-out", type=Path, help="pw.x output of the DD-HSE run")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8")) if args.summary.exists() else {}
    lit = LITERATURE[args.material]

    eps = summary.get("epsilon") or {}
    components = eps.get("components") or []
    pbe_gap = (summary.get("pbe_gap") or {}).get("gap_eV")
    ddh_gap = gap_from(args.ddh_out)
    hse_gap = gap_from(args.hse_out)

    rows = [
        ("Material", args.material),
        ("Engine", "Quantum ESPRESSO (pw.x + epsilon.x)"),
        ("Structure source", lit["structure_source"]),
        ("PBE band gap", f"{fmt(pbe_gap, 3)} eV"),
        ("epsilon components (eps.x)", ", ".join(f"{c:.4f}" for c in components) if components else "pending"),
        ("epsilon_inf", fmt(summary.get("epsilon_inf"), 6)),
        ("exx_fraction = 1 / epsilon_inf", fmt(summary.get("exx_fraction"), 6)),
        ("mu (DD-HSE screening_parameter)", f"{lit['mu_bohr_inv']:.3f} bohr^-1 (used directly in QE)"),
        ("DDH / PBE0 gap (primary QE target)", f"{fmt(ddh_gap, 3)} eV"),
        ("DD-HSE gap (approximate RS)", f"{fmt(hse_gap, 3)} eV"),
        (
            "Paper values",
            f"PBE {lit['pbe_gap_eV']:.2f}; HSE06 {lit['hse06_gap_eV']:.2f}; "
            f"DDH {lit['ddh_gap_eV']:.2f}; RS-DDH {lit['rs_ddh_gap_eV']:.2f}; "
            f"DD0-RSH-CAM {lit['dd0_rsh_cam_gap_eV']:.2f}",
        ),
        ("Experimental gap", f"{lit['experimental_gap_eV']:.2f} eV"),
    ]

    lines = [
        f"# {args.material} QE DDRSH-Approximation Summary",
        "",
        f"Reference: {lit['reference']}",
        "",
        "Primary QE-reproducible target is the global DDH, i.e. PBE0 with "
        "exx_fraction = 1 / epsilon_inf. The DD-HSE run is only an approximation of "
        "the range-separated family: QE HSE removes Fock exchange in the long range, "
        "while DD-RSH-CAM keeps screened Fock there. A strict DD-RSH-CAM reproduction "
        "needs a patched QE with separate short- and long-range exact-exchange fractions.",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in rows)

    if ddh_gap is not None:
        d_paper = ddh_gap - lit["ddh_gap_eV"]
        d_exp = ddh_gap - lit["experimental_gap_eV"]
        lines.extend(
            [
                "",
                "## Comparison (DDH, primary target)",
                "",
                f"- DDH gap (this run): {ddh_gap:.3f} eV",
                f"- vs paper DDH ({lit['ddh_gap_eV']:.2f} eV): {d_paper:+.3f} eV",
                f"- vs experiment ({lit['experimental_gap_eV']:.2f} eV): {d_exp:+.3f} eV",
                "",
                "Likely contributions to the deviation:",
                "",
                f"- Lattice constant: this run uses the experimental a = 4.186 A; "
                f"PBE here is {fmt(pbe_gap, 2)} eV vs paper 4.79 eV (paper used a = 4.148 A).",
                f"- epsilon_inf source: PBE DFPT gives {fmt(summary.get('epsilon_inf'), 3)} "
                f"(exx_fraction {fmt(summary.get('exx_fraction'), 3)}) vs paper 2.81; "
                "a self-consistent hybrid epsilon_inf would change the EXX fraction.",
                "- k-mesh (6x6x6) and Fock q-grid (nqx 3x3x3) are not converged; hybrid gaps "
                "rise toward the converged value as these grids are densified.",
                "- Pseudopotential and cutoffs (SG15 ONCV, ecutwfc 80 Ry) differ from the paper's setup.",
            ]
        )

    lines.extend(
        [
            "",
            "## Error Sources To Record",
            "",
            "- Lattice constant and whether the structure was optimized or taken from literature.",
            "- QE version and whether `epsilon.x` and hybrid (`input_dft`) are both available.",
            "- Pseudopotential files (must be norm-conserving for epsilon.x) and their provenance.",
            "- `ecutwfc`, `ecutrho`, k-mesh, and `nqx` Fock-grid convergence for PBE, eps, and hybrid.",
            "- Whether epsilon_inf comes from PBE eps.x (RPA, no local fields) or a hybrid recompute.",
            "- That DD-HSE is an approximation, not exact DD-RSH-CAM (long-range topology differs).",
            "- Whether the hybrid run is one-shot or iterated with a recomputed epsilon_inf.",
        ]
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
