---
title: SeismoNet
emoji: 🌊
colorFrom: blue
colorTo: slate
sdk: docker
app_port: 7860
pinned: false
---

# SeismoNet — seismic P/S phase picking

Deep-learning phase picker: a 1D U-Net reads a three-component waveform window and marks the P- and
S-wave arrival times. This Space serves the same container as the repository below — FastAPI on the same
origin as the built React UI.

- **Source:** <https://github.com/jahnavi-957/SeismoNet>
- **Try it:** open the app → **CSV Upload** → upload `samples/demo_12traces_predict.csv` from the repository →
  map **Trace ID → `trace_id`** → **Validate CSV** → **Run real model analysis**
- **Benchmark:** held-out test P F1 `0.685`, S F1 `0.499` (1,472 traces, 45 unseen events)

This is a phase picker, not an earthquake predictor or an early-warning system.

> Deploying: this file supplies the Hugging Face Space metadata (`sdk: docker`, `app_port: 7860`). Copy it
> over the Space's `README.md` after pushing the repository; the project's own README stays on GitHub.
