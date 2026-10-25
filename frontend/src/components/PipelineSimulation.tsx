import React, { useEffect, useState } from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

export interface PipelineStage {
  label: string;
  detail: string;
}

interface Props {
  stages: PipelineStage[];
  title?: string;
  subtitle?: string;
}

/**
 * Visible walk-through of the processing pipeline. Stages advance on a timer while the
 * real request is in flight, so the user sees the order of operations rather than a
 * blank spinner. Nothing here changes the computation — it only narrates it.
 */
const PipelineSimulation: React.FC<Props> = ({ stages, title = 'Processing…', subtitle }) => {
  const [index, setIndex] = useState(0);
  const finished = index >= stages.length;

  useEffect(() => {
    if (finished) return;
    const timer = window.setTimeout(() => setIndex((current) => current + 1), 340);
    return () => window.clearTimeout(timer);
  }, [index, finished]);

  const percent = Math.round((Math.min(index, stages.length) / stages.length) * 100);

  return (
    <section className="rounded-2xl border border-cyan-800/60 bg-cyan-950/10 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">{finished ? 'Step complete' : title}</h2>
          {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
        </div>
        <span className="rounded-full border border-cyan-700/60 px-3 py-1 font-mono text-xs text-cyan-300">
          {percent}%
        </span>
      </div>

      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-cyan-500 transition-all duration-300 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>

      <ol className="mt-5 space-y-3">
        {stages.map((stage, position) => {
          const complete = position < index;
          const active = position === index;
          return (
            <li
              key={stage.label}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 transition-colors ${
                active
                  ? 'border-cyan-700 bg-cyan-950/30'
                  : complete
                    ? 'border-slate-800 bg-slate-900/40'
                    : 'border-slate-800/60 bg-slate-900/20'
              }`}
            >
              <span className="mt-0.5 shrink-0">
                {complete ? (
                  <CheckCircle2 size={18} className="text-green-400" />
                ) : active ? (
                  <Loader2 size={18} className="animate-spin text-cyan-400" />
                ) : (
                  <Circle size={18} className="text-slate-600" />
                )}
              </span>
              <div className="min-w-0">
                <p className={`text-sm font-semibold ${complete ? 'text-slate-300' : active ? 'text-white' : 'text-slate-500'}`}>
                  {position + 1}. {stage.label}
                </p>
                {(active || complete) && <p className="mt-1 text-xs leading-5 text-slate-400">{stage.detail}</p>}
              </div>
            </li>
          );
        })}
      </ol>

      {!finished && (
        <p className="mt-4 text-xs text-slate-500">
          Inference runs on CPU, so this takes a few seconds. The steps above follow the real order of
          operations in the backend.
        </p>
      )}
    </section>
  );
};

export default PipelineSimulation;
