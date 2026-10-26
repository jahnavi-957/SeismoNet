# Viva questions and answers

Likely questions for the SeismoNet mini-project, with short answers you can say out loud. **★** marks the
ones most likely to be asked. Numbers are all verified from the repository.

---

## A. Fundamentals

**★ A1. What is your project, in one sentence?**
A deep-learning model that reads a three-component seismogram and marks when the P and S waves arrive — the
task seismologists call phase picking.

**★ A2. What exactly are P and S waves?**
Both come from the same rupture. P is the fast compressional wave, small amplitude, arrives first. S is slower,
shear, larger amplitude and carries most of the damaging shaking. The delay between them encodes distance.

**★ A3. Why is picking needed?**
Every downstream step — location, depth, magnitude, early warning, catalogs — starts from arrival times.
Today analysts pick by hand, which is slow and subjective, and modern networks produce far more data than they
can pick.

**★ A4. Is this earthquake prediction or early warning?**
No. It measures arrivals in a wave that has *already been recorded*. Early warning needs streaming, dense
networks, association and magnitude estimation; we build the picking stage those systems depend on.

**A5. What is a "trace"?**
One station's recording of one earthquake, cut to one 3,072-sample window. Name format:
`event.network.station..channel`, e.g. `1128071.IV.ASSB..HH`.

**A6. Why is your model useful if it can't locate an earthquake?**
Because picking is the bottleneck step that *every* other task consumes. One focused component, measured
honestly, is a better contribution than a shallow end-to-end attempt.

---

## B. Dataset

**★ B1. What data did you use?**
INSTANCE Counts (Italy), CC BY 4.0, 100 Hz, three components ENZ, records of 12,000 samples (120 s). We used a
300-event, 10,000-trace sample; the full archive is 54,008 events.

**★ B2. How did you split train/validation/test?**
At **event level**, never at trace level, so no earthquake appears in two splits. Verified programmatically:
zero event overlap, split hash `aea671c76ce2`.

**★ B3. Why event-level?**
Traces from one earthquake share source and path, so a trace-level split would let the model "recognise the
earthquake" rather than learn phase picking — an inflated score. Event-level splitting is what makes the test
number a generalisation claim.

**★ B4. How much data did the model actually train on?**
16 events / 492 traces. Validation 8 events / 210 traces. Test 45 unseen events / 1,472 traces, opened once.

**B5. Why only 16 training events?**
Compute bound: a 4 GiB laptop GPU, and the mini-project scope. Documented as a limitation; scaling is the
obvious next step.

**B6. Why 3,072-sample windows?**
At 100 Hz that is 30.72 s — enough to contain both arrivals. It is also 3 × 2¹⁰, divisible by 2⁴ for the four
pooling stages. 3,000 was rejected because 3,000 ÷ 16 is not an integer.

**B7. How are the windows positioned?**
Deterministically centred on the P/S midpoint for validation and test (so every trace is scored fairly);
randomised between 25 % and 75 % of the window during training, so the model can't rely on "arrivals are in
the middle".

**B8. What preprocessing?**
Per-window demeaning and peak normalisation — statistics from the window only, so no information leaks across
traces and raw instrument units stop mattering.

**B9. Why are some traces missing an S arrival?**
The S wave arrives outside the 30.72 s window for distant events: 595 of 1,472 test traces have no S reference.
Those are excluded from S recall, not counted as misses.

---

## C. Model

**★ C1. What model did you build?**
A 1D U-Net: four encoder levels, four decoder levels, skip connections, 678,707 trainable parameters, width 16.

**★ C2. Why a U-Net?**
The output must be per-sample, not one label per window — that's what gives millisecond timing. The encoder
gives context, the decoder restores resolution, and the skip connections carry fine timing detail straight
across. A plain CNN or a classifier cannot produce a 3,072-sample probability curve.

