import React from 'react';

const AboutProject: React.FC = () => (
  <div className="mx-auto max-w-5xl space-y-6 p-6 pb-10">
    <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">Project scope</p>
      <h1 className="mt-3 text-3xl font-bold text-white">About SeismoNet</h1>
      <p className="mt-4 max-w-3xl leading-7 text-slate-300">
        SeismoNet is a college research prototype for identifying P-wave and S-wave arrivals in a
        recorded three-component seismic waveform. A 1D U-Net produces one probability curve per
        class: P wave, S wave, and background/noise.
      </p>
      <div className="mt-6 rounded-xl border border-amber-800/60 bg-amber-950/20 p-4 text-sm text-amber-100">
        This is a phase-picking and waveform-analysis tool. It is not an earthquake prediction,
        earthquake early-warning, location, magnitude, or real-time monitoring system.
      </div>
    </section>

    <div className="grid gap-6 md:grid-cols-2">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <h2 className="text-lg font-semibold text-white">Method</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
          <li><strong className="text-cyan-300">Input:</strong> ENZ waveform window, 3,072 samples at an effective 100 Hz.</li>
          <li><strong className="text-cyan-300">Preprocessing:</strong> per-window demeaning and global peak normalization.</li>
          <li><strong className="text-cyan-300">Model:</strong> `SeismoUnet1d`, base width 16, depth 4, 678,707 parameters.</li>
          <li><strong className="text-cyan-300">Picking:</strong> frozen local-maximum protocol with P 0.05, S 0.10, and a 20-sample tolerance.</li>
        </ul>
      </section>
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <h2 className="text-lg font-semibold text-white">Data and evaluation</h2>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
          <li><strong className="text-cyan-300">Dataset:</strong> INSTANCE Counts artifacts documented by the research pipeline.</li>
          <li><strong className="text-cyan-300">Reference:</strong> Experiment 002 checkpoint, epoch 11.</li>
          <li><strong className="text-cyan-300">Evaluation:</strong> P/S precision, recall, F1, and timing residuals under an explicit tolerance.</li>
          <li><strong className="text-cyan-300">Uploads:</strong> CSV files are validated, normalized, inferred, and optionally compared with supplied reference arrivals.</li>
        </ul>
      </section>
    </div>

    <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
      <h2 className="text-lg font-semibold text-white">Limitations</h2>
      <p className="mt-3 text-sm leading-6 text-slate-300">
        The optional raw waveform sample is not present in every checkout, so the trace browser may
        use a clearly-labelled deterministic demo fallback. Uploaded CSVs must represent one
        supported 3,072-sample window per trace (or explicitly grouped traces). Synthetic uploads
        exercise the software pipeline but are not scientific evaluations. Reported validation and
        held-out metrics belong to their documented splits and must not be mixed with user uploads.
      </p>
    </section>
  </div>
);

export default AboutProject;
