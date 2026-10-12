# SeismoNet: Deep Learning-Based Seismic Phase Detection

SeismoNet is a deep learning mini-project that aims to identify **P-wave
and S-wave arrival times** in seismic waveform recordings. It uses a
**1D U-Net architecture inspired by PhaseNet** to predict the
probability of P-wave arrivals, S-wave arrivals, and noise across a
waveform.

The project is intended as a research and educational prototype for
analysing seismic data. It is not a replacement for expert judgement or
validated operational earthquake-monitoring systems.

## Problem Statement

Identifying seismic phase arrival times is an important step in
earthquake analysis and seismic monitoring. Traditionally, analysts
manually inspect waveforms to identify the arrival of primary (P) and
secondary (S) waves. Manual picking can be time-consuming, particularly
when large numbers of recordings must be processed, and picks may vary
between analysts.

SeismoNet aims to build a deep learning-based phase-picking pipeline
that processes labelled seismic waveforms, predicts P- and S-wave
arrival times, and evaluates predictions against reference annotations.
The project will also investigate how selected training configurations
and waveform noise affect performance.

## Objectives

-   Prepare and inspect labelled seismic waveform data.
-   Implement and train or fine-tune a 1D U-Net-based phase detector.
-   Predict per-time-step probabilities for P waves, S waves, and noise.
-   Extract predicted phase-arrival times from model outputs.
-   Evaluate predictions against reference labels using suitable
    metrics.
-   Compare controlled experiment versions and document the effect of
    configuration changes.
-   Visualise waveforms, reference arrivals, predicted arrivals, and
    model outputs.
-   Provide a simple interface for exploring supported waveform
    recordings.

## Target Users

**Primary users** - Seismologists and earthquake researchers. - Seismic
data analysts. - Geophysics research laboratories.

**Secondary users** - Geophysics students. - University researchers
studying seismic signals and deep learning. - Academic teams evaluating
automated seismic phase picking.

SeismoNet is intended to assist these users by making phase-picking
predictions easier to inspect and evaluate. It does not independently
determine whether an earthquake is occurring or provide emergency
warnings.

## How It Works

1.  **Load waveform data:** Read seismic recordings and the associated
    metadata and reference phase-arrival labels.
2.  **Preprocess:** Validate waveform dimensions, sampling rate,
    component order, missing values, and label availability. Apply the
    preprocessing required by the selected model.
3.  **Run the model:** Feed the waveform into the 1D U-Net.
4.  **Predict probabilities:** Produce probabilities for P-wave
    arrivals, S-wave arrivals, and noise at each time step.
5.  **Extract picks:** Identify candidate P and S arrivals from the
    probability outputs using a documented peak-picking procedure.
6.  **Evaluate:** Compare predicted picks with reference annotations on
    held-out data.
7.  **Record experiments:** Save model settings, data splits, random
    seeds, metrics, and outputs so that runs can be compared.
8.  **Visualise results:** Plot the waveform, reference arrivals,
    predicted arrivals, and probability curves.

## Deep Learning Approach

The planned model is a **one-dimensional U-Net**, inspired by PhaseNet.

-   **Encoder:** Convolutional layers learn waveform features at
    different temporal scales.
-   **Skip connections:** Preserve detailed temporal information between
    encoder and decoder layers.
-   **Decoder:** Produces time-step predictions for the phase classes.
-   **Output:** P-wave, S-wave, and noise probabilities.

The model will be trained or fine-tuned using labelled seismic data and
a suitable loss function. The exact architecture, preprocessing,
training settings, and source implementation will be documented in the
final project report.

> Important: Using a pretrained model to generate predictions is not, by
> itself, evidence that the team trained a deep learning model. The
> project will record the actual training or fine-tuning process and
> preserve training logs and checkpoints where feasible.

## Dataset

The project will use a publicly available seismic dataset with suitable
waveform data and P/S arrival annotations. The initial implementation
should use a manageable subset so the team can validate the complete
pipeline before scaling up.

