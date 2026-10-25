import axios, { AxiosError } from 'axios';
import {
  AnalysisResult,
  CsvAnalysisResult,
  CsvMapping,
  CsvValidationResult,
  ModelMetrics,
  Trace,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120_000,
  headers: { Accept: 'application/json' },
});

function makeCsvForm(file: File, mapping?: CsvMapping | null, mode?: 'predict' | 'compare'): FormData {
  const form = new FormData();
  form.append('file', file, file.name);
  if (mapping) form.append('mapping', JSON.stringify(mapping));
  if (mode) form.append('mode', mode);
  return form;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (detail && typeof detail === 'object' && typeof detail.message === 'string') return detail.message;
    if (typeof error.message === 'string' && error.message.trim()) return error.message;
  }
  return fallback;
}

export const seismoService = {
  async getTraces(): Promise<Trace[]> {
    const response = await api.get<Trace[]>('/traces');
    return response.data;
  },

  async analyzeTrace(traceId: string): Promise<AnalysisResult> {
    const response = await api.get<AnalysisResult>(`/analyze/${encodeURIComponent(traceId)}`);
    return response.data;
  },

  async getMetrics(): Promise<ModelMetrics> {
    const response = await api.get<ModelMetrics>('/metrics');
    return response.data;
  },

  async checkHealth(): Promise<Record<string, unknown>> {
    const response = await api.get<Record<string, unknown>>('/health');
    return response.data;
  },

  async validateCSV(file: File, mapping?: CsvMapping | null): Promise<CsvValidationResult> {
    const response = await api.post<CsvValidationResult>('/csv/validate', makeCsvForm(file, mapping));
    return response.data;
  },

  async analyzeCSV(
    file: File,
    mapping: CsvMapping,
    mode: 'predict' | 'compare',
  ): Promise<CsvAnalysisResult> {
    const response = await api.post<CsvAnalysisResult>('/csv/analyze', makeCsvForm(file, mapping, mode));
    return response.data;
  },
};
