import React from 'react';
import { Activity, ArrowRight, CheckCircle2, Cpu, Database, ShieldCheck, Upload, Zap } from 'lucide-react';
import { getApiErrorMessage, seismoService } from '../services/api';
import { ModelMetrics } from '../types';
import type { PageId } from '../App';

interface OverviewProps {
  onNavigate: (page: PageId) => void;
}

const Overview: React.FC<OverviewProps> = ({ onNavigate }) => {
  const [metrics, setMetrics] = React.useState<ModelMetrics | null>(null);
  const [metricsError, setMetricsError] = React.useState<string | null>(null);

  React.useEffect(() => {
    seismoService.getMetrics().then(setMetrics).catch((error) => {
      setMetricsError(getApiErrorMessage(error, 'Evaluation metrics are unavailable.'));
    });
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 pb-10">
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl sm:p-12">
        <div className="relative z-10 max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-400">Seismic phase analysis</p>
          <h2 className="mt-4 text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
            SeismoNet <span className="text-cyan-400">phase picker</span>
          </h2>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
            A frozen 1D U-Net analyzes three-component waveform windows and estimates where recorded
            P- and S-wave arrivals occur. The result is a transparent probability curve and a
            protocol-defined pick, not an earthquake prediction.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button type="button" onClick={() => onNavigate('picker')} className="inline-flex items-center gap-2 rounded-full bg-cyan-600 px-6 py-3 font-bold text-white shadow-lg shadow-cyan-900/30 transition hover:bg-cyan-500">
              Open Phase Picker <ArrowRight size={16} />
            </button>
            <button type="button" onClick={() => onNavigate('csv-upload')} className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-6 py-3 font-bold text-white transition hover:bg-slate-700">
              <Upload size={16} /> Analyze a CSV
            </button>
            <button type="button" onClick={() => onNavigate('evaluation')} className="rounded-full border border-slate-700 px-6 py-3 font-semibold text-slate-300 transition hover:border-cyan-700 hover:text-white">
              View evaluation
            </button>
          </div>
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 opacity-20">
          <svg viewBox="0 0 1000 100" preserveAspectRatio="none" className="h-full w-full">
            <path d="M0 50 Q 50 10 100 50 T 200 50 T 300 20 T 400 80 T 500 50 T 600 10 T 700 50 T 800 50 T 900 40 T 1000 50" stroke="#00FFFF" strokeWidth="2" fill="transparent" />
          </svg>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {[
          { icon: <Cpu size={20} />, title: '1D U-Net', body: 'Base width 16, depth 4, 678,707 trainable parameters.' },
          { icon: <Database size={20} />, title: 'ENZ input', body: 'Three-component waveform windows at an effective 100 Hz rate.' },
          { icon: <ShieldCheck size={20} />, title: 'Frozen protocol', body: 'P 0.05, S 0.10, and 20 samples (200 ms) matching tolerance.' },
        ].map((card) => (
          <div key={card.title} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-900/30 text-cyan-400">{card.icon}</div>
            <h3 className="font-bold text-white">{card.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">{card.body}</p>
          </div>
        ))}
      </div>

      <section className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h3 className="text-2xl font-bold text-white">Verified evaluation snapshot</h3>
            <p className="mt-2 text-sm text-slate-400">{metrics?.evaluation_split ? `${metrics.evaluation_split} split · F1 is not accuracy` : 'Loading the saved evaluation artifact…'}</p>
          </div>
          {metrics && <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400">{metrics.n_traces?.toLocaleString()} traces</span>}
        </div>
        {metricsError && <p className="mt-5 rounded-xl border border-red-800 bg-red-950/20 p-4 text-sm text-red-200">{metricsError}</p>}
        {metrics && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-amber-800/50 bg-amber-950/10 p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">P-wave F1</p>
              <p className="mt-2 text-3xl font-bold text-white">{metrics.p_wave.f1.toFixed(3)}</p>
              <p className="mt-2 text-xs text-slate-400">Precision {metrics.p_wave.precision.toFixed(3)} · Recall {metrics.p_wave.recall.toFixed(3)}</p>
            </div>
            <div className="rounded-xl border border-fuchsia-800/50 bg-fuchsia-950/10 p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-fuchsia-400">S-wave F1</p>
              <p className="mt-2 text-3xl font-bold text-white">{metrics.s_wave.f1.toFixed(3)}</p>
              <p className="mt-2 text-xs text-slate-400">Precision {metrics.s_wave.precision.toFixed(3)} · Recall {metrics.s_wave.recall.toFixed(3)}</p>
            </div>
          </div>
        )}
        <p className="mt-5 text-xs leading-5 text-slate-500">The evaluation page identifies the split, checkpoint protocol, and selection caveat before displaying detailed numbers.</p>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 sm:p-8">
        <h3 className="text-2xl font-bold text-white">How the system works</h3>
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-5">
          {[
            { icon: <Database size={20} />, title: 'Waveform', desc: 'ENZ samples' },
            { icon: <Activity size={20} />, title: 'Preprocess', desc: 'Demean + normalize' },
            { icon: <Cpu size={20} />, title: 'U-Net', desc: 'Per-sample logits' },
            { icon: <Zap size={20} />, title: 'Probabilities', desc: 'P / S / noise' },
            { icon: <CheckCircle2 size={20} />, title: 'Picks', desc: 'Protocol-defined arrivals' },
          ].map((step) => (
            <div key={step.title} className="rounded-xl border border-slate-700 bg-slate-800/30 p-4 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-cyan-900/40 text-cyan-400">{step.icon}</div>
              <h4 className="text-xs font-bold text-white">{step.title}</h4>
              <p className="mt-1 text-[11px] text-slate-500">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Overview;
