export interface HardwareMetrics {
  chip_name: string;
  is_apple_silicon: boolean;
  hardware_profile: '16GB_COMPATIBLE' | '24GB_BALANCED' | '32GB_PERFORMANCE';
  cpu_percent: number;
  cpu_cores_logical: number;
  cpu_cores_physical: number;
  total_ram_gb: number;
  used_ram_gb: number;
  available_ram_gb: number;
  ram_percent: number;
  swap_used_mb: number;
  memory_pressure: 'GREEN' | 'YELLOW' | 'RED' | 'UNKNOWN';
  disk_total_gb: number;
  disk_free_gb: number;
  disk_percent: number;
  process_memory_mb: number;
  temperature: string;
}

export interface ThrottlePolicy {
  action: string;
  max_concurrency: number;
  allow_secondary_model: boolean;
  allow_reviewer_model: boolean;
  reason: string;
  profile: string;
}

export type ProviderClass = 'LOCAL_MT' | 'LOCAL_AI' | 'APPLE_LOCAL' | 'CLOUD_AI' | 'PUBLIC_WEB' | 'TEST';
export type PrivacyClass = 'OFFLINE' | 'APPLE_LOCAL' | 'CLOUD_USER_ENABLED' | 'PUBLIC_WEB_USER_ENABLED';
export type ProductionPolicy = 'FAST_LOCAL' | 'BEST_LOCAL_QUALITY' | 'BALANCED' | '16GB_SAFE' | '32GB_QUALITY' | 'ADAPTIVE_ESCALATION';

export interface ModelCapability {
  model_id: string;
  display_name: string;
  provider_name: string;
  provider_class: ProviderClass;
  privacy_class: PrivacyClass;
  architecture: string;
  execution_backends: string[];
  source_languages: string[];
  target_languages: string[];
  translation_capable: boolean;
  review_capable: boolean;
  parameter_count: string;
  precision: string;
  quantization: string;
  estimated_runtime_ram_gb: number;
  minimum_recommended_ram_gb: number;
  recommended_ram_gb: number;
  verified: boolean;
  official_source_url: string;
  role: string;
  direct_pair: boolean;
  pivot_languages: string[];
  route_description: string;
}

export interface ProviderStatusItem {
  is_available: boolean;
  status_message: string;
  status_code?: string;
  details: Record<string, any>;
}

export interface ProvidersStatusResponse {
  system_ready: boolean;
  status_label: 'READY' | 'SETUP REQUIRED';
  providers: {
    ollama: ProviderStatusItem;
    lmstudio: ProviderStatusItem;
    gemini: ProviderStatusItem;
    transformers: ProviderStatusItem;
    argos?: ProviderStatusItem;
    apple_translation?: ProviderStatusItem;
    public_web?: ProviderStatusItem;
  };
  cloud_usage: {
    today_requests: number;
    today_input_tokens: number;
    today_output_tokens: number;
  };
}

export interface ProjectRecord {
  id: string;
  name: string;
  folder_path: string;
  mode: 'review' | 'automatic' | 'hybrid' | 'compare';
  routing_strategy: string;
  production_policy?: ProductionPolicy;
  privacy_mode?: 'LOCAL_ONLY' | 'LOCAL_AND_CLOUD' | 'ALLOW_PUBLIC_WEB';
  quality_target?: number;
  min_meaning_floor?: number;
  min_completeness_floor?: number;
  min_naturalness_floor?: number;
  min_terminology_floor?: number;
  primary_model_id: string;
  secondary_model_id?: string;
  reviewer_model_id?: string;
  gemini_model_id?: string;
  preferred_english_provider?: string;
  status: 'active' | 'paused' | 'completed';
  created_at: string;
  updated_at: string;
}

export interface DocumentRecord {
  id: string;
  project_id: string;
  filename: string;
  filepath: string;
  total_pages: number;
  processed_pages: number;
  total_chunks: number;
  completed_chunks: number;
  is_scanned: boolean;
  status: string;
  error_message?: string;
}

