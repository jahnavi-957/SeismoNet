import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, RefreshCw } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getApiErrorMessage, seismoService } from '../services/api';
import { ModelMetrics } from '../types';

const ModelEvaluation: React.FC = () => {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setMetrics(await seismoService.getMetrics());
    } catch (requestError) {
      setMetrics(null);
      setError(getApiErrorMessage(requestError, 'The saved evaluation artifact is unavailable.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadMetrics(); }, [loadMetrics]);

  if (loading) return <div className="mx-auto max-w-5xl p-8 text-sm text-slate-400">Loading verified evaluation metrics…</div>;
  if (error || !metrics) return <div className="mx-auto max-w-5xl p-6"><div className="rounded-2xl border border-red-800 bg-red-950/20 p-6 text-red-100"><h2 className="text-lg font-semibold">Evaluation unavailable</h2><p className="mt-2 text-sm">{error || 'No metrics were returned.'}</p><button type="button" onClick={() => void loadMetrics()} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-800 px-4 py-2 text-sm font-semibold hover:bg-red-700"><RefreshCw size={15} /> Retry</button></div></div>;

  const pData = [
    { name: 'Precision', value: metrics.p_wave.precision },
    { name: 'Recall', value: metrics.p_wave.recall },
    { name: 'F1', value: metrics.p_wave.f1 },
  ];
  const sData = [
    { name: 'Precision', value: metrics.s_wave.precision },
    { name: 'Recall', value: metrics.s_wave.recall },
    { name: 'F1', value: metrics.s_wave.f1 },
  ];
  const card = (label: string, value: number, accent: string) => <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 text-center"><p className="text-xs uppercase text-slate-400">{label}</p><p className={`mt-1 text-2xl font-bold ${accent}`}>{value.toFixed(3)}</p></div>;
  const chart = (data: typeof pData, phase: 'P' | 'S') => <div className="h-64 w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} /><XAxis dataKey="name" stroke="#64748b" fontSize={12} /><YAxis domain={[0, 1]} stroke="#64748b" fontSize={12} tickFormatter={(value) => Number(value).toFixed(1)} /><Tooltip formatter={(value: number) => value.toFixed(3)} cursor={{ fill: 'transparent' }} contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#fff' }} /><Bar dataKey="value" radius={[4, 4, 0, 0]}>{data.map((_, index) => <Cell key={`${phase}-${index}`} fill={index === 2 ? (phase === 'P' ? '#f59e0b' : '#d946ef') : '#475569'} />)}</Bar></BarChart></ResponsiveContainer></div>;

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 pb-10">
      <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">Measured performance</p><h2 className="mt-2 text-3xl font-bold text-white">Model Evaluation</h2><p className="mt-2 text-sm text-slate-400">{metrics.evaluation_split} split · F1 is a phase-picking metric, not accuracy.</p></div><div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-right"><p className="text-[10px] font-bold uppercase text-slate-500">Frozen checkpoint</p><p className="font-mono text-sm text-white">Experiment 002 · epoch 11</p><p className="mt-1 text-[10px] text-slate-500">{metrics.n_traces?.toLocaleString() || '—'} traces · {metrics.n_events?.toLocaleString() || '—'} events</p></div></div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">{[
        { phase: 'P' as const, title: 'P-wave performance', data: metrics.p_wave, series: pData, color: 'text-amber-400' },
        { phase: 'S' as const, title: 'S-wave performance', data: metrics.s_wave, series: sData, color: 'text-fuchsia-400' },
      ].map((item) => <section key={item.phase} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-xl"><div className="mb-6 flex items-center gap-2"><span className={`h-3 w-3 rounded-full ${item.phase === 'P' ? 'bg-amber-500' : 'bg-fuchsia-500'}`} /><h3 className="text-xl font-bold text-white">{item.title}</h3></div><div className="mb-7 grid grid-cols-3 gap-3">{card('Precision', item.data.precision, 'text-white')}{card('Recall', item.data.recall, 'text-white')}{card('F1', item.data.f1, item.color)}</div>{chart(item.series, item.phase)}<div className="mt-4 border-t border-slate-800 pt-4 text-xs text-slate-500">TP / FP / FN: {item.data.tp} / {item.data.fp} / {item.data.fn}</div></section>)}
      </div>

      <section className="rounded-2xl border border-cyan-900/60 bg-cyan-950/10 p-6"><h3 className="flex items-center gap-2 font-semibold text-cyan-200"><BarChart3 size={18} /> Frozen evaluation protocol</h3><div className="mt-4 grid gap-3 text-sm text-slate-300 sm:grid-cols-2 lg:grid-cols-4"><div>Protocol<br /><strong className="font-mono text-white">{metrics.protocol_id || 'protocol-5fa5744aca58cc3c'}</strong></div><div>Thresholds<br /><strong className="text-white">P {metrics.p_threshold ?? 0.05} · S {metrics.s_threshold ?? 0.1}</strong></div><div>Tolerance<br /><strong className="text-white">{metrics.matching_tolerance_samples ?? 20} samples</strong></div><div>Sampling rate<br /><strong className="text-white">{metrics.sampling_rate_hz ?? 100} Hz</strong></div></div></section>

      <section className="flex gap-4 rounded-2xl border border-amber-800/60 bg-amber-950/20 p-6"><AlertTriangle className="shrink-0 text-amber-500" /><div><h4 className="font-bold text-amber-400">Scientific integrity notice</h4><p className="mt-2 text-sm leading-6 text-slate-300">{metrics.note}</p><p className="mt-2 text-xs leading-5 text-slate-500">The metrics shown here come from the saved project artifact. They are separate from metrics calculated on a user-uploaded labeled CSV.</p></div></section>
    </div>
  );
};

export default ModelEvaluation;