Potential starting points: - [PhaseNet official
repository](https://github.com/AI4EPS/PhaseNet) --- implementation,
documentation, and example workflows. - [STEAD
dataset](https://github.com/smousavi05/STEAD) --- Stanford Earthquake
Dataset resources.

Before running experiments, the team must confirm the dataset's licence
and terms, waveform format, sampling rate, component ordering, label
conventions, and download requirements. The dataset should not be
assumed to be downloaded or configured merely because it is listed here.

### Data-splitting precautions

-   Keep training, validation, and test data separate.
-   Use the validation set for model and threshold decisions.
-   Evaluate final performance on held-out test data.
-   Where metadata permits, avoid leakage between recordings from the
    same event or closely related records across splits.
-   Document missing labels and how they are handled.

## Evaluation

The model will be evaluated against reference arrival annotations.
Planned metrics include:

-   **Precision:** The proportion of predicted phase picks that match
    reference picks under the chosen matching rule.
-   **Recall:** The proportion of reference picks detected by the model.
-   **F1-score:** The harmonic mean of precision and recall.
-   **Arrival-time error:** The difference between a predicted pick and
    its matched reference arrival, reported in samples or seconds.
-   **Median and mean absolute error:** Summaries of the magnitude of
    arrival-time errors.
-   **Tolerance-based recall:** The proportion of reference arrivals
    detected within a specified time tolerance.

P-wave and S-wave results should be reported separately. The matching
tolerance and peak-picking rules must be stated clearly. A confusion
matrix may be included where the evaluation formulation makes it
meaningful.

The project will report measured results rather than promise a target
accuracy in advance.

## Planned Experiments

1.  **Baseline run:** Train or fine-tune the model with a documented
    initial configuration.
2.  **Configuration comparison:** Change one major setting, such as
    learning rate, epoch count, or training-data fraction, while keeping
    the evaluation protocol fixed.
3.  **Noise analysis:** Evaluate selected recordings under documented
    noise conditions, if time and data permit.
4.  **Error analysis:** Inspect missed arrivals, false picks, and cases
    where predicted arrivals differ from reference labels.

Changes in results should be interpreted carefully. If multiple settings
change at once, the experiment may not establish which change caused the
difference.

## Planned Technology Stack

-   **Python** --- core implementation.
-   **PyTorch** --- deep learning.
-   **Hugging Face / scientific Python tools** --- as needed for the
    selected implementation.
-   **NumPy and Pandas** --- numerical data and metadata handling.
-   **Scikit-learn** --- supporting metrics where appropriate.
-   **Matplotlib / Plotly** --- waveform and result visualisation.
-   **Streamlit** --- planned lightweight demonstration interface.
-   **Git and GitHub** --- source control and collaboration.

The final dependencies will be recorded in `requirements.txt` after the
working environment has been verified.

## Planned Repository Structure

``` text
SeismoNet/
├── data/                 # Dataset instructions or locally stored data
├── notebooks/            # Exploration and experiments
├── src/
│   ├── preprocessing.py  # Waveform loading and preprocessing
│   ├── model.py          # Model definition or integration
│   ├── train.py          # Training or fine-tuning
│   ├── predict.py        # Inference and phase-pick extraction
│   └── evaluate.py       # Evaluation and metrics
├── models/               # Saved checkpoints (if appropriate)
├── results/              # Metrics, predictions, and plots
├── reports/              # Experiment records and final report
├── app/                  # Demonstration interface
├── requirements.txt
├── README.md
└── .gitignore
```

This is the intended structure; files will be added as implementation
progresses.

## One-Week Development Plan

  -----------------------------------------------------------------------
  Day                                 Planned work
  ----------------------------------- -----------------------------------
  1                                   Set up the environment, inspect the
                                      dataset, validate labels, and plot
                                      sample waveforms.

  2                                   Build preprocessing and get an
                                      end-to-end model run working.

  3                                   Train or fine-tune the model and
                                      save checkpoints and logs.

  4                                   Implement phase-pick extraction and
                                      evaluation metrics.

  5                                   Run a controlled configuration
                                      comparison and inspect errors.

  6                                   Build the interface and visualise
                                      predictions and metrics.

  7                                   Test the workflow, document results
                                      and limitations, and prepare for
                                      the viva.
  -----------------------------------------------------------------------

This is a target schedule, not a claim that the implementation is
already complete. If time is limited, prioritise a working training and
evaluation pipeline over extra interface features.

## Team Responsibilities

For a team of three, responsibilities can be divided as follows:

-   **Member 1 --- Data:** Dataset inspection, waveform preprocessing,
    metadata and visualisation.
-   **Member 2 --- Model:** Model integration, training/fine-tuning,
    checkpoints and training logs.
-   **Member 3 --- Evaluation and application:** Arrival-time metrics,
    experiment comparisons, plots and interface.

All members should understand the full pipeline and be prepared to
explain the model, labels, evaluation protocol, and limitations.

## Limitations and Responsible Use

-   Model performance depends on the dataset, sensor characteristics,
    sampling rate, noise conditions, and label quality.
-   A model trained on one dataset may not generalise to other regions,
    stations, or recording systems.
-   Missing or uncertain reference picks can affect evaluation.
-   Predicted probability is not the same as verified correctness.
-   The prototype is for research and educational use, not an
    operational earthquake early-warning or emergency-response system.
-   Any claim of reproducing PhaseNet or another published result must
    be supported by a documented protocol and a fair comparison with the
    original study.

## Current Project Status

This README describes the **planned project scope**. Dataset selection,
implementation details, training runs, measured results, and screenshots
should be updated as the project is built. Do not report planned
features as completed features.

## References

-   Zhu, W. et al. (2021). *PhaseNet: A deep-neural-network-based
    seismic arrival-time picking method*. [Official implementation and
    documentation](https://github.com/AI4EPS/PhaseNet).
-   Mousavi, S. M. et al. *Stanford Earthquake Dataset (STEAD)*.
    [Dataset repository](https://github.com/smousavi05/STEAD).

## Team

**Project:** SeismoNet\
**Domain:** Deep Learning, Signal Processing, Seismology\
**Model direction:** 1D U-Net inspired by PhaseNet\
**Status:** In development
