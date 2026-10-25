import React, { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CsvComparison, CsvPrediction } from '../types';

interface CSVResultPlotProps {
  prediction: CsvPrediction;
  comparison?: CsvComparison;
}

const CSVResultPlot: React.FC<CSVResultPlotProps> = ({ prediction, comparison }) => {
  const points = useMemo(() => {
    const count = Math.min(
      prediction.waveform[0]?.length ?? 0,
      prediction.waveform[1]?.length ?? 0,
      prediction.waveform[2]?.length ?? 0,
      prediction.p_probability_curve.length,
      prediction.s_probability_curve.length,
    );
    return Array.from({ length: count }, (_, sample) => ({
      sample,
      e: prediction.waveform[0][sample],
      n: prediction.waveform[1][sample],
      z: prediction.waveform[2][sample],
      p: prediction.p_probability_curve[sample],
      s: prediction.s_probability_curve[sample],
    }));
  }, [prediction]);

  const chart = (key: 'e' | 'n' | 'z', label: string, color: string) => (
    <div className="h-44 rounded-xl border border-slate-800 bg-slate-950/50 p-2">
      <p className="pl-2 text-xs font-mono text-slate-400">{label}</p>
      <ResponsiveContainer width="100%" height="92%">
        <LineChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="sample" hide />
          <YAxis hide domain={['auto', 'auto']} />
          <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#fff' }} />
          <Line dataKey={key} type="monotone" stroke={color} dot={false} strokeWidth={1.2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        {chart('e', 'Component E (normalized)', '#22d3ee')}
        {chart('n', 'Component N (normalized)', '#38bdf8')}
        {chart('z', 'Component Z (normalized)', '#67e8f9')}
      </div>
      <div className="h-64 rounded-xl border border-slate-800 bg-slate-950/50 p-2">
        <p className="pl-2 text-xs font-mono text-slate-400">P/S probability curves</p>
        <ResponsiveContainer width="100%" height="92%">
          <LineChart data={points} margin={{ top: 14, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="sample" stroke="#64748b" fontSize={10} />
            <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
            <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#fff' }} />
            <Legend verticalAlign="top" height={28} />
            <Line name="P wave" dataKey="p" type="monotone" stroke="#f59e0b" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line name="S wave" dataKey="s" type="monotone" stroke="#d946ef" dot={false} strokeWidth={2} isAnimationActive={false} />
            {prediction.p_predicted_sample != null && <ReferenceLine x={prediction.p_predicted_sample} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'P pred', fill: '#f59e0b', fontSize: 10 }} />}
            {prediction.s_predicted_sample != null && <ReferenceLine x={prediction.s_predicted_sample} stroke="#d946ef" strokeDasharray="4 4" label={{ value: 'S pred', fill: '#d946ef', fontSize: 10 }} />}
            {comparison?.p_reference_sample != null && <ReferenceLine x={comparison.p_reference_sample} stroke="#fbbf24" strokeDasharray="2 2" label={{ value: 'P ref', fill: '#fbbf24', fontSize: 10 }} />}
            {comparison?.s_reference_sample != null && <ReferenceLine x={comparison.s_reference_sample} stroke="#e879f9" strokeDasharray="2 2" label={{ value: 'S ref', fill: '#e879f9', fontSize: 10 }} />}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default CSVResultPlot;
