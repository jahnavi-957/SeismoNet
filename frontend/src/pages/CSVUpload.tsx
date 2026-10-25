import React, { useMemo, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Download, FileText, Loader, RotateCcw, Upload } from 'lucide-react';
import CSVResultPlot from '../components/CSVResultPlot';
import { getApiErrorMessage, seismoService } from '../services/api';
import { CsvAnalysisResult, CsvMapping, CsvPrediction, CsvValidationResult } from '../types';

type Step = 'upload' | 'mapping' | 'validation' | 'results';
const steps: Step[] = ['upload', 'mapping', 'validation', 'results'];

const emptyMapping: CsvMapping = {
  sampling_rate_hz: 100,
  arrival_coordinate_type: 'sample_index',
};

const CSVUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<CsvValidationResult | null>(null);
  const [mapping, setMapping] = useState<CsvMapping>(emptyMapping);
  const [mode, setMode] = useState<'predict' | 'compare'>('predict');
  const [analysis, setAnalysis] = useState<CsvAnalysisResult | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [step, setStep] = useState<Step>('upload');
  const [busy, setBusy] = useState<'validating' | 'analyzing' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const mappedColumns = useMemo(() => validation?.columns || [], [validation]);
  const selectedPrediction: CsvPrediction | undefined = analysis?.predictions[selectedIndex];
  const selectedComparison = analysis?.comparisons?.find((item) => item.index === selectedPrediction?.index);

  const reset = () => {
    setFile(null);
    setValidation(null);
    setMapping(emptyMapping);
    setMode('predict');
    setAnalysis(null);
    setSelectedIndex(0);
    setStep('upload');
    setBusy(null);
    setError(null);
    setAnalysisError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const validateSelectedFile = async (nextFile: File, nextMapping?: CsvMapping | null): Promise<CsvValidationResult | null> => {
    setBusy('validating');
    setError(null);
    try {
      const result = await seismoService.validateCSV(nextFile, nextMapping);
      setValidation(result);
      const detected: Partial<CsvMapping> = result.mapping || {};
      setMapping((current) => ({
        ...current,
        ...detected,
        sampling_rate_hz: Number(detected.sampling_rate_hz ?? current.sampling_rate_hz),
        arrival_coordinate_type: detected.arrival_coordinate_type || current.arrival_coordinate_type,
      }));
      setStep('mapping');
      if (!result.is_valid) setError(result.error || result.errors?.[0] || 'CSV validation failed.');
      return result;
    } catch (requestError) {
      setValidation(null);
      setStep('mapping');
      setError(getApiErrorMessage(requestError, 'The backend could not validate this CSV.'));
      return null;
    } finally {
      setBusy(null);
    }
  };

  const handleFile = async (nextFile?: File) => {
    if (!nextFile) return;
    if (!nextFile.name.toLowerCase().endsWith('.csv')) {
      setError('Only .csv files are supported.');
      return;
    }
    if (nextFile.size > 50 * 1024 * 1024) {
      setError('File too large. The maximum upload size is 50 MB.');
      return;
    }
    setFile(nextFile);
    setValidation(null);
    setAnalysis(null);
    setAnalysisError(null);
    setError(null);
    setMapping(emptyMapping);
    setMode('predict');
    setStep('mapping');
    await validateSelectedFile(nextFile, null);
  };

  const updateMapping = (key: keyof CsvMapping, value: string | number) => {
    setMapping((current) => ({ ...current, [key]: value }));
    setValidation((current) => current ? { ...current, is_valid: false } : current);
  };

  const validateMapping = async () => {
    if (!file) return;
    const result = await validateSelectedFile(file, mapping);
    if (result?.is_valid) setStep('validation');
  };

  const runAnalysis = async () => {
    if (!file || !validation?.is_valid) {
      setAnalysisError('Validate the CSV after confirming the column mapping.');
      return;
    }
    if (mode === 'compare' && !validation.has_reference_labels) {
      setAnalysisError('Comparison mode requires a P or S reference column.');
      return;
    }
    setBusy('analyzing');
    setAnalysisError(null);
    try {
      const result = await seismoService.analyzeCSV(file, mapping, mode);
      setAnalysis(result);
      setSelectedIndex(0);
      setStep('results');
    } catch (requestError) {
      setAnalysisError(getApiErrorMessage(requestError, 'Inference failed. The page remains available so you can retry.'));
    } finally {
      setBusy(null);
    }
  };

  const downloadResults = () => {
    if (!analysis) return;
    const blob = new Blob([JSON.stringify(analysis, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `seismonet-results-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderColumnSelect = (label: string, key: keyof CsvMapping, required = false) => (
    <label className="block text-sm text-slate-300">
      <span className="mb-2 block font-medium">{label}{required && <span className="text-amber-400"> *</span>}</span>
      <select value={String(mapping[key] ?? '')} onChange={(event) => updateMapping(key, event.target.value || '')} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500">
        <option value="">Not mapped</option>
        {mappedColumns.map((column) => <option key={column} value={column}>{column}</option>)}
      </select>
    </label>
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6 pb-10">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">User data pipeline</p>
        <h1 className="mt-2 text-3xl font-bold text-white">CSV Waveform Upload</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Upload one supported 3,072-sample waveform window, map its columns, validate it on the backend, and run the frozen Python phase-picking path.</p>
      </header>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4" aria-label="CSV workflow steps">
        {steps.map((item, index) => {
          const active = step === item;
          const complete = steps.indexOf(step) > index;
          return <div key={item} className={`rounded-xl border px-3 py-3 text-center text-xs font-semibold uppercase tracking-wider ${active ? 'border-amber-400 bg-amber-400/10 text-amber-300' : complete ? 'border-green-500/70 bg-green-500/10 text-green-300' : 'border-slate-700 bg-slate-900/50 text-slate-500'}`}><span className="mr-2">{complete ? '✓' : index + 1}</span>{item}</div>;
        })}
      </div>

      {error && <div className="flex items-start gap-3 rounded-xl border border-red-800 bg-red-950/20 p-4 text-sm text-red-100"><AlertCircle size={18} className="mt-0.5 shrink-0 text-red-400" /><div className="flex-1">{error}</div><button type="button" onClick={() => setError(null)} className="text-xs text-red-200 underline">Dismiss</button></div>}
      {analysisError && <div className="flex items-start gap-3 rounded-xl border border-red-800 bg-red-950/20 p-4 text-sm text-red-100"><AlertCircle size={18} className="mt-0.5 shrink-0 text-red-400" /><div className="flex-1">{analysisError}</div><button type="button" onClick={() => void runAnalysis()} disabled={busy !== null} className="text-xs font-semibold text-red-100 underline disabled:opacity-50">Retry</button></div>}

      {step === 'upload' && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 sm:p-8">
          <div onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); void handleFile(event.dataTransfer.files[0]); }} onClick={() => inputRef.current?.click()} className="cursor-pointer rounded-2xl border-2 border-dashed border-slate-700 p-10 text-center transition hover:border-cyan-500 hover:bg-slate-800/30">
            <Upload className="mx-auto text-cyan-400" size={44} />
            <h2 className="mt-4 text-lg font-semibold text-white">Drop a CSV here or browse</h2>
            <p className="mt-2 text-sm text-slate-400">UTF-8 CSV · maximum 50 MB · maximum 100,000 rows</p>
            <button type="button" onClick={(event) => { event.stopPropagation(); inputRef.current?.click(); }} className="mt-5 rounded-lg bg-cyan-600 px-5 py-2 text-sm font-semibold text-white hover:bg-cyan-500">Choose file</button>
            <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => void handleFile(event.target.files?.[0])} />
          </div>
          <div className="mt-6 grid gap-4 text-xs text-slate-300 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><p className="mb-2 font-semibold text-slate-200">Prediction schema</p><code className="leading-6 text-cyan-200">sample_index,E,N,Z<br />0,0.124,-0.032,0.078</code></div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"><p className="mb-2 font-semibold text-slate-200">Comparison schema</p><code className="leading-6 text-cyan-200">sample_index,E,N,Z,p_arrival_sample,s_arrival_sample<br />0,0.124,-0.032,0.078,1200,2450</code></div>
          </div>
        </section>
      )}

      {step === 'mapping' && (
        <section className="space-y-5 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold text-white">Confirm file and column mapping</h2><p className="mt-1 text-sm text-slate-400"><FileText className="mr-1 inline" size={14} />{file?.name} · {validation?.row_count?.toLocaleString() || '—'} rows</p></div><button type="button" onClick={reset} className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-xs text-slate-300 hover:bg-slate-700"><RotateCcw size={14} /> Start over</button></div>
          <div className="grid gap-4 md:grid-cols-3">{renderColumnSelect('East (E)', 'e_col', true)}{renderColumnSelect('North (N)', 'n_col', true)}{renderColumnSelect('Vertical (Z)', 'z_col', true)}</div>
          <div className="grid gap-4 md:grid-cols-3">{renderColumnSelect('Trace ID (for grouped files)', 'trace_id_col')}{renderColumnSelect('Sample/time coordinate', 'timestamp_col')}<label className="block text-sm text-slate-300"><span className="mb-2 block font-medium">Sampling rate (Hz)</span><input type="number" min="0.001" step="any" value={Number.isFinite(mapping.sampling_rate_hz) ? mapping.sampling_rate_hz : ''} onChange={(event) => updateMapping('sampling_rate_hz', Number(event.target.value))} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500" /></label></div>
          <div className="grid gap-4 md:grid-cols-3">{renderColumnSelect('P reference arrival', 'p_arrival_col')}{renderColumnSelect('S reference arrival', 's_arrival_col')}<label className="block text-sm text-slate-300"><span className="mb-2 block font-medium">Reference coordinate type</span><select value={mapping.arrival_coordinate_type} onChange={(event) => updateMapping('arrival_coordinate_type', event.target.value as CsvMapping['arrival_coordinate_type'])} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"><option value="sample_index">Sample index</option><option value="time_seconds">Time in seconds</option></select></label></div>

          {validation?.preview && <div><h3 className="mb-2 text-sm font-semibold text-slate-200">Preview</h3><div className="overflow-x-auto rounded-xl border border-slate-800"><table className="min-w-full text-left text-xs"><thead className="bg-slate-800/70 text-slate-300"><tr>{mappedColumns.map((column) => <th key={column} className="whitespace-nowrap px-3 py-2">{column}</th>)}</tr></thead><tbody>{validation.preview.slice(0, 5).map((row, index) => <tr key={index} className="border-t border-slate-800 text-slate-400">{mappedColumns.map((column) => <td key={column} className="whitespace-nowrap px-3 py-2">{String(row[column] ?? '')}</td>)}</tr>)}</tbody></table></div></div>}

          <div className="flex flex-wrap gap-3 border-t border-slate-800 pt-5"><button type="button" onClick={() => void validateMapping()} disabled={busy !== null} className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-5 py-2 text-sm font-semibold text-white hover:bg-cyan-500 disabled:opacity-50">{busy === 'validating' && <Loader size={15} className="animate-spin" />} Validate CSV</button><button type="button" onClick={reset} className="rounded-lg bg-slate-800 px-5 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700">Cancel</button></div>
        </section>
      )}

      {step === 'validation' && validation && (
        <section className="space-y-5 rounded-2xl border border-green-800/60 bg-green-950/10 p-6">
          <div className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 text-green-400" /><div><h2 className="text-xl font-semibold text-white">CSV is ready for inference</h2><p className="mt-1 text-sm text-slate-300">{validation.row_count.toLocaleString()} rows · {validation.trace_count || 1} trace · effective rate {validation.effective_sampling_rate_hz} Hz</p>{validation.resampling_required && <p className="mt-2 text-xs text-amber-300">The backend will resample this input to the frozen 100 Hz model rate and convert reference coordinates.</p>}</div></div>
          <div className="grid gap-4 sm:grid-cols-2"><label className={`cursor-pointer rounded-xl border p-4 ${mode === 'predict' ? 'border-cyan-500 bg-cyan-950/20' : 'border-slate-700 bg-slate-900/30'}`}><input type="radio" className="mr-2" checked={mode === 'predict'} onChange={() => setMode('predict')} />Prediction mode<p className="mt-2 text-xs text-slate-400">Show actual model picks and P/S probability curves. No metrics without reference labels.</p></label><label className={`rounded-xl border p-4 ${validation.has_reference_labels ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'} ${mode === 'compare' ? 'border-fuchsia-500 bg-fuchsia-950/20' : 'border-slate-700 bg-slate-900/30'}`}><input type="radio" className="mr-2" checked={mode === 'compare'} disabled={!validation.has_reference_labels} onChange={() => setMode('compare')} />Comparison mode<p className="mt-2 text-xs text-slate-400">{validation.has_reference_labels ? 'Compare predicted and supplied reference arrivals.' : 'Add P or S reference columns to enable comparison.'}</p></label></div>
          <div className="flex flex-wrap gap-3"><button type="button" onClick={() => void runAnalysis()} disabled={busy !== null} className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-5 py-2 text-sm font-semibold text-white hover:bg-green-500 disabled:opacity-50">{busy === 'analyzing' && <Loader size={15} className="animate-spin" />} Run real model analysis</button><button type="button" onClick={() => setStep('mapping')} disabled={busy !== null} className="rounded-lg bg-slate-800 px-5 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700">Edit mapping</button></div>
        </section>
      )}

      {step === 'results' && analysis && selectedPrediction && (
        <section className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-6"><div><p className="text-xs font-semibold uppercase tracking-wider text-green-400">Inference complete</p><h2 className="mt-1 text-2xl font-bold text-white">{analysis.mode === 'compare' ? 'Comparison results' : 'Prediction results'}</h2><p className="mt-1 text-sm text-slate-400">{analysis.trace_count} trace(s) · protocol {analysis.protocol.protocol_id} · P {analysis.protocol.p_threshold} / S {analysis.protocol.s_threshold}</p></div><div className="flex gap-2"><button type="button" onClick={downloadResults} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"><Download size={15} /> Export JSON</button><button type="button" onClick={reset} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-700">New file</button></div></div>
          {analysis.warnings.length > 0 && <div className="rounded-xl border border-amber-800 bg-amber-950/20 p-4 text-sm text-amber-100"><strong>Warnings:</strong> {analysis.warnings.join('; ')}</div>}
          {analysis.predictions.length > 1 && <label className="block max-w-sm text-sm text-slate-300">Trace result<select value={selectedIndex} onChange={(event) => setSelectedIndex(Number(event.target.value))} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">{analysis.predictions.map((prediction, index) => <option key={prediction.index} value={index}>{prediction.trace_id || `Trace ${index + 1}`}</option>)}</select></label>}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5"><CSVResultPlot prediction={selectedPrediction} comparison={selectedComparison} /></div>

          <div className="grid gap-4 md:grid-cols-2"><div className="rounded-xl border border-amber-800/50 bg-amber-950/10 p-5"><p className="text-xs uppercase tracking-wider text-amber-400">P-wave pick</p><p className="mt-2 text-2xl font-bold text-white">{selectedPrediction.p_predicted_sample ?? 'No pick'}</p><p className="mt-1 text-xs text-slate-400">{selectedPrediction.p_predicted_ms != null ? `${selectedPrediction.p_predicted_ms.toFixed(1)} ms · probability ${(selectedPrediction.p_probability ?? 0).toFixed(3)}` : 'No interior peak reached the frozen threshold.'}</p></div><div className="rounded-xl border border-fuchsia-800/50 bg-fuchsia-950/10 p-5"><p className="text-xs uppercase tracking-wider text-fuchsia-400">S-wave pick</p><p className="mt-2 text-2xl font-bold text-white">{selectedPrediction.s_predicted_sample ?? 'No pick'}</p><p className="mt-1 text-xs text-slate-400">{selectedPrediction.s_predicted_ms != null ? `${selectedPrediction.s_predicted_ms.toFixed(1)} ms · probability ${(selectedPrediction.s_probability ?? 0).toFixed(3)}` : 'No interior peak reached the frozen threshold.'}</p></div></div>

          {analysis.mode === 'compare' && selectedComparison && <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5"><h3 className="text-lg font-semibold text-white">Reference comparison</h3><div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="rounded-lg bg-slate-950/40 p-3 text-sm text-slate-300">P residual: <strong className={selectedComparison.p_within_tolerance ? 'text-green-400' : 'text-red-400'}>{selectedComparison.p_residual_ms == null ? 'N/A' : `${selectedComparison.p_residual_ms > 0 ? '+' : ''}${selectedComparison.p_residual_ms.toFixed(1)} ms`}</strong></div><div className="rounded-lg bg-slate-950/40 p-3 text-sm text-slate-300">S residual: <strong className={selectedComparison.s_within_tolerance ? 'text-green-400' : 'text-red-400'}>{selectedComparison.s_residual_ms == null ? 'N/A' : `${selectedComparison.s_residual_ms > 0 ? '+' : ''}${selectedComparison.s_residual_ms.toFixed(1)} ms`}</strong></div></div></div>}

          {analysis.mode === 'compare' && analysis.metrics && <div className="grid gap-4 md:grid-cols-2">{(['p_metrics', 's_metrics'] as const).map((key) => { const metric = analysis.metrics?.[key]; if (!metric) return null; return <div key={key} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5"><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{key === 'p_metrics' ? 'P-wave' : 'S-wave'} upload metrics</p><div className="mt-3 grid grid-cols-3 gap-3 text-center"><div><p className="text-xs text-slate-500">Precision</p><p className="mt-1 font-mono text-white">{metric.precision.toFixed(3)}</p></div><div><p className="text-xs text-slate-500">Recall</p><p className="mt-1 font-mono text-white">{metric.recall.toFixed(3)}</p></div><div><p className="text-xs text-slate-500">F1</p><p className="mt-1 font-mono text-white">{metric.f1.toFixed(3)}</p></div></div><p className="mt-3 text-xs text-slate-500">TP / FP / FN: {metric.tp} / {metric.fp} / {metric.fn}. These metrics apply only to this uploaded labeled file.</p></div>; })}</div>}
        </section>
      )}
    </div>
  );
};

export default CSVUpload;
