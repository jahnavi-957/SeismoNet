export interface Trace {
  trace_id: string;
  event_id: string;
  p_ref: string;
  s_ref: string;
  data_source?: string;
}

export interface AnalysisResult {
  trace_id: string;
  event_id: string;
  waveform: number[][];
  probs: {
    p: number[];
    s: number[];
    noise: number[];
  };
  picks: {
    p: {
      predicted: number | null;
      reference: number | null;
      probability: number | null;
    };
    s: {
      predicted: number | null;
      reference: number | null;
      probability: number | null;
    };
  };
  window_start: number;
  window_length: number;
  sampling_rate: number;
  data_source?: string;
  inference_mode?: string;
}

export interface ModelMetrics {
  evaluation_split?: string;
  n_traces?: number;
  n_events?: number;
  matching_tolerance_samples?: number;
  sampling_rate_hz?: number;
  p_wave: {
    f1: number;
    precision: number;
    recall: number;
    tp: number;
    fp: number;
    fn: number;
  };
  s_wave: {
    f1: number;
    precision: number;
    recall: number;
    tp: number;
    fp: number;
    fn: number;
  };
  protocol_id?: string;
  p_threshold?: number;
  s_threshold?: number;
  note: string;
}

export interface CsvMapping {
  e_col?: string;
  n_col?: string;
  z_col?: string;
  trace_id_col?: string;
  timestamp_col?: string;
  p_arrival_col?: string;
  s_arrival_col?: string;
  sampling_rate_hz: number;
  arrival_coordinate_type: 'sample_index' | 'time_seconds';
}

export interface CsvValidationResult {
  is_valid: boolean;
  error?: string | null;
  errors?: string[];
  row_count: number;
  trace_count?: number;
  has_reference_labels: boolean;
  columns?: string[];
  detected_columns: Record<string, string | null | undefined>;
  mapping?: CsvMapping;
  preview?: Array<Record<string, string | number>>;
  effective_sampling_rate_hz?: number;
  resampling_required?: boolean;
}

export interface CsvPrediction {
  index: number;
  trace_id?: string;
  waveform: number[][];
  probs: { p: number[]; s: number[]; noise: number[] };
  p_predicted_sample: number | null;
  s_predicted_sample: number | null;
  p_predicted_ms: number | null;
  s_predicted_ms: number | null;
  p_probability: number | null;
  s_probability: number | null;
  p_probability_curve: number[];
  s_probability_curve: number[];
  noise_probability_curve?: number[];
  sampling_rate_hz: number;
  protocol: {
    protocol_id: string;
    p_threshold: number;
    s_threshold: number;
    matching_tolerance_samples: number;
  };
}

export interface CsvComparison {
  index: number;
  trace_id?: string;
  p_predicted_sample: number | null;
  p_reference_sample: number | null;
  p_residual_samples: number | null;
  p_residual_ms: number | null;
  p_within_tolerance: boolean | null;
  s_predicted_sample: number | null;
  s_reference_sample: number | null;
  s_residual_samples: number | null;
  s_residual_ms: number | null;
  s_within_tolerance: boolean | null;
}

export interface CsvAnalysisResult {
  mode: 'predict' | 'compare';
  predictions: CsvPrediction[];
  comparisons?: CsvComparison[];
  metrics?: {
    p_metrics?: { tp: number; fp: number; fn: number; precision: number; recall: number; f1: number };
    s_metrics?: { tp: number; fp: number; fn: number; precision: number; recall: number; f1: number };
  };
  warnings: string[];
  trace_count: number;
  input_sampling_rate_hz: number;
  effective_sampling_rate_hz: number;
  protocol: {
    protocol_id: string;
    p_threshold: number;
    s_threshold: number;
    matching_tolerance_samples: number;
    sampling_rate_hz: number;
  };
}
