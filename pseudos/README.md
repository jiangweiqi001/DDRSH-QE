# Pseudopotentials

The QE inputs expect norm-conserving (NC) PBE pseudopotentials in this directory.
Norm-conserving is required because `epsilon.x` needs the optical matrix elements
that NC pseudopotentials provide cleanly.

Expected files (referenced in every `*.in`):

```text
Mg_ONCV_PBE-1.2.upf
O_ONCV_PBE-1.2.upf
```

## Where to get them

Download ONCV scalar-relativistic PBE pseudopotentials from PseudoDojo
(https://www.pseudo-dojo.org), "NC SR (ONCVPSP v0.4)", PBE, standard accuracy,
UPF format. Place the two UPF files in this folder with the names above, or edit
the `ATOMIC_SPECIES` lines in the inputs to match the names you downloaded.

## Important consistency note

Use the same pseudopotentials for every step (PBE SCF, epsilon, DDH, DD-HSE).
Hybrid band gaps shift with the pseudopotential choice, so record the exact files
used in `results/MgO-ddrsh-summary.md`.

If you increase or decrease the pseudopotential hardness, re-check `ecutwfc` and
`ecutrho` convergence in all inputs.
