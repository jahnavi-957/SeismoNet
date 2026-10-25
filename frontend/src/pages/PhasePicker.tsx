import React, { useCallback, useEffect, useState } from 'react';
import { Activity, AlertCircle, CheckCircle2, Play, RefreshCw, Search } from 'lucide-react';
import { getApiErrorMessage, seismoService } from '../services/api';
import { AnalysisResult, Trace } from '../types';
import WaveformPlot from '../components/WaveformPlot';
import PipelineSimulation, { PipelineStage } from '../components/PipelineSimulation';

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const modelStages: PipelineStage[] = [
  { label: 'Loading the trace window', detail: 'One 3,072-sample window at 100 Hz (30.72 s of ground motion).' },
  { label: 'Splitting into E, N, Z', detail: 'East, North and Vertical components are separated.' },
  { label: 'Reading the reference arrivals', detail: 'The recorded P and S times for this trace, used for comparison.' },
  { label: 'Running the frozen 1D U-Net', detail: '678,707 parameters produce three probability curves per sample.' },
  { label: 'Thresholding into picks', detail: 'Strongest local peak per phase above the frozen thresholds, 20 samples apart.' },
  { label: 'Drawing the charts', detail: 'Waveform panels and P/S probability curves with pick markers.' },
];

const demoStages: PipelineStage[] = [
  { label: 'Loading the trace window', detail: 'One 3,072-sample window at 100 Hz (30.72 s of ground motion).' },
  { label: 'Splitting into E, N, Z', detail: 'East, North and Vertical components are separated.' },
  { label: 'Reading the reference arrivals', detail: 'The recorded P and S times for this trace, used for comparison.' },
  { label: 'Building demonstration curves', detail: 'No raw dataset in this checkout, so the curves are constructed at the reference times instead of being inferred.' },
  { label: 'Thresholding into picks', detail: 'Strongest local peak per phase above the frozen thresholds, 20 samples apart.' },
  { label: 'Drawing the charts', detail: 'Waveform panels and P/S probability curves with pick markers.' },
];