**★ C3. How many parameters, and where are they?**
678,707. The bottleneck block `down3` holds 295,936 (44 %); the first decoder block `up0` another 213,632
(31 %). The head is 51 parameters.

**★ C4. What is the input and output?**
Input `(batch, 3, 3072)`, output `(batch, 3, 3072)` logits, softmax over the class axis → P / S / noise
probabilities that sum to 1 at every sample.

**★ C5. What is the receptive field?**
230 samples ≈ 2.3 s, computed from the convolution/pooling arithmetic. Enough to see a whole P wavelet, not so
large that timing blurs.

**C6. Why `bias=False` on the convolutions?**
Each one is followed by BatchNorm, whose shift makes a conv bias redundant. Saves parameters and changes
nothing.

**C7. Why a 1×1 output convolution?**
It maps 16 feature channels to 3 class scores per sample without mixing neighbouring samples — the timing
decision stays local.

**C8. Why is depth fixed at 4?**
The implementation raises an error for other depths: the length must stay divisible by 2^depth. Fixed depth
makes the shape contract explicit instead of silently padding.

**C9. How big is the model in practice?**
2.63 MB on disk, 262 M multiply-accumulates per window (≈0.5 GFLOP), ~40 ms per window on CPU.

---

## D. Training

**★ D1. What loss, and why?**
Soft-target cross-entropy over Gaussian-smoothed labels (σ = 20 samples = 200 ms), with all-zero targets where
a phase is absent. Soft targets stop the model chasing the exact sample an analyst clicked; analyst picks carry
their own uncertainty.

**★ D2. Hyperparameters?**
Adam, lr 1e-3, weight decay 1e-4, batch 4, 20 epochs, seed 42, best epoch 11 selected by validation P F1.
~10 s per epoch, 49 MiB peak memory.

**★ D3. How did you choose the final model?**
By maximum validation P F1 (epoch 11). The test set played no part in any choice — that's the point of freezing.

**D4. Any regularisation? Only weight decay; augmentation was implemented and deliberately left off so the
baseline is the unaugmented pipeline.

**D5. Did it overfit?**
Not by the evidence: validation loss 0.0787, train 0.0587, and P F1 fell only from 0.724 (validation) to 0.685
(test). The gap is the optimism of tuning on validation, not overfitting.

**D6. Why not train longer / bigger?**
Time and a 4 GiB GPU. The loss curves and the σ ablation showed diminishing returns; capacity was not the
limiting factor.

---

## E. Evaluation

**★ E1. What are your headline results?**
Held-out test: **P F1 0.685** (precision 0.704, recall 0.667, TP/FP/FN 982/413/490) and **S F1 0.499**
(0.455 / 0.552, 484/579/393). Median P timing error 110 ms, S 140 ms.

**★ E2. How is a pick judged correct?**
If it lies within **20 samples = 200 ms** of the reference arrival. Otherwise it is a false positive, and a
missed reference is a false negative.

**★ E3. Why F1 and not accuracy?**
Accuracy would be ~99 % because almost every sample is noise — a flattering, meaningless number. Phase picking
is a needle-finding task, so precision/recall/F1 are the honest metrics.

**★ E4. Why is test (0.685) lower than validation (0.724)?**
The best epoch *and* the thresholds were chosen on the validation set, so validation is optimistically biased.
Test was touched once, after freezing, which is why it is the number we quote. Reporting both is the finding.

**★ E5. Why is S so much worse than P?**
S onsets are emergent and lower-frequency, often arriving inside the P coda. S precision 0.455 means more than
half of S detections are spurious. It is the project's known weak point, reported rather than hidden.

**E6. What are the frozen thresholds?**
P > 0.05, S > 0.10, local maxima at least 20 samples apart, under `protocol-5fa5744aca58cc3c`, fixed before the
test set was opened.

**E7. Is the tolerance arbitrary?**
It is a protocol choice — 200 ms at 100 Hz. F1 changes with tolerance, so we state it every time. That is why
cross-paper comparisons need care.

