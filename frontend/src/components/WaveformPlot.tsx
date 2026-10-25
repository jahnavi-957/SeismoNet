import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { AnalysisResult } from '../types';

interface WaveformPlotProps {
  data: AnalysisResult;
}

const WaveformPlot: React.FC<WaveformPlotProps> = ({ data }) => {
  const { waveform, probs, picks, window_start } = data;

  // Generate data for Recharts
  //- Waveforms: 3 lines
  //- Probabilities: 2 lines
  const timeSeries: Array<{
    time: number;
    ch0: number;
    ch1: number;
    ch2: number;
    pProb: number;
    sProb: number;
  }> = [];
  const length = Math.min(
    data.window_length,
    waveform[0]?.length ?? 0,
    waveform[1]?.length ?? 0,
    waveform[2]?.length ?? 0,
    probs.p?.length ?? 0,
    probs.s?.length ?? 0,
  );
  for (let i = 0; i < length; i++) {
    timeSeries.push({
      time: window_start + i,
      ch0: waveform[0][i],
      ch1: waveform[1][i],
      ch2: waveform[2][i],
      pProb: probs.p[i],
      sProb: probs.s[i],
    });
  }

  const renderChart = (dataKey: string, label: string, color: string) => (
    <div className="h-48 w-full mb-4 bg-slate-900/50 p-2 rounded-lg border border-slate-800">
      <p className="text-xs text-slate-400 mb-2 pl-2 font-mono">{label}</p>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={timeSeries}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis dataKey="time" hide />
          <YAxis hide domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
          <Line type="monotone" dataKey={dataKey} stroke={color} dot={false} strokeWidth={1} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="space-y-6">
      {length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-sm text-slate-400">No waveform samples were returned for this trace.</div>
      ) : <div className="grid grid-cols-1 gap-4">
        {renderChart('ch0', 'Component E (East)', '#00FFFF')}
        {renderChart('ch1', 'Component N (North)', '#00FFFF')}
        {renderChart('ch2', 'Component Z (Vertical)', '#00FFFF')}
      </div>}

      <div className="mt-8">
        <h4 className="text-sm font-semibold text-slate-300 mb-4 pl-2">Phase Probabilities</h4>
        <div className="h-64 w-full bg-slate-900/50 p-2 rounded-lg border border-slate-800">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={timeSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
              <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#fff' }}
              />
              <Legend verticalAlign="top" height={36}/>
              <Line name="P-Wave" type="monotone" dataKey="pProb" stroke="#f59e0b" dot={false} strokeWidth={2} isAnimationActive={false} />
              <Line name="S-Wave" type="monotone" dataKey="sProb" stroke="#d946ef" dot={false} strokeWidth={2} isAnimationActive={false} />
              {picks.p.predicted != null && <ReferenceLine x={picks.p.predicted} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'P pred', fill: '#f59e0b', fontSize: 10 }} />}
              {picks.s.predicted != null && <ReferenceLine x={picks.s.predicted} stroke="#d946ef" strokeDasharray="4 4" label={{ value: 'S pred', fill: '#d946ef', fontSize: 10 }} />}
              {picks.p.reference != null && <ReferenceLine x={picks.p.reference} stroke="#fbbf24" strokeDasharray="2 2" label={{ value: 'P ref', fill: '#fbbf24', fontSize: 10 }} />}
              {picks.s.reference != null && <ReferenceLine x={picks.s.reference} stroke="#e879f9" strokeDasharray="2 2" label={{ value: 'S ref', fill: '#e879f9', fontSize: 10 }} />}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default WaveformPlot;
