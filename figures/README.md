# Figures

Publication-grade figures for the conformance-aware HTN repair paper. Every
figure is driven by a file in `../results/` (never mocked) and is emitted as both
a vector **PDF** (for the paper) and a 400-dpi **PNG** (for slides/preview) under
`out/`.

## Typographic system (`figstyle.py`)
- one serif/sans pairing: **STIX** serif for axes + tick labels (matches an
  AAAI/NeurIPS Times body), **DejaVu Sans** for direct data labels;
- **Okabe–Ito** colorblind-safe palette, with fixed semantic roles
  (gold/ideal = black, ours = blue, cost-only = vermillion, control = grey,
  o4-mini = blue, gpt-oss = orange, partial-order = green);
- single-column width (3.3 in), tight aspect ratios;
- top/right spines removed, faint y-grid only where a value is read off an axis;
- **no titles/subtitles** (the one-sentence takeaway lives in the LaTeX caption);
- every point/bar carries a black edge and every line a black outline, so marks
  read as bold;
- direct labeling preferred over legends.

## Build
```bash
cd figures
python3 gen_fulldomain_raw.py   # writes ../results/po_fulldomain_raw.json (N5 data)
python3 gen_frontier.py         # writes ../results/frontier.json          (N3 data)
for s in fig_*.py; do python3 "$s"; done   # writes out/<name>.{pdf,png}
```
The two `gen_*.py` scripts only re-sample/measure with the audited pipeline in
`tcr.experiments.*`; they add no new modelling.

## Figure ↔ result ↔ claim
| figure | result file(s) | claim |
|---|---|---|
| `fig_leak_tree` | `data/synthetic.py`, `CLAUDE.md` (schematic) | the gap's cause is a shared compound; placement decides conformant vs leaky |
| `fig_overview` | `po_indifference.json` (annotated precision only) | FIG 1 schematic: minimal-cost repair is precision-blind; ours restores gold behaviour |
| `fig_conformance_gap` | `headline.json` | gap present in every ambiguous family, zero in the control |
| `fig_invisibility` | `headline.json` | gap invisible to target-local negatives, visible only under gold-structural |
| `fig_precision_gain` | `selector_comparison.json` | conformance selection hits precision 1.0 at equal recall |
| `fig_timeline_gap` | `timeline_conformance.json`, `headline.json` | the temporal layer agrees; both controlled |
| `fig_overgen_cliff` | `ipc_overgen_*.jsonl` | real SOTA repairs are a median 0.3% valid at length L |
| `fig_frontier` | `frontier.json` | cost–precision tension; minimal cost is the precision floor |
| `fig_to_vs_po` | schematic (no data) | reordering gap is PO-specific: TO fixes order by position, PO may omit cost-free precedence |
| `fig_cegis_loop` | real Monroe method (counts computed) | CEGIS pins one missing edge per counter-example; 2 edges recover gold (0.40→0.50→1.0) |
| `fig_cegis` | `po_indifference.json`, `po_cegis.json` | CEGIS recovers gold ordering optimally on PO (full 9-domain corpus); gap larger on genuinely-partial gold; no gap on TO |
| `fig_compounding` | `po_fulldomain_raw.json`, `po_fulldomain.json` | over-acceptance compounds geometrically with plan length |

See `RATIONALE.md` for the argument behind each novel figure and `figures.tex`
for the figure environments (one-sentence captions + comment blocks).