const PhasePicker: React.FC = () => {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loadingTraces, setLoadingTraces] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTraces = useCallback(async () => {
    setLoadingTraces(true);
    setError(null);
    try {
      const data = await seismoService.getTraces();
      setTraces(Array.isArray(data) ? data : []);
      setSelectedTrace((current) => current || data[0]?.trace_id || '');
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Failed to load permitted trace metadata.'));
      setTraces([]);
    } finally {
      setLoadingTraces(false);
    }
  }, []);

  useEffect(() => { void loadTraces(); }, [loadTraces]);

  const runAnalysis = async () => {
    if (!selectedTrace) {
      setError('Select a trace before running analysis.');
      return;
    }
    setLoadingAnalysis(true);
    setError(null);
    try {
      const [analysisResult] = await Promise.all([
        seismoService.analyzeTrace(selectedTrace),
        sleep(1900),
      ]);
      setResult(analysisResult);
    } catch (requestError) {
      setResult(null);
      setError(getApiErrorMessage(requestError, 'Inference failed. Check that the backend model service is available.'));
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const selected = traces.find((trace) => trace.trace_id === selectedTrace);
  const pickLabel = (value: number | null) => value == null ? 'No pick' : value.toLocaleString();
  const isDemoFallback = (result?.data_source ?? traces[0]?.data_source) === 'synthetic_demo_fallback';

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 p-6 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-xl">
        <div>
          <h2 className="text-2xl font-bold text-white">Phase Picker</h2>
          <p className="mt-1 text-sm text-slate-400">Analyze one permitted waveform trace with the frozen Python inference path.</p>
        </div>
        <div className="flex gap-3">
          <button type="button" onClick={() => { setResult(null); setError(null); }} className="inline-flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-xs font-medium text-slate-300 transition hover:bg-slate-700">
            <RefreshCw size={14} /> Reset view
          </button>
          <button type="button" onClick={() => void runAnalysis()} disabled={loadingAnalysis || loadingTraces || !selectedTrace} className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-6 py-2 text-xs font-bold text-white shadow-lg shadow-cyan-900/20 transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50">
            {loadingAnalysis ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {loadingAnalysis ? 'Analyzing…' : 'Run analysis'}
          </button>
        </div>
      </div>

      {isDemoFallback && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-800/60 bg-amber-950/20 p-4 text-sm text-amber-100">
          <AlertCircle size={18} className="mt-0.5 shrink-0 text-amber-400" />
          <div>
            <p className="font-semibold text-amber-300">Demo mode — the model is not running on this page</p>
            <p className="mt-1 leading-6 text-amber-100/90">
              The raw waveform dataset is not present in this checkout, so these picks and probability
              curves are constructed at the reference arrivals — which is why the residual reads 0
              samples. This is an interface demonstration, not model output. Use <strong>CSV Upload</strong> to
              run the real frozen checkpoint.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <Search size={18} className="text-cyan-400" />
          <div className="min-w-0 flex-1">
            <label htmlFor="trace-select" className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Select trace</label>
            <select id="trace-select" value={selectedTrace} onChange={(event) => { setSelectedTrace(event.target.value); setResult(null); }} disabled={loadingTraces || traces.length === 0} className="mt-1 w-full rounded-md bg-slate-900 px-2 py-1 text-sm text-white outline-none disabled:text-slate-600">
              {traces.length === 0 && <option value="">{loadingTraces ? 'Loading traces…' : 'No traces available'}</option>}
              {traces.map((trace) => <option key={trace.trace_id} value={trace.trace_id}>{trace.trace_id}</option>)}
            </select>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <Activity size={18} className="text-cyan-400" />
          <div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Event ID</p><p className="font-mono text-sm text-white">{selected?.event_id || '—'}</p></div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <CheckCircle2 size={18} className="text-cyan-400" />
          <div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Protocol</p><p className="text-sm font-medium text-green-400">P 0.05 · S 0.10 · tol 20</p></div>
        </div>
      </div>

      {error && <div className="flex items-start gap-3 rounded-xl border border-red-800 bg-red-950/20 p-4 text-sm text-red-200"><AlertCircle size={18} className="mt-0.5 shrink-0 text-red-400" /><div className="flex-1">{error}</div>{!traces.length && <button type="button" onClick={() => void loadTraces()} className="text-xs font-semibold text-red-100 underline">Retry</button>}</div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-inner lg:col-span-3">
          {loadingAnalysis ? (
            <PipelineSimulation
              stages={isDemoFallback ? demoStages : modelStages}
              title="Analysing this trace…"
              subtitle={selectedTrace}
            />
          ) : result ? <WaveformPlot data={result} /> : <div className="flex min-h-[540px] flex-col items-center justify-center gap-4 text-center text-slate-500"><div className="rounded-full bg-slate-800/50 p-4 text-slate-600"><Activity size={48} /></div><p className="text-sm italic">{traces.length ? 'Select a trace and run analysis to visualize predictions.' : 'No permitted trace metadata is available.'}</p></div>}
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl">
            <h3 className="mb-4 flex items-center gap-2 font-bold text-white"><Activity size={18} className="text-cyan-400" /> Results</h3>
            {result ? (
              <div className="space-y-5">
                {(['p', 's'] as const).map((phase) => {
                  const pick = result.picks[phase];
                  const color = phase === 'p' ? 'text-amber-400' : 'text-fuchsia-400';
                  const hasPrediction = pick.predicted != null;
                  const hasReference = pick.reference != null;
                  const residual = hasPrediction && hasReference ? pick.predicted! - pick.reference! : null;
                  return (
                    <div key={phase} className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
                      <div className="mb-3 flex items-center justify-between"><span className={`text-xs font-bold uppercase ${color}`}>{phase}-wave</span><span className={`rounded-full px-2 py-0.5 text-[10px] ${hasPrediction ? 'bg-green-900/30 text-green-400' : 'bg-slate-700 text-slate-400'}`}>{hasPrediction ? 'Detected' : 'No pick'}</span></div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400"><div>Reference<br /><span className="font-mono text-white">{pickLabel(pick.reference)}</span></div><div>Predicted<br /><span className="font-mono text-white">{pickLabel(pick.predicted)}</span></div></div>
                      {residual != null && <div className={`mt-3 border-t border-slate-700 pt-3 text-xs font-bold ${Math.abs(residual) <= 20 ? 'text-green-400' : 'text-red-400'}`}>Residual: {residual > 0 ? '+' : ''}{residual} samples</div>}
                    </div>
                  );
                })}
                <div className="border-t border-slate-800 pt-4 text-xs leading-5 text-slate-500">
                  <p>Source: <span className="text-slate-300">{result.data_source || 'unknown'}</span></p>
                  <p>Mode: <span className="text-slate-300">{result.inference_mode || 'model'}</span></p>
                  <p>Rate: <span className="text-slate-300">{result.sampling_rate} Hz</span></p>
                </div>
              </div>
            ) : <p className="py-12 text-center text-xs italic text-slate-500">Run analysis to see detailed picks.</p>}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default PhasePicker;