export interface ChunkRecord {
  id: string;
  document_id: string;
  project_id: string;
  page_number: number;
  chunk_index: number;
  source_text: string;
  target_urdu?: string;
  secondary_urdu?: string;
  reviewer_urdu?: string;
  final_urdu?: string;
  status: 'pending' | 'translating' | 'qa' | 'awaiting_review' | 'approved' | 'rejected' | 'failed';
  qa_status?: 'PASS' | 'WARNING' | 'REVIEW_REQUIRED' | 'FAILED';
  qa_issues: string[];
  primary_provider?: string;
  primary_provider_class?: string;
  primary_model?: string;
  execution_backend?: string;
  route?: string;
  is_pivot?: boolean;
  pivot_languages?: string[];
  secondary_provider?: string;
  secondary_model?: string;
  review_provider?: string;
  review_model?: string;
  approved_by?: string;
  approved_at?: string;
  latency_ms?: number;
  peak_ram_mb?: number;
  memory_pressure?: string;
  english_reference?: string;
  english_reference_provider?: string;
  english_reference_model?: string;
  english_reference_route?: string;
  english_reference_timestamp?: string;
  ocr_provider?: string;
  ocr_engine?: string;
  ocr_language?: string;
  ocr_confidence?: number;
  ocr_timestamp?: string;
  created_at: string;
  updated_at: string;
}

export interface ProviderScorecard {
  provider_id: string;
  provider_name: string;
  provider_class: string;
  privacy_class: string;
  cost_class: string;
  route: string;
  is_pivot: boolean;
  pivot_languages: string[];
  sample_count: number;
  documents_sampled: number;
  pages_sampled: number;
  human_reviews: number;
  quality_score?: number;
  meaning_score?: number;
  completeness_score?: number;
  naturalness_score?: number;
  terminology_score?: number;
  overall_score?: number;
  latency_ms?: number;
  peak_ram_mb?: number;
  model_load_time_ms?: number;
  availability_status: string;
}

export interface RecommendationItem {
  provider_id: string;
  provider_name: string;
  score?: number;
  latency_ms?: number;
  peak_ram_mb?: number;
  sample_count?: number;
  reason: string;
}

export interface PolicyRecommendationsResponse {
  has_benchmark_data: boolean;
  total_benchmark_runs?: number;
  message?: string;
  recommendations: {
    best_quality?: RecommendationItem;
    fastest_verified?: RecommendationItem;
    lowest_memory?: RecommendationItem;
    best_local?: RecommendationItem;
    best_balanced?: RecommendationItem;
  };
  scorecards: ProviderScorecard[];
}

export interface GlossaryItem {
  id?: string;
  project_id?: string;
  source_arabic: string;
  target_urdu: string;
  category?: string;
  notes?: string;
  is_approved: boolean;
  created_at?: string;
}

export interface BenchmarkSample {
  id: string;
  category: string;
  title: string;
  source: string;
}

export type ExecutionStatus = 'READY' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED' | 'NOT_INSTALLED' | 'NOT_CONNECTED' | 'NOT_CONFIGURED';

export interface BenchmarkOutput {
  bench_id: string;
  model_id: string;
  provider_name: string;
  execution_status?: ExecutionStatus;
  urdu_text: string | null;
  latency_ms: number | null;
  output_length_chars: number;
  output_length_words: number;
  throughput_chunks_per_min: number | null;
  estimated_tokens_per_min: number | null;
  qa_status: string;
  qa_issues: string[];
  error?: string | null;
  memory_metrics: {
    process_ram_mb: number;
    ram_percent: number;
    memory_pressure: string;
    swap_used_mb: number;
  };
}

export interface CustomBenchmarkPassageResult {
  passage_index: number;
  source_arabic: string;
  word_count: number;
  outputs: BenchmarkOutput[];
}

