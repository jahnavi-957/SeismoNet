# SeismoNet — demo walkthrough for judges

Everything below is verified against the running application. Numbers are from `runs/eval_test_best/metrics.json`
and from the live model.

---

## 0. The one-sentence pitch

> "We built a deep-learning model that reads a three-component seismogram and automatically marks the exact
> instants the P-wave and S-wave arrive — the task seismologists call phase picking."

## 1. Why anyone cares (say this in ~20 seconds)

An earthquake sends two waves. The **P-wave** is fast and small; the **S-wave** is slower and carries most of the
shaking damage. Because P arrives first, detecting it quickly is what makes early warning possible — every second
counts. Traditionally an analyst marks these arrivals by hand, trace by trace. We automate that.

**Do not say** "we predict earthquakes". You do not. You pick arrival times. Say it plainly — judges respect a
bounded claim more than an inflated one.

## 2. What was actually built (30 seconds, three numbers)

| | |
|---|---|
| Input | one window of **3,072 samples × 3 components** (E, N, Z) at 100 Hz = **30.7 seconds** |
| Model | **1D U-Net**, 4 levels, **678,707 parameters** — outputs a probability curve **per sample** for P, S and noise |
| Output | a **sample index** for the P arrival and one for the S arrival, converted to milliseconds |

Why a U-Net and not a normal classifier: we need a label for *every sample*, not one label per window. That is
what gives millisecond timing. Skip connections carry fine timing detail from encoder to decoder.

## 3. The demo, click by click

Open the app at **http://127.0.0.1:5173** with the backend running on port 8000.

### Step 1 — Overview (10 s)

Point at the top of the page:

> "These are our real held-out results: **P F1 0.685, S F1 0.499**, from 1,472 traces across 45 earthquakes the
> model never saw during training."

### Step 2 — CSV Upload (60 s)

Go to **CSV Upload** and upload:

```
C:\Users\Tanish\Downloads\seismonet_demo_12traces_predict.csv
```

> "This file holds twelve separate 30-second windows — 36,864 rows — from different stations and different
> earthquakes. The `trace_id` column tells the system which rows belong to which window."

On the mapping screen:

> "The system has detected my columns. East, North, Vertical map to the three sensors; `sample_index` is the time
> axis; the sampling rate is 100 Hz. Nothing here is hard-coded to my file."

Click **Validate CSV**.

> "It checks the contract before running anything: every trace must be exactly 3,072 samples, all values must be
> finite and numeric, and if labelled, the S arrival must come after the P arrival."

### Step 3 — Run the model (30 s)

Click **Run real model analysis**. A staged panel appears — **let it play**, narrate it:

> "This is the real pipeline: read the CSV, map the channels, enforce the window contract, demean and
> peak-normalise so the amplitude units don't matter, run the frozen U-Net, threshold the probability curves into
> picks, then draw."

### Step 4 — The result (90 s) — this is the money moment

The page shows three waveform panels and two probability curves. Use the **Trace result** dropdown to pick
trace 1 (`11043661.IV.LNSS..HH`) and read off:

> "On this trace the model places the **P arrival at sample 1,271** — that's **12.71 seconds** into the window —
> with probability **0.49**. The **S arrival at sample 1,674**, that's **16.74 seconds**, probability **0.67**.
> The gap between them, about 4 seconds, is the S-minus-P time — the quantity seismologists use to estimate
> distance to the epicentre."

Then point at the curves:

> "The model doesn't jump straight to a pick. For every one of the 3,072 samples it produces three probabilities
> that sum to one — P, S, noise. The pick is just the strongest local peak that clears a fixed threshold,
> P > 0.05 for P and S > 0.10 for S. That's why you see a curve and a pin, not just a number."

Scroll to **What just happened?** and say:

> "And we wrote the explanation into the page, so anyone opening it understands what the model did instead of
> staring at numbers."

### Step 5 — Model Evaluation (30 s)

Open **Model Evaluation**:

> "This is the honest benchmark. **Precision 0.704, recall 0.667, F1 0.685** for P; **0.455 / 0.552 / 0.499** for S.
> The badge says it: these are held-out test numbers, not the numbers from any uploaded file."

If they ask why 0.685 and not something near 1.0:

> "Because F1 here means 'fraction of arrivals picked within 200 milliseconds of the analyst's pick'. This is a
> finding-a-needle task, so accuracy would be a meaningless 99% — most samples are noise."

## 4. Four claims to avoid

1. **"It predicts earthquakes."** No — it picks arrival times.
2. **"Uploaded results show the model's accuracy."** They show that one file. The benchmark is the Evaluation page.
3. **"S works as well as P."** It doesn't. S precision is 0.455 — over half its S picks are false alarms. Say it
   before a judge finds it.
4. **"The uploaded waveforms are real recordings."** For the web demo we upload a demonstration window set,
   because the multi-gigabyte raw dataset isn't on the demo laptop. The real evaluation used actual INSTANCE
   traces. If asked, say exactly that.

## 5. Likely judge questions

**"Why U-Net?"**
Need per-sample output, not a single label. U-Net keeps the sequence length and skip connections preserve timing
resolution at 678k parameters — small enough for a 4 GB laptop GPU.

**"Why is S so much worse?"**
S waves are emergent, lower-frequency and often clipped or missing in the metadata (595 of 1,472 test traces have
no S reference at all). Precision 0.455 means more than half of S detections are spurious. We report it rather
than hide it.

**"Validation F1 was 0.724, test is 0.685 — regression?"**
No. Epoch and thresholds were selected on validation, so 0.724 is optimistic. Test was touched once, after
freezing. The gap is the size of that optimism — reporting both is the point.

**"How big is your dataset?"**
INSTANCE Counts, a 10,000-trace sample containing 300 events, split event-level so no earthquake appears in two
splits. Training used 16 events (492 traces), validation 8 events (210 traces), and 45 unseen events (1,472
traces) for the one-time test.

**"Is this real-time?"**
No. It's offline analysis of a recorded window, CPU inference in about a second. Real-time streaming is a
documented next step, not a claim.

**"What's the early-warning relevance?"**
P arrives first and is fast; picking it automatically is exactly the trigger step an early-warning system needs.
We do the picking, not the warning.

**"What would you do with more time?"**
Restore the full multi-gigabyte dataset and train on all 213 training events instead of 16; investigate the
S-wave false-positive rate; stream windows for live picking.

## 6. If something breaks

- Charts blank or 400 errors → the backend isn't running. It must be up on port 8000.
- If the demo file won't load, fall back to the screenshots already saved in
  `docs/screenshots/browser-2026-10-25/` and keep talking — the explanation is the demo.
- **Export JSON** on the results page saves every trace's predictions, so you can show the raw output as well.

## 7. Rehearsal checklist

- [ ] Backend running: `http://127.0.0.1:8000/api/health` returns `"status": "online"`
- [ ] Frontend open: `http://127.0.0.1:5173`
- [ ] Demo CSV path copied somewhere easy: `C:\Users\Tanish\Downloads\seismonet_demo_12traces_predict.csv`
- [ ] Trace 1 selected before you start talking about numbers
- [ ] Model Evaluation page pre-loaded in a second tab
- [ ] Time yourself: the whole run should be **under 4 minutes**
