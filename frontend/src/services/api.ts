import {
  HardwareMetrics,
  ThrottlePolicy,
  HardwareStatusResponse,
  ProvidersStatusResponse,
  ModelCapability,
  ProjectRecord,
  DocumentRecord,
  ChunkRecord,
  GlossaryItem,
  BenchmarkSample,
  BenchmarkRunItem,
  SystemDependenciesResponse,
  PyTorchVerifyResponse,
  GeminiQuotaResponse,
  ProviderScorecard,
  PolicyRecommendationsResponse,
  ArbiterResponse
} from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export const api = {
  // Hardware
  getHardwareStatus: async (): Promise<HardwareStatusResponse> => {
    const res = await fetch(`${API_BASE}/hardware/status`);
    if (!res.ok) throw new Error('Failed to fetch hardware status');
    return res.json();
  },

  // Providers & Models
  getProvidersStatus: async (): Promise<ProvidersStatusResponse> => {
    const res = await fetch(`${API_BASE}/providers/status`);
    if (!res.ok) throw new Error('Failed to fetch provider status');
    return res.json();
  },

  getGeminiQuota: async (): Promise<GeminiQuotaResponse> => {
    const res = await fetch(`${API_BASE}/providers/gemini-quota`);
    if (!res.ok) throw new Error('Failed to fetch Gemini quota');
    return res.json();
  },

  getModelRegistry: async (): Promise<ModelCapability[]> => {
    const res = await fetch(`${API_BASE}/providers/models`);
    if (!res.ok) throw new Error('Failed to fetch model registry');
    return res.json();
  },

  configureGeminiKey: async (apiKey: string): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/providers/gemini/configure-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to configure Gemini Key');
    }
    return res.json();
  },

  deleteGeminiKey: async (): Promise<{ success: boolean }> => {
    const res = await fetch(`${API_BASE}/providers/gemini/delete-key`, { method: 'DELETE' });
    return res.json();
  },

  testModel: async (providerName: string, modelId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/providers/test-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_name: providerName, model_id: modelId }),
    });
    return res.json();
  },

  // Projects
  listProjects: async (): Promise<ProjectRecord[]> => {
    const res = await fetch(`${API_BASE}/projects`);
    if (!res.ok) throw new Error('Failed to fetch projects');
    return res.json();
  },

  createProject: async (data: {
    name: string;
    folder_path: string;
    mode: string;
    routing_strategy: string;
    primary_model_id: string;
    secondary_model_id?: string;
    reviewer_model_id?: string;
    gemini_model_id?: string;
  }): Promise<ProjectRecord> => {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create project');
    }
    return res.json();
  },

  getProjectDetails: async (projectId: string): Promise<{ project: ProjectRecord; stats: any }> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`);
    if (!res.ok) throw new Error('Failed to fetch project details');
    return res.json();
  },

  listProjectDocuments: async (projectId: string): Promise<DocumentRecord[]> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}/documents`);
    if (!res.ok) throw new Error('Failed to list documents');
    return res.json();
  },

  startProject: async (projectId: string) => {
    const res = await fetch(`${API_BASE}/projects/${projectId}/start`, { method: 'POST' });
    return res.json();
  },

  pauseProject: async (projectId: string) => {
    const res = await fetch(`${API_BASE}/projects/${projectId}/pause`, { method: 'POST' });
    return res.json();
  },

  rescanProject: async (projectId: string) => {
    const res = await fetch(`${API_BASE}/projects/${projectId}/rescan`, { method: 'POST' });
    return res.json();
  },

  uploadPdfs: async (projectId: string, files: File[]): Promise<{ success: boolean; uploaded: string[]; documents: DocumentRecord[] }> => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await fetch(`${API_BASE}/projects/${projectId}/upload-pdf`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to upload PDF files');
    }
    return res.json();
  },

  deleteDocument: async (projectId: string, documentId: string) => {
    const res = await fetch(`${API_BASE}/projects/${projectId}/documents/${documentId}`, { method: 'DELETE' });
    return res.json();
  },

  clearProjectQueue: async (projectId: string) => {
    const res = await fetch(`${API_BASE}/projects/${projectId}/clear-queue`, { method: 'POST' });
    return res.json();
  },

  deleteProject: async (projectId: string) => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: 'DELETE' });
    return res.json();
  },

  getArbiterEngines: async (): Promise<ArbiterResponse> => {
    const res = await fetch(`${API_BASE}/system/arbiter`);
    return res.json();
  },

  // Review Workstation
  getNextReviewChunk: async (projectId: string): Promise<{ chunk: ChunkRecord | null; message?: string }> => {
    const res = await fetch(`${API_BASE}/review/${projectId}/next`);
    if (!res.ok) throw new Error('Failed to fetch next review chunk');
    return res.json();
  },

  getChunkById: async (projectId: string, chunkId: string): Promise<{ chunk: ChunkRecord }> => {
    const res = await fetch(`${API_BASE}/review/${projectId}/chunk/${chunkId}`);
    if (!res.ok) throw new Error('Failed to fetch chunk');
    return res.json();
  },

  listProjectChunks: async (projectId: string, status?: string): Promise<ChunkRecord[]> => {
    const url = status 
      ? `${API_BASE}/review/${projectId}/chunks?status=${status}` 
      : `${API_BASE}/review/${projectId}/chunks`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch chunks');
    return res.json();
  },

  approveChunk: async (chunkId: string, finalUrdu: string, saveToTm: boolean = true) => {
    const res = await fetch(`${API_BASE}/review/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chunk_id: chunkId, final_urdu: finalUrdu, save_to_tm: saveToTm }),
    });
    return res.json();
  },

  rejectChunk: async (chunkId: string) => {
    const res = await fetch(`${API_BASE}/review/reject?chunk_id=${chunkId}`, { method: 'POST' });
    return res.json();
  },

  regenerateChunk: async (chunkId: string, modelId?: string): Promise<{ success: boolean; chunk: ChunkRecord }> => {
    const res = await fetch(`${API_BASE}/review/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chunk_id: chunkId, model_id: modelId }),
    });
    return res.json();
  },

  geminiReviewChunk: async (chunkId: string, modelId: string = 'gemini-3.6-flash'): Promise<{ success: boolean; chunk: ChunkRecord }> => {
    const res = await fetch(`${API_BASE}/review/gemini-review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chunk_id: chunkId, model_id: modelId }),
    });
    return res.json();
  },

  // Glossary
  getGlossaryTerms: async (projectId?: string): Promise<GlossaryItem[]> => {
    const url = projectId ? `${API_BASE}/glossary?project_id=${projectId}` : `${API_BASE}/glossary`;
    const res = await fetch(url);
    return res.json();
  },

  addGlossaryTerm: async (term: { source_arabic: string; target_urdu: string; category?: string; notes?: string; project_id?: string }): Promise<GlossaryItem> => {
    const res = await fetch(`${API_BASE}/glossary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(term),
    });
    return res.json();
  },

  deleteGlossaryTerm: async (termId: string) => {
    const res = await fetch(`${API_BASE}/glossary/${termId}`, { method: 'DELETE' });
    return res.json();
  },

  getTranslationMemory: async (): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/glossary/translation-memory`);
    return res.json();
  },

  // Benchmark Suite
  getBenchmarkSamples: async (): Promise<BenchmarkSample[]> => {
    const res = await fetch(`${API_BASE}/benchmarks/samples`);
    return res.json();
  },

  getBenchmarkHistory: async (runName?: string): Promise<BenchmarkRunItem[]> => {
    const url = runName ? `${API_BASE}/benchmarks/history?run_name=${runName}` : `${API_BASE}/benchmarks/history`;
    const res = await fetch(url);
    return res.json();
  },

  runBenchmark: async (modelId: string, runName?: string): Promise<BenchmarkRunItem[]> => {
    const res = await fetch(`${API_BASE}/benchmarks/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: modelId, run_name: runName }),
    });
    return res.json();
  },

  runCustomBenchmark: async (customText: string, models: string[]): Promise<any> => {
    const res = await fetch(`${API_BASE}/benchmarks/custom-run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ custom_arabic_text: customText, models: models }),
    });
    return res.json();
  },

  runAllAvailableBenchmarks: async (): Promise<BenchmarkRunItem[]> => {
    const res = await fetch(`${API_BASE}/benchmarks/run-all`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to run available benchmarks');
    }
    return res.json();
  },

  clearBenchmarkHistory: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/benchmarks/history`, {
      method: 'DELETE',
    });
    return res.json();
  },

  resetProjectReviewStatus: async (projectId: string, targetStatus: string = 'awaiting_review'): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/review/${projectId}/reset-status?target_status=${targetStatus}`, {
      method: 'POST',
    });
    return res.json();
  },

  scoreBenchmark: async (
    benchmarkId: string,
    scores: { meaning: number; completeness: number; naturalness: number; terminology: number; overall: number }
  ) => {
    const res = await fetch(`${API_BASE}/benchmarks/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ benchmark_id: benchmarkId, ...scores }),
    });
    return res.json();
  },

  // System & Dependencies
  getDependencies: async (): Promise<SystemDependenciesResponse> => {
    const res = await fetch(`${API_BASE}/system/dependencies`);
    if (!res.ok) throw new Error('Failed to fetch system dependencies');
    return res.json();
  },

  installPyTorch: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/install-pytorch`, { method: 'POST' });
    return res.json();
  },

  installArgos: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/install-argos`, { method: 'POST' });
    return res.json();
  },

  getInstallStatus: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/install-status`);
    return res.json();
  },

  verifyPyTorch: async (): Promise<PyTorchVerifyResponse> => {
    const res = await fetch(`${API_BASE}/system/verify-pytorch`, { method: 'POST' });
    return res.json();
  },

  verifyArgos: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/verify-argos`, { method: 'POST' });
    return res.json();
  },

  startOllama: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/start-ollama`, { method: 'POST' });
    return res.json();
  },

  pullOllamaModel: async (modelName: string = 'qwen3:8b'): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/pull-ollama-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName }),
    });
    return res.json();
  },

  installNLLB: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/install-nllb`, { method: 'POST' });
    return res.json();
  },

  installMLXOcr: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/install-mlx-ocr`, { method: 'POST' });
    return res.json();
  },

  startMLXServer: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${API_BASE}/system/start-mlx-server`, { method: 'POST' });
    return res.json();
  },

  // Local Models Hub & Server Links
  getModelsHubStatus: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/models-hub`);
    if (!res.ok) throw new Error('Failed to fetch models hub status');
    return res.json();
  },

  updateServerUrls: async (params: { ollama_url?: string; lmstudio_url?: string; custom_models_dir?: string }): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/models-hub/update-servers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return res.json();
  },

  openModelsFolder: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/system/models-hub/open-folder`, { method: 'POST' });
    return res.json();
  },

  // English Reference
  fetchEnglishReference: async (chunkId: string, providerModelId: string = 'qwen3:8b'): Promise<{ success: boolean; chunk: ChunkRecord }> => {
    const res = await fetch(`${API_BASE}/review/fetch-english-reference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chunk_id: chunkId, provider_model_id: providerModelId }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to fetch English reference');
    }
    return res.json();
  },

  // Scorecards & Recommendations
  getProviderScorecards: async (): Promise<ProviderScorecard[]> => {
    const res = await fetch(`${API_BASE}/benchmarks/scorecard`);
    if (!res.ok) throw new Error('Failed to fetch provider scorecards');
    return res.json();
  },

  getPolicyRecommendations: async (qualityTarget: number = 4.0, privacyMode: string = 'LOCAL_ONLY'): Promise<PolicyRecommendationsResponse> => {
    const res = await fetch(`${API_BASE}/benchmarks/recommendations?quality_target=${qualityTarget}&privacy_mode=${privacyMode}`);
    if (!res.ok) throw new Error('Failed to fetch policy recommendations');
    return res.json();
  },

  // Export URLs
  getPdfUrduExportUrl: (projectId: string) => `${API_BASE}/export/${projectId}/pdf/urdu`,
  getPdfBilingualExportUrl: (projectId: string, layout: string = 'stacked') => `${API_BASE}/export/${projectId}/pdf/bilingual?layout=${layout}`,
  getPdfTrilingualExportUrl: (projectId: string) => `${API_BASE}/export/${projectId}/pdf/trilingual`,
  getPdfReviewExportUrl: (projectId: string) => `${API_BASE}/export/${projectId}/pdf/review`,
  getDocxExportUrl: (projectId: string) => `${API_BASE}/export/${projectId}/docx`,
  getTxtExportUrl: (projectId: string, bilingual: boolean = false) => `${API_BASE}/export/${projectId}/txt?bilingual=${bilingual}`,
  getJsonExportUrl: (projectId: string) => `${API_BASE}/export/${projectId}/json`,
};