export interface CustomBenchmarkResponse {
  run_name: string;
  total_passages: number;
  models_tested: number;
  passages: CustomBenchmarkPassageResult[];
}

export interface BenchmarkRunItem {
  id: string;
  run_name: string;
  test_case_id: string;
  category: string;
  title?: string;
  source_arabic: string;
  provider_name: string;
  model_name: string;
  target_urdu: string | null;
  latency_ms: number | null;
  output_length_chars?: number;
  output_length_words?: number;
  peak_ram_mb?: number;
  memory_pressure?: string;
  qa_status: string;
  execution_status?: ExecutionStatus;
  error?: string | null;
  manual_meaning_score?: number;
  manual_completeness_score?: number;
  manual_naturalness_score?: number;
  manual_terminology_score?: number;
  manual_overall_score?: number;
}

export interface ModelReadinessItem {
  ready: boolean;
  status: ExecutionStatus;
  reason: string;
}

export interface SystemDependenciesResponse {
  pytorch: {
    installed: boolean;
    torch_version: string | null;
    transformers_installed: boolean;
    transformers_version: string | null;
    mps_available: boolean;
    device: string;
  };
  argos?: {
    installed: boolean;
    version: string | null;
    packages_installed: boolean;
    languages: string[];
  };
  ollama: {
    running: boolean;
    endpoint: string;
    installed_models: string[];
    qwen3_installed: boolean;
  };
  gemini: {
    configured: boolean;
  };
  mlx?: {
    installed: boolean;
    weights_exist: boolean;
    server_running: boolean;
    is_apple_silicon: boolean;
  };
  readiness_matrix: Record<string, ModelReadinessItem>;
  install_state: {
    status: 'idle' | 'installing' | 'completed' | 'failed';
    target: string | null;
    logs: string;
    error: string | null;
  };
}

export interface ArgosVerifyResponse {
  success: boolean;
  installed: boolean;
  packages_installed: boolean;
  languages?: string[];
  message: string;
  error?: string;
}

export interface PyTorchVerifyResponse {
  success: boolean;
  installed: boolean;
  mps_available: boolean;
  torch_version?: string;
  transformers_version?: string;
  message: string;
  error?: string;
}

export interface GeminiQuotaTierSummary {
  tier_name: string;
  rpm_cap: number;
  rpm_active: number;
  tpm_cap: number;
  tpm_active: number;
  rpd_cap: number;
  rpd_used: number;
  rpd_remaining: number;
  percentage_used: number;
  is_exhausted: boolean;
  is_approaching_limit: boolean;
}

export interface GeminiQuotaResponse {
  date: string;
  tiers: {
    'flash-lite'?: GeminiQuotaTierSummary;
    'flash': GeminiQuotaTierSummary;
    'pro'?: GeminiQuotaTierSummary;
  };
}

export interface ServerActivity {
  status: 'IDLE' | 'INGESTING' | 'OCR_PROCESSING' | 'TRANSLATING' | 'REVIEWING' | 'ERROR' | 'COMPLETED' | 'PAUSED';
  activity_message: string;
  current_project_id?: string | null;
  current_file?: string | null;
  current_chunk?: string | null;
  last_error?: string | null;
  error_timestamp?: string | null;
  updated_at: string;
}

export interface HardwareStatusResponse {
  metrics: HardwareMetrics;
  throttle_policy: ThrottlePolicy;
  server_activity?: ServerActivity;
}

export interface ArbiterResponse {
  status: 'READY' | 'INSTALL_REQUIRED';
  status_message: string;
  ocr: {
    engine: string;
    is_fallback: boolean;
    label: string;
    reason: string;
  };
  translation: {
    engine: string;
    is_fallback: boolean;
    label: string;
    route: string;
    ready: boolean;
  };
  hardware: {
    ram_percent: number;
    memory_pressure: string;
    process_memory_mb: number;
  };
}


