# Results

| File | Description |
| --- | --- |
| [`MgO-results.md`](MgO-results.md) | **Main summary** — production setup, gaps, claims |
| [`MgO-results.json`](MgO-results.json) | Same numbers, machine-readable |
| [`MgO-audit.md`](MgO-audit.md) | Convergence audit appendix (2026-06-16) |
| [`MgO-ddrsh-summary.md`](MgO-ddrsh-summary.md) | Legacy auto-generated table (DDH + strict) |
| [`MgO-qe-summary.json`](MgO-qe-summary.json) | PBE gap + DFPT ε∞ from `epsilon.x` / `ph.x` |

Regenerate audit table after new runs:

```bash
python3 scripts/collect_audit_gaps.py
```
