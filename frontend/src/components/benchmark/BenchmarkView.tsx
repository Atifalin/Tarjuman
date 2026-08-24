import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Play,
  CheckCircle2,
  Clock,
  RefreshCw,
  HardDrive,
  Check,
  FileText,
  BookmarkPlus,
  AlertCircle,
  Download,
  Terminal,
  Layers,
  Zap,
  Server,
  Trash2
} from 'lucide-react';
import {
  BenchmarkSample,
  BenchmarkRunItem,
  ModelCapability,
  SystemDependenciesResponse,
  CustomBenchmarkResponse
} from '../../types';
import { api } from '../../services/api';
import { ProviderScorecardView } from './ProviderScorecardView';

interface BenchmarkViewProps {
  models: ModelCapability[];
}

const SAMPLE_20_PASSAGES = `1. عن أبي هريرة رضي الله عنه قال: قال رسول الله صلى الله عليه وسلم: «كلمتان خفيفتان على اللسان، ثقيلتان في الميزان، حبيبتان إلى الرحمن: سبحان الله وبحمده، سبحان الله العظيم».

2. قال الإمام الشافعي رحمه الله: ما ناظرت أحداً قط إلا أحببت أن يوفق ويسدد ويعان، ويكون عليه رعاية من الله وحفظ.

3. أجمع الفقهاء على أن الطهارة شرط لصحة الصلاة، وهي تنقسم إلى طهارة الحدث وطهارة الخبث في الثوب والبدن والمكان.

4. تعتبر مدينة بغداد من أعظم مراكز الإشعاع العلمي في العصر العباسي، حيث أسس الخليفة المأمون بيت الحكمة لدراسة الفلك والطب والفلسفة.

5. إن التطور التكنولوجي في معالجة اللغات الطبيعية ساهم بشكل فعال في بناء نظم الترجمة الآلية العصبية المتقدمة.

6. أعلنت وزارة التعليم العالي عن إطلاق مبادرة وطنية شاملة لتطوير المناهج الدراسية ودعم البحث العلمي في الجامعات الحكومية.

7. يهدف المشروع الاقتصادي الجديد إلى تعزيز الاستثمارات الأجنبية المباشرة وتوفير أكثر من خمسين ألف فرصة عمل جديدة خلال عام 2026.

8. قال الحكيم: العلم صيد والكتابة قيده، قيّد صيودك بالحبال الواثقة، فمن الحماقة أن تصيد غزالة وتتركها بين الخلائق طالقة.

9. اتفقت الأطراف المتعاقدة في هذا العقد التجاري على تسليم البضائع في ميناء الوصول خلال مدة لا تتجاوز ثلاثين يوماً من تاريخ التوقيع.

10. كشفت الدراسات المناخية الحديثة عن ارتفاع ملحوظ في درجات حرارة المحيطات، مما يؤثر سلباً على التنوع البيولوجي والشعب المرجانية.`;