**E8. What did the ablation show?**
A pre-registered σ sweep (10 / 20 / 40) with a seed-43 noise-floor arm. Differences stayed within seed
variability, which is reported as a negative result — that is a legitimate outcome.

---

## F. Limitations and next steps

**★ F1. What are the main limitations?**
One dataset, 16 training events, single-station windows, at most one pick per phase per window, no real-time
streaming, and S precision of 0.455.

**★ F2. If you had more time?**
Train on all 213 training events in the sample (and eventually the full archive), investigate the S false-positive
rate, add multi-station association, then streaming for live picking.

**★ F3. Could someone misuse this?**
Yes, if they read F1 as accuracy or apply it outside the trained region. That is why the documentation, the app
and the report all state the scope and the held-out protocol explicitly.

**F4. What was the hardest part?**
Getting the evaluation honest: event-level splits, freezing the protocol before touching test, and refusing to
quote the biased validation number.

---

## G. Web application

**★ G1. What did you build around the model?**
A FastAPI service plus a React/Vite UI: Overview, Phase Picker, CSV Upload, Model Evaluation, About. One Docker
container serves both on the same origin; 1.93 GB, 210 MiB idle, 228 MiB peak.

**★ G2. How does a user's CSV get processed?**
Multipart upload → structure validation → grouping into 3,072-sample windows by `trace_id` → demean and
peak-normalise → frozen U-Net forward pass → threshold to picks → JSON with picks, probabilities and curves.
The file is parsed in memory and never stored.

**★ G3. What is the upload contract?**
Exactly 3,072 samples per trace at 100 Hz, finite numeric values, S after P, ≤ 50 MB, ≤ 100,000 rows (≈32 traces).

**★ G4. In the browser demo, does the Phase Picker run the model?**
No — when the raw dataset is absent it returns `synthetic_demo_fallback`, and an amber banner says the model is
not running. The CSV path genuinely runs the frozen checkpoint.

**★ G5. Are the demo CSVs real recordings?**
No. They are generated from the recorded reference arrivals; the page and `samples/README.md` say so. They
demonstrate the software path, not model performance.

---

## H. Rapid fire

| Question | Answer |
|---|---|
| Parameters | 678,707 trainable (681,669 numbers in the file including BN buffers) |
| Architecture | 1D U-Net, depth 4, base 16, skip connections |
| Input | 3 × 3,072 samples, ENZ, 100 Hz, 30.72 s |
| Output | 3 × 3,072 probabilities per sample, P / S / noise |
| Loss | soft-target cross-entropy, Gaussian σ = 20 samples |
| Optimiser | Adam, 1e-3 |
| Epochs | 20, best 11 by validation P F1 |
| Test P F1 | 0.685 |
| Test S F1 | 0.499 |
| Tolerance | 20 samples = 200 ms |
| Thresholds | P 0.05, S 0.10 |
| Training events | 16 (492 traces) |
| Test events | 45 unseen (1,472 traces) |
| Dataset | INSTANCE Counts, Italy, CC BY 4.0 |
| Inference cost | ~40 ms per window on CPU, 262 M MACs |
| Model file | 2.63 MB, `runs/experiment_002_p_training/best.pt` |
| Tests | 190 passed, 36 skipped (skips need the raw HDF5) |
| Is it EEW? | No — picking only |
| Novelty | Engineering + honest evaluation, not a new architecture |

---

## I. Traps to avoid

1. **Never say "predicts earthquakes"** or "early warning system". Say "phase picking / arrival timing".
2. **Never quote validation 0.724 without saying it is biased.**
3. **Never call the demo CSVs real data.**
4. **Never say F1 is accuracy.**
5. **Never claim S works well** — 0.455 precision is the honest figure.
6. **If you don't know:** "That wasn't measured; the closest thing we have is X" beats inventing a number.
   Examiners reward the boundary far more than a guess.
