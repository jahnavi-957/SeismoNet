import React from 'react';
import { BookOpen, Info } from 'lucide-react';
import { CsvAnalysisResult, CsvMapping, CsvValidationResult } from '../types';

interface Props {
  analysis: CsvAnalysisResult;
  validation: CsvValidationResult | null;
  mapping: CsvMapping;
  fileName?: string;
}

const yesNo = (value: boolean | null | undefined) =>
  value == null ? '—' : value ? 'inside tolerance' : 'outside tolerance';

const fmt = (value: number | null | undefined, digits = 0) =>
  value == null ? 'no pick' : value.toLocaleString(undefined, { maximumFractionDigits: digits });

/**
 * Plain-language explanation of what the uploaded CSV produced. Every number shown here
 * comes from the API response; the text describes the pipeline in the order it runs.
 */
const ResultExplainer: React.FC<Props> = ({ analysis, validation, mapping, fileName }) => {
  const protocol = analysis.protocol;
  const predictions = analysis.predictions.slice(0, 8);
  const isCompare = analysis.mode === 'compare';
  const columns = [
    validation?.mapping?.e_col || mapping.e_col,
    validation?.mapping?.n_col || mapping.n_col,
    validation?.mapping?.z_col || mapping.z_col,
  ].filter(Boolean) as string[];

  return (
    <section className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
      <header className="flex items-start gap-3">
        <BookOpen className="mt-1 shrink-0 text-cyan-400" size={20} />
        <div>
          <h2 className="text-xl font-bold text-white">What just happened?</h2>
          <p className="mt-1 text-sm text-slate-400">
            A plain-language walk-through of your file, what the model did with it, and what the
            numbers on this page mean.
          </p>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">1. What you uploaded</h3>
          <ul className="mt-3 space-y-1.5 text-sm leading-6 text-slate-300">
            <li><strong className="text-white">File:</strong> {fileName || 'uploaded CSV'}</li>
            <li><strong className="text-white">Rows:</strong> {(validation?.row_count ?? 0).toLocaleString()} data rows</li>
            <li><strong className="text-white">Traces found:</strong> {analysis.trace_count} (one trace = one 3,072-sample window)</li>
            <li><strong className="text-white">Sampling rate:</strong> {analysis.input_sampling_rate_hz} Hz → used at {analysis.effective_sampling_rate_hz} Hz</li>
            <li><strong className="text-white">Window length:</strong> 3,072 samples ≈ 30.7 seconds of ground motion</li>
          </ul>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">2. How the file was read</h3>
          <ol className="mt-3 space-y-1.5 text-sm leading-6 text-slate-300">
            <li>1. Your columns were matched to the three sensors: <strong className="text-white">East, North, Vertical</strong>{columns.length ? ` (${columns.join(', ')})` : ''}.</li>
            <li>2. Rows were grouped into traces; each trace must be exactly 3,072 samples long.</li>
            <li>3. Each trace was <strong className="text-white">demeaned</strong> (average removed) and <strong className="text-white">peak-normalised</strong> (largest value scaled to 1.0), so raw units do not matter.</li>
            <li>4. The three channels were stacked as one 3×3,072 block and sent to the model.</li>
          </ol>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">3. What the model did</h3>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          For <strong className="text-white">every single sample</strong> (all 3,072 of them) the frozen 1D U-Net
          output three probabilities that sum to 1: how likely that moment is a <strong className="text-amber-300">P-wave</strong>,
          an <strong className="text-fuchsia-300">S-wave</strong>, or <strong className="text-slate-300">noise</strong>.
          Those are the curves drawn above.
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-300">
          A <strong className="text-white">pick</strong> is then placed at the strongest local peak of a curve, but only if
          the peak clears a fixed threshold: <strong className="text-white">P &gt; {protocol.p_threshold}</strong> and{' '}
          <strong className="text-white">S &gt; {protocol.s_threshold}</strong>, with peaks at least{' '}
          {protocol.matching_tolerance_samples} samples apart. If no peak clears the threshold, the honest answer is
          &ldquo;no pick&rdquo; — that is a result, not an error.
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-slate-800/70 text-slate-300">
            <tr>
              <th className="px-3 py-2">Trace</th>
              <th className="px-3 py-2">P pick (sample)</th>
              <th className="px-3 py-2">P (ms)</th>
              <th className="px-3 py-2">P probability</th>
              <th className="px-3 py-2">S pick (sample)</th>
              <th className="px-3 py-2">S (ms)</th>
              <th className="px-3 py-2">S probability</th>
              {isCompare && <th className="px-3 py-2">P residual</th>}
              {isCompare && <th className="px-3 py-2">S residual</th>}
            </tr>
          </thead>
          <tbody>
            {predictions.map((prediction, index) => {
              const comparison = analysis.comparisons?.find((item) => item.index === prediction.index);
              return (
                <tr key={`${prediction.trace_id || index}`} className="border-t border-slate-800 text-slate-300">
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-slate-200">{prediction.trace_id || `Trace ${index + 1}`}</td>
                  <td className="px-3 py-2 font-mono">{fmt(prediction.p_predicted_sample)}</td>
                  <td className="px-3 py-2 font-mono">{fmt(prediction.p_predicted_ms, 0)}</td>
                  <td className="px-3 py-2 font-mono">{prediction.p_probability == null ? '—' : prediction.p_probability.toFixed(3)}</td>
                  <td className="px-3 py-2 font-mono">{fmt(prediction.s_predicted_sample)}</td>
                  <td className="px-3 py-2 font-mono">{fmt(prediction.s_predicted_ms, 0)}</td>
                  <td className="px-3 py-2 font-mono">{prediction.s_probability == null ? '—' : prediction.s_probability.toFixed(3)}</td>
                  {isCompare && (
                    <td className="px-3 py-2 font-mono">
                      {comparison?.p_residual_ms == null ? '—' : `${comparison.p_residual_ms.toFixed(0)} ms (${yesNo(comparison.p_within_tolerance)})`}
                    </td>
                  )}
                  {isCompare && (
                    <td className="px-3 py-2 font-mono">
                      {comparison?.s_residual_ms == null ? '—' : `${comparison.s_residual_ms.toFixed(0)} ms (${yesNo(comparison.s_within_tolerance)})`}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {analysis.predictions.length > predictions.length && (
        <p className="text-xs text-slate-500">Showing the first {predictions.length} of {analysis.predictions.length} traces. Use the trace selector above and Export JSON for the rest.</p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">4. How to read the numbers</h3>
          <ul className="mt-3 space-y-1.5 text-sm leading-6 text-slate-300">
            <li><strong className="text-white">Sample:</strong> position in the window, 0–3,071. At 100 Hz, sample 1,500 = 15.0 s.</li>
            <li><strong className="text-white">ms:</strong> the same position converted to milliseconds.</li>
            <li><strong className="text-white">Probability:</strong> how strongly the model believes that instant is that phase. 0.60 is a confident pick; 0.11 is barely over the threshold.</li>
            <li><strong className="text-white">&ldquo;No pick&rdquo;:</strong> nothing cleared the threshold — usually because the wave is weak, buried in noise, or absent.</li>
            {isCompare && (
              <li><strong className="text-white">Residual:</strong> predicted minus your reference. A pick counts as correct only if it is within {protocol.matching_tolerance_samples} samples ({protocol.matching_tolerance_samples * 10} ms).</li>
            )}
          </ul>
        </div>

        <div className="rounded-xl border border-amber-800/50 bg-amber-950/10 p-5">
          <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-amber-300">
            <Info size={15} /> 5. What this result does not mean
          </h3>
          <ul className="mt-3 space-y-1.5 text-sm leading-6 text-amber-100/90">
            <li>It is <strong>not</strong> an earthquake prediction, location, or magnitude — only arrival times of P and S.</li>
            <li>Metrics on this page describe <strong>your uploaded file only</strong>. They are not the model&rsquo;s general accuracy.</li>
            <li>A synthetic or noise-only file proves the software works; it says nothing about real seismic performance.</li>
            <li>The model&rsquo;s honest benchmark is the one-time held-out test on the <strong>Model Evaluation</strong> page (P F1 0.685, S F1 0.499).</li>
          </ul>
        </div>
      </div>

      {isCompare && analysis.metrics && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">6. Upload-only comparison metrics</h3>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            <strong className="text-white">TP</strong> = pick within tolerance, <strong className="text-white">FP</strong> = pick with no matching reference,
            <strong className="text-white"> FN</strong> = a reference the model missed. Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 balances the two.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {(['p_metrics', 's_metrics'] as const).map((key) => {
              const metric = analysis.metrics?.[key];
              if (!metric) return null;
              return (
                <div key={key} className="rounded-lg bg-slate-900/60 p-3 text-sm text-slate-300">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{key === 'p_metrics' ? 'P-wave' : 'S-wave'}</p>
                  <p className="mt-1 font-mono text-xs">
                    precision {metric.precision.toFixed(3)} · recall {metric.recall.toFixed(3)} · F1 {metric.f1.toFixed(3)}
                  </p>
                  <p className="mt-1 font-mono text-xs text-slate-500">TP {metric.tp} / FP {metric.fp} / FN {metric.fn}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
};

export default ResultExplainer;