export const BenchmarkView: React.FC<BenchmarkViewProps> = ({ models }) => {
  const [samples, setSamples] = useState<BenchmarkSample[]>([]);
  const [history, setHistory] = useState<BenchmarkRunItem[]>([]);
  const [deps, setDeps] = useState<SystemDependenciesResponse | null>(null);
  const [selectedModel, setSelectedModel] = useState('gemini-3.6-flash');
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'custom' | 'scorecard' | 'run' | 'history'>('scorecard');

  // PyTorch / Action inline state
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  // Custom text multi-passage benchmark
  const [customArabicText, setCustomArabicText] = useState(
    'تعد دراسة العلوم وتدوين المعارف من أعظم أسباب نهضة الأمم وتقدم الحضارات الإنسانية عبر التاريخ.'
  );
  const [selectedModelsForCustom, setSelectedModelsForCustom] = useState<string[]>([]);
  const [customResults, setCustomResults] = useState<CustomBenchmarkResponse | null>(null);
  const [customRunning, setCustomRunning] = useState(false);

  const loadData = async () => {
    try {
      const s = await api.getBenchmarkSamples();
      setSamples(s);
      const h = await api.getBenchmarkHistory();
      setHistory(h);
      const d = await api.getDependencies();
      setDeps(d);

      // Pre-select ready models if not already chosen
      if (selectedModelsForCustom.length === 0 && d?.readiness_matrix) {
        const readyModels = Object.entries(d.readiness_matrix)
          .filter(([_, item]) => (item as any)?.ready)
          .map(([mId]) => mId);
        setSelectedModelsForCustom(readyModels.length > 0 ? readyModels : ['gemini-3.6-flash']);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleInstallTorchInline = async () => {
    setActionInProgress('torch');
    setActionMsg('Installing Apple Silicon PyTorch & Transformers in background...');
    try {
      await api.installPyTorch();
      // Poll until done
      const poll = setInterval(async () => {
        const st = await api.getInstallStatus();
        if (st.status === 'completed') {
          clearInterval(poll);
          setActionInProgress(null);
          setActionMsg('✅ PyTorch installed successfully!');
          await loadData();
        } else if (st.status === 'failed') {
          clearInterval(poll);
          setActionInProgress(null);
          setActionMsg(`❌ Installation failed: ${st.error}`);
        }
      }, 2000);
    } catch (e: any) {
      setActionInProgress(null);
      setActionMsg(`Failed: ${e.message}`);
    }
  };

  const handleStartOllamaInline = async () => {
    setActionInProgress('ollama');
    setActionMsg('Starting Ollama daemon...');
    try {
      const res = await api.startOllama();
      setActionMsg(res.message);
      await loadData();
    } catch (e: any) {
      setActionMsg(`Error: ${e.message}`);
    } finally {
      setActionInProgress(null);
    }
  };

  const handlePullQwenInline = async () => {
    setActionInProgress('qwen');
    setActionMsg('Pulling Qwen3 8B in Ollama...');
    try {
      const res = await api.pullOllamaModel('qwen3:8b');
      setActionMsg(res.message);
      await loadData();
    } catch (e: any) {
      setActionMsg(`Error: ${e.message}`);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleRunBenchmark = async () => {
    setRunning(true);
    try {
      await api.runBenchmark(selectedModel);
      await loadData();
      setActiveTab('history');
    } catch (e: any) {
      alert(`Benchmark run failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleRunAllAvailable = async () => {
    setRunning(true);
    try {
      await api.runAllAvailableBenchmarks();
      await loadData();
      setActiveTab('history');
    } catch (e: any) {
      alert(`Benchmark run failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleClearHistory = async () => {
    if (!confirm('Are you sure you want to clear all benchmark run history and scores?')) return;
    try {
      await api.clearBenchmarkHistory();
      setHistory([]);
      setCustomResults(null);
      await loadData();
    } catch (e: any) {
      alert(`Failed to clear history: ${e.message}`);
    }
  };

  const handleRunCustomComparison = async () => {
    if (!customArabicText.trim()) return;
    setCustomRunning(true);
    try {
      const res = await api.runCustomBenchmark(customArabicText.trim(), selectedModelsForCustom);
      setCustomResults(res);
      await loadData();
    } catch (e: any) {
      alert(`Custom benchmark comparison failed: ${e.message}`);
    } finally {
      setCustomRunning(false);
    }
  };

  const toggleCustomModel = (mId: string) => {
    setSelectedModelsForCustom((prev) =>
      prev.includes(mId) ? prev.filter((m) => m !== mId) : [...prev, mId]
    );
  };

  const handleScoreChange = async (
    benchId: string,
    field: 'meaning' | 'completeness' | 'naturalness' | 'terminology' | 'overall',
    val: number
  ) => {
    const item = history.find((h) => h.id === benchId);
    if (!item) return;

    const meaning = field === 'meaning' ? val : item.manual_meaning_score || 5;
    const completeness = field === 'completeness' ? val : item.manual_completeness_score || 5;
    const naturalness = field === 'naturalness' ? val : item.manual_naturalness_score || 5;
    const terminology = field === 'terminology' ? val : item.manual_terminology_score || 5;
    const overall = field === 'overall' ? val : item.manual_overall_score || 5;

    try {
      await api.scoreBenchmark(benchId, {
        meaning,
        completeness,
        naturalness,
        terminology,
        overall
      });
      setHistory((prev) =>
        prev.map((h) =>
          h.id === benchId
            ? {
                ...h,
                manual_meaning_score: meaning,
                manual_completeness_score: completeness,
                manual_naturalness_score: naturalness,
                manual_terminology_score: terminology,
                manual_overall_score: overall
              }
            : h
        )
      );
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            Empirical Arabic → Urdu Multi-Model Benchmark Suite
          </h2>
          <p className="text-xs text-slate-400">
            Real side-by-side translation evaluation of NLLB-200, Argos Translate, Qwen3, and MADLAD-400.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAllAvailable}
            disabled={running}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold px-4 py-2 rounded-xl transition-colors shadow-md shadow-emerald-600/20"
          >
            {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>Benchmark All Ready Models</span>
          </button>

          {history.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-1.5 bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800 text-xs font-semibold px-3 py-2 rounded-xl transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear History</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('scorecard')}
          className={`text-xs font-bold px-4 py-2 rounded-xl transition-colors ${
            activeTab === 'scorecard'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900'
          }`}
        >
          Provider Scorecard & Recommendations
        </button>

        <button
          onClick={() => setActiveTab('custom')}
          className={`text-xs font-bold px-4 py-2 rounded-xl transition-colors ${
            activeTab === 'custom'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900'
          }`}
        >
          Custom Text Multi-Passage Benchmark
        </button>

        <button
          onClick={() => setActiveTab('run')}
          className={`text-xs font-bold px-4 py-2 rounded-xl transition-colors ${
            activeTab === 'run'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900'
          }`}
        >
          10-Category Standard Dataset
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`text-xs font-bold px-4 py-2 rounded-xl transition-colors ${
            activeTab === 'history'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900'
          }`}
        >
          Scoring History & Evaluation ({history.length})
        </button>
      </div>

      {/* Action Notification Banner */}
      {actionMsg && (
        <div className="bg-indigo-950/70 border border-indigo-500/40 text-indigo-200 px-4 py-3 rounded-xl text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            {actionInProgress ? <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            <span>{actionMsg}</span>
          </div>
          <button onClick={() => setActionMsg(null)} className="text-slate-400 hover:text-white text-[11px]">
            Dismiss
          </button>
        </div>
      )}

      {/* TAB 0: PROVIDER SCORECARD & RECOMMENDATIONS */}
      {activeTab === 'scorecard' && (
        <ProviderScorecardView activeProject={null} onNavigateToBenchmark={() => setActiveTab('custom')} />
      )}

      {/* TAB 1: CUSTOM TEXT MULTI-PASSAGE BENCHMARK */}
      {activeTab === 'custom' && (
        <div className="space-y-6">
          
          {/* PROVIDER READINESS MATRIX BANNER */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 shadow-lg">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                Model Readiness & Dependency Status:
              </h3>
              <button
                onClick={loadData}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 bg-slate-800 px-2.5 py-1 rounded-lg"
              >
                <RefreshCw className="w-3 h-3" />
                Refresh Readiness
              </button>
            </div>

            <div className="grid grid-cols-4 gap-3">
              {/* MADLAD-400 */}
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">MADLAD-400 7B</span>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    deps?.pytorch.installed ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}>
                    {deps?.pytorch.installed ? '✓ READY' : '❌ PyTorch Missing'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Seq2Seq MT Model</p>
                {!deps?.pytorch.installed && (
                  <button
                    onClick={handleInstallTorchInline}
                    disabled={actionInProgress === 'torch'}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-[10px] font-bold py-1.5 rounded-lg flex items-center justify-center gap-1"
                  >
                    {actionInProgress === 'torch' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                    Install PyTorch (MPS)
                  </button>
                )}
              </div>

              {/* Meta NLLB-200 */}
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">Meta NLLB-200</span>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    deps?.pytorch.installed ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}>
                    {deps?.pytorch.installed ? '✓ READY' : '❌ PyTorch Missing'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">3.3B Distilled Seq2Seq</p>
                {!deps?.pytorch.installed && (
                  <button
                    onClick={handleInstallTorchInline}
                    disabled={actionInProgress === 'torch'}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-[10px] font-bold py-1.5 rounded-lg flex items-center justify-center gap-1"
                  >
                    {actionInProgress === 'torch' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                    Install PyTorch (MPS)
                  </button>
                )}
              </div>

              {/* Qwen3 8B */}
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">Qwen3 8B</span>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    deps?.ollama.running && deps.ollama.qwen3_installed
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-rose-950 text-rose-300 border border-rose-800'
                  }`}>
                    {!deps?.ollama.running ? '❌ Not Running' : (!deps.ollama.qwen3_installed ? '❌ Model Missing' : '✓ READY')}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Ollama Local LLM</p>
                {!deps?.ollama.running ? (
                  <button
                    onClick={handleStartOllamaInline}
                    disabled={actionInProgress === 'ollama'}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-[10px] font-bold py-1.5 rounded-lg flex items-center justify-center gap-1"
                  >
                    <Play className="w-3 h-3" />
                    Start Ollama
                  </button>
                ) : !deps.ollama.qwen3_installed ? (
                  <button
                    onClick={handlePullQwenInline}
                    disabled={actionInProgress === 'qwen'}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-[10px] font-bold py-1.5 rounded-lg flex items-center justify-center gap-1"
                  >
                    <Download className="w-3 h-3" />
                    Pull Qwen3 8B
                  </button>
                ) : null}
              </div>

              {/* Google Gemini */}
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">Gemini 3.6 Flash</span>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    deps?.gemini.configured ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}>
                    {deps?.gemini.configured ? '✓ READY' : '❌ Key Missing'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Google Cloud API</p>
                <span className="text-[10px] text-emerald-400 font-mono block">
                  {deps?.gemini.configured ? 'Keychain Verified' : 'Configure in Settings'}
                </span>
              </div>
            </div>
          </div>

          {/* Paste Arabic Passages */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">
                Paste 1 to 50 Arabic Passages for Multi-Model Evaluation:
              </h3>
              <button
                type="button"
                onClick={() => setCustomArabicText(SAMPLE_20_PASSAGES)}
                className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-mono bg-indigo-950/40 border border-indigo-500/30 px-3 py-1.5 rounded-lg"
              >
                <BookmarkPlus className="w-3.5 h-3.5" />
                Load 10 Representative Test Passages
              </button>
            </div>

            <textarea
              value={customArabicText}
              onChange={(e) => setCustomArabicText(e.target.value)}
              rows={6}
              placeholder="أدخل مقاطع النصوص العربية هنا (افصل بين المقاطع بسطر فارغ)..."
              className="w-full bg-slate-950 p-4 rounded-xl border border-slate-700 text-slate-100 font-arabic-text text-lg focus:outline-none focus:border-indigo-500 leading-relaxed"
            />

            {/* Model Selection Grid */}
            <div className="space-y-2">
              <span className="text-xs text-slate-400 font-medium">Select Models to Run Side-by-Side:</span>
              <div className="flex flex-wrap gap-3">
                {models.map((m) => {
                  const isReady = deps?.readiness_matrix?.[m.model_id]?.ready ?? false;
                  return (
                    <label
                      key={m.model_id}
                      className={`flex items-center gap-2 text-xs px-3.5 py-2 rounded-xl border cursor-pointer transition-all ${
                        selectedModelsForCustom.includes(m.model_id)
                          ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 font-bold shadow-sm'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedModelsForCustom.includes(m.model_id)}
                        onChange={() => toggleCustomModel(m.model_id)}
                        className="hidden"
                      />
                      <span className="font-mono">{m.display_name}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                        isReady ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'
                      }`}>
                        {isReady ? 'READY' : 'UNAVAILABLE'}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <span className="text-xs text-slate-500 font-mono">
                {customArabicText.split('\n\n').filter((p) => p.trim()).length} passage(s) | {selectedModelsForCustom.length} model(s) selected
              </span>

              <button
                onClick={handleRunCustomComparison}
                disabled={customRunning || selectedModelsForCustom.length === 0 || !customArabicText.trim()}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition-all shadow-lg shadow-indigo-600/20"
              >
                {customRunning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                <span>{customRunning ? 'Executing Multi-Model Evaluation...' : 'Run Side-by-Side Benchmark'}</span>
              </button>
            </div>
          </div>

          {/* Results Side-by-Side Matrix */}
          {customResults && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-400" />
                  Benchmark Results: {customResults.total_passages} Passage(s) Evaluated
                </h3>
                <span className="text-xs text-slate-400 font-mono">Run: {customResults.run_name}</span>
              </div>

              {customResults.passages.map((p, pIdx) => (
                <div key={pIdx} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
                  
                  {/* Source Passage Banner */}
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-850 space-y-1">
                    <div className="flex items-center justify-between text-xs text-slate-400 pb-1 border-b border-slate-800/80">
                      <span className="font-bold text-indigo-400">Passage #{p.passage_index}</span>
                      <span className="font-mono">{p.word_count} Arabic words</span>
                    </div>
                    <p className="font-arabic-text text-lg text-slate-200 pt-1 leading-relaxed">{p.source_arabic}</p>
                  </div>

                  {/* Model Outputs Side-by-Side Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    {p.outputs.map((res, mIdx) => {
                      const isFailed = res.execution_status === 'FAILED' || res.execution_status === 'NOT_INSTALLED' || res.execution_status === 'NOT_CONNECTED' || !res.urdu_text;
                      return (
                        <div key={mIdx} className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3">
                          
                          {/* Model header */}
                          <div className="flex items-center justify-between text-xs border-b border-slate-800 pb-2">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-white font-mono">{res.model_id}</span>
                              <span className="text-[10px] bg-slate-900 px-2 py-0.5 rounded text-slate-400 border border-slate-800">
                                {res.provider_name.toUpperCase()}
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              <span className="flex items-center gap-1 text-slate-400 font-mono text-[11px]">
                                <Clock className="w-3 h-3 text-indigo-400" />
                                {res.latency_ms !== null && res.latency_ms !== undefined ? `${res.latency_ms} ms` : 'N/A'}
                              </span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                isFailed ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              }`}>
                                {res.execution_status || res.qa_status}
                              </span>
                            </div>
                          </div>

                          {/* Translated Output or Failed Diagnostic */}
                          <div className="min-h-[90px]">
                            {res.urdu_text ? (
                              <div className="space-y-1">
                                <p className="font-urdu-text text-xl text-emerald-300 leading-loose">{res.urdu_text}</p>
                                {res.provider_name === 'gemini' && (
                                  <span className="text-[10px] text-amber-400/80 font-mono">
                                    ⏱ Cloud API Roundtrip: Network latency + Remote model generation
                                  </span>
                                )}
                              </div>
                            ) : (
                              <div className="bg-rose-950/30 border border-rose-500/30 rounded-lg p-3 text-xs text-rose-300 space-y-1">
                                <div className="font-bold flex items-center gap-1.5 text-rose-400">
                                  <AlertCircle className="w-4 h-4" />
                                  <span>Inference Failed (No Output)</span>
                                </div>
                                <p className="font-mono text-[11px] text-rose-200/90 break-words">{res.error || 'Provider execution failed.'}</p>
                              </div>
                            )}
                          </div>

                          {/* Resource Telemetry */}
                          <div className="grid grid-cols-4 gap-1.5 pt-2 border-t border-slate-800/80 text-[10px] text-slate-400">
                            <div>
                              <span className="block text-slate-500">Output Words:</span>
                              <span className="font-mono text-slate-200 font-bold">{res.output_length_words || 'None'}</span>
                            </div>
                            <div>
                              <span className="block text-slate-500">Throughput:</span>
                              <span className="font-mono text-indigo-300 font-bold">
                                {res.throughput_chunks_per_min !== null && res.throughput_chunks_per_min !== undefined
                                  ? `${res.throughput_chunks_per_min} ch/m`
                                  : 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="block text-slate-500">Peak RAM RSS:</span>
                              <span className="font-mono text-slate-200 font-bold">{res.memory_metrics.process_ram_mb} MB</span>
                            </div>
                            <div>
                              <span className="block text-slate-500">Pressure:</span>
                              <span className="font-mono text-emerald-400 font-bold">{res.memory_metrics.memory_pressure}</span>
                            </div>
                          </div>

                        </div>
                      );
                    })}
                  </div>

                </div>
              ))}
            </div>
          )}

        </div>
      )}

      {/* TAB 2: SAMPLES 10 CATEGORIES */}
      {activeTab === 'run' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900 p-4 rounded-2xl border border-slate-800">
            <div>
              <span className="text-xs text-slate-300 font-bold block">Run Complete 10-Category Arabic Benchmark:</span>
              <span className="text-[11px] text-slate-400">Executes standard Fiqh, Classical, News, Hadith, and Number preservation tests.</span>
            </div>

            <div className="flex items-center gap-3">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-slate-100 text-xs px-3 py-2 rounded-xl font-mono"
              >
                {models.map((m) => (
                  <option key={m.model_id} value={m.model_id}>
                    {m.display_name}
                  </option>
                ))}
              </select>

              <button
                onClick={handleRunBenchmark}
                disabled={running}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl shadow-md"
              >
                {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                <span>{running ? 'Running 10 Samples...' : 'Execute Benchmark'}</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {samples.map((s, idx) => (
              <div key={s.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-indigo-400">#{idx + 1} {s.category}</span>
                  <span className="text-slate-500 font-mono">{s.title}</span>
                </div>
                <p className="font-arabic-text text-lg text-slate-100 bg-slate-950 p-3 rounded-xl border border-slate-850">
                  {s.source}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: SCORING HISTORY & EVALUATION */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {history.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-xs text-slate-400">
              No benchmark runs recorded yet. Run a benchmark above to score model performance.
            </div>
          ) : (
            history.map((h) => {
              const isFailed = h.execution_status === 'FAILED' || !h.target_urdu;
              return (
                <div key={h.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
                  <div className="flex items-center justify-between text-xs border-b border-slate-800 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-indigo-400">{h.category}</span>
                      <span className="text-slate-600">|</span>
                      <span className="font-mono text-slate-300">{h.model_name}</span>
                      <span className="text-[10px] bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-400">
                        {h.provider_name.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="font-mono text-slate-400 text-[11px]">
                        Latency: {h.latency_ms !== null && h.latency_ms !== undefined ? `${h.latency_ms} ms` : 'N/A'}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isFailed ? 'bg-rose-950 text-rose-300' : 'bg-emerald-950 text-emerald-300'
                      }`}>
                        {h.qa_status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400 font-semibold block">Arabic Source:</span>
                      <p className="font-arabic-text text-base text-slate-200 bg-slate-950 p-3 rounded-xl border border-slate-850 leading-relaxed">
                        {h.source_arabic}
                      </p>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[11px] text-emerald-400 font-semibold block">Urdu Output:</span>
                      {h.target_urdu ? (
                        <p className="font-urdu-text text-xl text-emerald-300 bg-slate-950 p-3 rounded-xl border border-slate-850 leading-loose">
                          {h.target_urdu}
                        </p>
                      ) : (
                        <div className="bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs p-3 rounded-xl font-mono">
                          {h.error || 'Execution failed / No translation output'}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 5-Dimension Manual Evaluation Form */}
                  {h.target_urdu && (
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                        <span>5-Dimension Human Evaluation Scorecard:</span>
                        <span className="text-indigo-400 font-mono">
                          Overall: {h.manual_overall_score || 5}/5
                        </span>
                      </div>

                      <div className="grid grid-cols-5 gap-3">
                        {(['meaning', 'completeness', 'naturalness', 'terminology', 'overall'] as const).map((field) => {
                          const val = (h as any)[`manual_${field}_score`] || 5;
                          return (
                            <div key={field} className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1 text-center">
                              <span className="text-[11px] text-slate-400 block capitalize">{field}</span>
                              <div className="flex items-center justify-center gap-1">
                                {[1, 2, 3, 4, 5].map((score) => (
                                  <button
                                    key={score}
                                    onClick={() => handleScoreChange(h.id, field, score)}
                                    className={`w-6 h-6 rounded text-xs font-bold transition-all ${
                                      val === score
                                        ? 'bg-indigo-600 text-white shadow-sm'
                                        : 'bg-slate-950 text-slate-400 hover:bg-slate-800'
                                    }`}
                                  >
                                    {score}
                                  </button>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                </div>
              );
            })
          )}
        </div>
      )}

    </div>
  );
};
