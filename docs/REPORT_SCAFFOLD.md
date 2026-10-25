# SeismoNet — College Mini-Project Report Scaffold

**Repository:** `C:\Users\Tanish\dlrl miniproject\SeismoNet`
**Status:** **completed** — the written report is [`REPORT.md`](REPORT.md) (2026-10-21). This file is kept as the section map and the rule for what may be quoted.

Each section below maps to the required report structure. Fill only from `docs/SUPERVISOR_REVIEW_2026-10-18.md`, `docs/PROJECT_STATUS.md`, and `runs/` artifacts; do not fabricate test results.

1. **Introduction** — project goal (per-sample P/S/noise probabilities via 1-D U-Net), what the system does and does not do (see `README.md` “not an earthquake early-warning system” and B1).

2. **Problem Statement and Objectives** — why P/S picking matters and why a frozen evaluation protocol is the deliverable (B2).

3. **Dataset** — INSTANCE Counts, `CC BY 4.0`, `100 Hz ENZ`, `70/15/15` event-level split `aea671c76ce2`, `10k` sample only, `16/8` validation events (`492/210`) — cite B3 and `DATASET_GUIDE.md`.

4. **Methodology** — loading / windowing `L 3072` / `σ` provisional / targets / augmentation / `InstanceDataset` / `SeismoUnet1d base 16 depth 4` / `soft_cross_entropy` / `Adam 1e-3` — cite B4 and `src/seismonet/`.

5. **Model Architecture** — U-Net encoder-bottleneck-decoder with skip connections, `(B,3,3072)→(B,3,3072)` logits → `softmax(dim=1)` — cite B4.

6. **Experimental Setup** — pilot (3 epochs) vs Experiment 002 (20 epochs, same 16/8-event task, seed 42, same `protocol-5fa5744aca58cc3c` `P 0.05 / S 0.10 / tol 20 @ 100 Hz`) and the `argmax P F1` selection rule — cite B5 and `runs/*/run.json`.

7. **Results** — validation-only table (B6) with `147/49/63 P 0.750/0.700/0.724` vs pilot `0.03`, per-epoch `loss_and_f1.png`, event-level breakdown — cite `runs/experiment_002_p_training/analysis/event_breakdown.json`.

8. **Error Analysis** — FP/FN counts, residual median `12` samples, galleries `analysis/trace_*.png` and `residual_histograms.png`, remaining `P FN 63 / FP 49` (worst `11043661` `0.519`) — cite B7 and `analysis/`.

9. **Limitations** — 8 isolation points in B8 (small task, event dependence, missing full archive, optimistic validation bias, test not evaluated, S still `0.52`, tol-specific scores, no generalisation).

10. **Conclusion** — same 1-D U-Net learns useful P features when trained past the pilot (`0.03→0.72` under one frozen protocol) but the number is validation-biased and a held-out evaluation is still required — cite B9.

11. **References** — PhaseNet (`https://github.com/AI4EPS/PhaseNet`) and INSTANCE (`doi:10.13127/instance`, CC BY 4.0) as recorded in `DATASET_GUIDE.md` and `REASONING_AND_DECISIONS.md`; list any additional citation as “requiring verification” per `README.md`.

> Test split: **not evaluated** — leave any test-results section as “Pending supervisor approval (B10)” until approval is recorded.

---

## Completion note (2026-10-21)

Every section above has been written up in [`REPORT.md`](REPORT.md) using the artifacts listed in that
document's Appendix B. Two deviations from the scaffold were necessary and are recorded in change-log
entry `2026-10-21-002`:

- the **architecture** description was taken from `src/seismonet/model.py` (`Conv1d(kernel_size=3,
  padding=1)`, `kernel_size=1` head), not from the design documents;
- the **event-level S F1** values were taken from
  `runs/experiment_002_p_training/analysis/event_breakdown.json`, and four cells that disagreed with it
  in `docs/SUPERVISOR_REVIEW_2026-10-18.md` were corrected there.

The report contains **no test results**, because the held-out evaluation is not approved.
