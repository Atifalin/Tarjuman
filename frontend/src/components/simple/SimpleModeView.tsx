import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  Play,
  Pause,
  CheckCircle2,
  AlertCircle,
  Download,
  RefreshCw,
  Trash2,
  ArrowRight,
  ArrowLeft,
  Layers,
  Cpu,
  Check,
  Edit3,
  RotateCcw,
  Sparkles,
  BookOpen,
  Eye,
  FolderOpen
} from 'lucide-react';
import {
  ProjectRecord,
  DocumentRecord,
  ChunkRecord,
  ModelCapability,
  ArbiterResponse,
  SystemDependenciesResponse
} from '../../types';
import { api } from '../../services/api';

interface SimpleModeViewProps {
  activeProject: ProjectRecord | null;
  onSelectProject: (proj: ProjectRecord) => void;
  models: ModelCapability[];
  onSwitchToAdvanced: () => void;
}

export const SimpleModeView: React.FC<SimpleModeViewProps> = ({
  activeProject,
  onSelectProject,
  models,
  onSwitchToAdvanced
}) => {
  // Step in the simple 5-step flow: 1: Upload, 2: Model Check, 3: Run, 4: Review, 5: Export
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [projectStats, setProjectStats] = useState<any>(null);
  const [arbiter, setArbiter] = useState<ArbiterResponse | null>(null);
  const [deps, setDeps] = useState<SystemDependenciesResponse | null>(null);

  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Review State
  const [reviewChunks, setReviewChunks] = useState<ChunkRecord[]>([]);
  const [reviewIndex, setReviewIndex] = useState<number>(0);
  const [editedUrdu, setEditedUrdu] = useState<string>('');
  const [savingReview, setSavingReview] = useState<boolean>(false);
  const [showEnglishRef, setShowEnglishRef] = useState<boolean>(false);

  const loadProjectData = async (projId: string) => {
    try {
      const statsRes = await api.getProjectDetails(projId);
      setProjectStats(statsRes.stats);
      const docs = await api.listProjectDocuments(projId);
      setDocuments(docs);
      const arb = await api.getArbiterEngines();
      setArbiter(arb);
      const d = await api.getDependencies();
      setDeps(d);
    } catch (e) {
      console.error(e);
    }
  };

  const loadAllProjects = async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
      if (!activeProject && list.length > 0) {
        onSelectProject(list[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadAllProjects();
  }, []);

  useEffect(() => {
    if (!activeProject) return;
    loadProjectData(activeProject.id);

    const interval = setInterval(() => {
      loadProjectData(activeProject.id);
    }, 1200);
    return () => clearInterval(interval);
  }, [activeProject?.id]);

  // Handle Review Chunk Loading
  const loadReviewChunks = async () => {
    if (!activeProject) return;
    try {
      const chunks = await api.listProjectChunks(activeProject.id);
      setReviewChunks(chunks);
      if (chunks.length > 0) {
        const current = chunks[reviewIndex] || chunks[0];
        setEditedUrdu(current.final_urdu || current.target_urdu || '');
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (currentStep === 4) {
      loadReviewChunks();
    }
  }, [currentStep, activeProject?.id]);

  useEffect(() => {
    if (reviewChunks.length > 0 && reviewChunks[reviewIndex]) {
      const c = reviewChunks[reviewIndex];
      setEditedUrdu(c.final_urdu || c.target_urdu || '');
    }
  }, [reviewIndex, reviewChunks]);

  const handleUploadFiles = async (files: FileList | File[]) => {
    if (!activeProject || files.length === 0) return;
    const pdfFiles = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfFiles.length === 0) {
      alert('Please select or drop valid Arabic .pdf files.');
      return;
    }

    setUploading(true);
    setUploadMsg(`Ingesting & classifying ${pdfFiles.length} PDF(s)...`);
    try {
      const res = await api.uploadPdfs(activeProject.id, pdfFiles);
      setUploadMsg(`✓ Successfully added ${res.uploaded.length} book(s) to project queue!`);
      await loadProjectData(activeProject.id);
      setTimeout(() => setUploadMsg(null), 4000);
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
      setUploadMsg(null);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!activeProject) return;
    if (!confirm('Are you sure you want to remove this PDF from the queue?')) return;
    try {
      await api.deleteDocument(activeProject.id, docId);
      await loadProjectData(activeProject.id);
    } catch (e: any) {
      alert(`Delete error: ${e.message}`);
    }
  };

  const handleClearQueue = async () => {
    if (!activeProject) return;
    if (!confirm('Are you sure you want to clear all documents from the translation queue?')) return;
    try {
      await api.clearProjectQueue(activeProject.id);
      await loadProjectData(activeProject.id);
    } catch (e: any) {
      alert(`Clear queue error: ${e.message}`);
    }
  };

  const handleToggleStartPause = async () => {
    if (!activeProject) return;
    try {
      if (projectStats?.is_running) {
        await api.pauseProject(activeProject.id);
      } else {
        await api.startProject(activeProject.id);
      }
      await loadProjectData(activeProject.id);
    } catch (e: any) {
      alert(`Toggle failed: ${e.message}`);
    }
  };

  const handleApproveCurrentChunk = async () => {
    if (reviewChunks.length === 0) return;
    const current = reviewChunks[reviewIndex];
    if (!current) return;

    setSavingReview(true);
    try {
      await api.approveChunk(current.id, editedUrdu.trim());
      // Update local state
      setReviewChunks((prev) =>
        prev.map((c, i) => (i === reviewIndex ? { ...c, status: 'approved', final_urdu: editedUrdu.trim() } : c))
      );
      if (reviewIndex < reviewChunks.length - 1) {
        setReviewIndex((prev) => prev + 1);
      } else {
        // Last chunk approved -> automatically advance to Export & Preview
        setCurrentStep(5);
      }
    } catch (e: any) {
      alert(`Approve error: ${e.message}`);
    } finally {
      setSavingReview(false);
    }
  };

  const currentReviewChunk = reviewChunks[reviewIndex];

  const [switchingModel, setSwitchingModel] = useState(false);
  const handleSwitchToInstalledNLLB = async () => {
    if (!activeProject) return;
    setSwitchingModel(true);
    try {
      const updated = await api.updateProjectModels(activeProject.id, {
        primary_model_id: 'nllb-200-distilled-1.3b',
        secondary_model_id: ''
      });
      onSelectProject(updated);
      await loadProjectData(activeProject.id);
    } catch (e: any) {
      alert(`Failed to switch model: ${e.message}`);
    } finally {
      setSwitchingModel(false);
    }
  };
  const isUsingUninstalledPrimary = !!activeProject && activeProject.primary_model_id !== 'nllb-200-distilled-1.3b' &&
    !deps?.readiness_matrix?.[activeProject.primary_model_id]?.ready;

  const [switchingMode, setSwitchingMode] = useState(false);
  const handleEnableContinuousMode = async () => {
    if (!activeProject) return;
    setSwitchingMode(true);
    try {
      const updated = await api.updateProjectModels(activeProject.id, { mode: 'hybrid' });
      onSelectProject(updated);
      await loadProjectData(activeProject.id);
    } catch (e: any) {
      alert(`Failed to switch mode: ${e.message}`);
    } finally {
      setSwitchingMode(false);
    }
  };
  const isReviewModeStepping = activeProject?.mode === 'review';

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      
      {/* Top Banner: Project Switcher & Arbiter Status */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-2xl">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white">Tarjuman Simple Mode</h2>
              <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded-full font-bold">
                100% Local
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Streamlined 5-step translation from Arabic PDF to Formatted Urdu Document.
            </p>
          </div>
        </div>

        {/* Engine Arbiter Provenance Badge */}
        <div className="flex items-center gap-3">
          {arbiter && (
            <div className="flex items-center gap-2 bg-slate-950 px-3.5 py-1.5 rounded-xl border border-slate-800 text-xs">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase">Active OCR:</span>
                  <span className="text-[11px] text-emerald-300 font-bold font-mono">{arbiter.ocr.label}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-slate-400 font-semibold uppercase">Translation:</span>
                  <span className="text-[11px] text-cyan-300 font-bold font-mono">{arbiter.translation.label}</span>
                </div>
              </div>
            </div>
          )}

          <button
            onClick={onSwitchToAdvanced}
            className="text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-750 px-3 py-1.5 rounded-xl border border-slate-700 font-medium transition-colors"
          >
            Switch to Advanced Workstation
          </button>
        </div>
      </div>

      {/* 5-Step Process Navigation Bar */}
      <div className="grid grid-cols-5 gap-2 bg-slate-900/80 p-1.5 rounded-2xl border border-slate-800 shadow-lg">
        {[
          { num: 1, title: '1. Upload PDF' },
          { num: 2, title: '2. Model Check' },
          { num: 3, title: '3. Run Translation' },
          { num: 4, title: '4. Proofread & Review' },
          { num: 5, title: '5. Export Urdu' }
        ].map((s) => (
          <button
            key={s.num}
            onClick={() => setCurrentStep(s.num)}
            className={`py-2.5 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
              currentStep === s.num
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <span>{s.title}</span>
          </button>
        ))}
      </div>

      {/* STEP 1: UPLOAD PDF */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files) handleUploadFiles(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`p-10 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center space-y-3 ${
              isDragging
                ? 'bg-indigo-950/60 border-indigo-400 text-indigo-200 scale-[1.01]'
                : 'bg-slate-900/60 hover:bg-slate-900 border-slate-800 hover:border-indigo-500/50 text-slate-400 shadow-xl'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => e.target.files && handleUploadFiles(e.target.files)}
              multiple
              accept=".pdf"
              className="hidden"
            />
            <div className="flex justify-center">
              <div className="p-4 rounded-2xl bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                <UploadCloud className={`w-8 h-8 ${uploading ? 'animate-bounce text-indigo-400' : ''}`} />
              </div>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">
                {uploading ? 'Analyzing and Ingesting PDF...' : isDragging ? 'Drop Arabic PDFs Here' : 'Drag & Drop Arabic PDF Books Here'}
              </h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                Supports printed text PDFs and scanned manuscripts. Automatic per-page text classification and Apple Vision/Qwen2-VL OCR.
              </p>
            </div>
            {uploadMsg && (
              <p className="text-xs font-mono font-bold text-emerald-400 mt-2 bg-emerald-950/50 border border-emerald-800/60 py-1.5 px-4 rounded-xl inline-block">
                {uploadMsg}
              </p>
            )}
          </div>

          {/* Uploaded Documents List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 shadow-xl">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                Active Document Queue ({documents.length} PDF books)
              </h4>
              {documents.length > 0 && (
                <button
                  onClick={handleClearQueue}
                  className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear Queue
                </button>
              )}
            </div>

            {documents.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No documents uploaded yet. Drop a PDF above to begin.
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {documents.map((doc) => (
                  <div key={doc.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-indigo-400" />
                      <div>
                        <p className="text-xs font-bold text-white">{doc.filename}</p>
                        <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono mt-0.5">
                          <span>{doc.total_pages} pages</span>
                          <span>•</span>
                          <span>{doc.total_chunks} chunks</span>
                          <span>•</span>
                          <span className={doc.is_scanned ? 'text-amber-400' : 'text-emerald-400'}>
                            {doc.is_scanned ? 'Scanned Book (OCR)' : 'Native Text'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                      title="Remove PDF from queue"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setCurrentStep(2)}
                disabled={documents.length === 0}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition-all shadow-md"
              >
                <span>Proceed to Model Check</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: MODEL CHECK & LOCAL READINESS */}
      {currentStep === 2 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Cpu className="w-5 h-5 text-indigo-400" />
              2. Local Engine Readiness & Hardware Status
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Verify your offline translation and OCR models before running. 100% on-device on Apple Silicon.
            </p>
          </div>

          {isUsingUninstalledPrimary && (
            <div className="bg-amber-950/40 border border-amber-800 rounded-xl p-4 flex items-center justify-between gap-4">
              <div className="text-xs text-amber-200">
                <span className="font-bold">This project's primary model (<code>{activeProject?.primary_model_id}</code>) isn't downloaded.</span>
                {' '}Translating will trigger a large first-time download, or silently fall back to a lower-quality engine.
                Switch to the already-installed <strong>Meta NLLB-200 1.3B</strong> instead?
              </div>
              <button
                onClick={handleSwitchToInstalledNLLB}
                disabled={switchingModel}
                className="flex items-center gap-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-xs font-bold px-3.5 py-2 rounded-lg whitespace-nowrap shadow-md"
              >
                {switchingModel ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>Use NLLB-200 1.3B</span>
              </button>
            </div>
          )}

          {isReviewModeStepping && (
            <div className="bg-cyan-950/40 border border-cyan-800 rounded-xl p-4 flex items-center justify-between gap-4">
              <div className="text-xs text-cyan-200">
                <span className="font-bold">This project is in "Review Mode"</span>
                {' '}— by design it translates <strong>one chunk at a time</strong> and stops, waiting for you to click "Resume" before continuing.
                This isn't a pause or a crash — it's the mode's intended behavior. Switch to <strong>Hybrid Mode</strong> for continuous, hands-off queue processing (still flags low-confidence chunks for review in Step 4).
              </div>
              <button
                onClick={handleEnableContinuousMode}
                disabled={switchingMode}
                className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-bold px-3.5 py-2 rounded-lg whitespace-nowrap shadow-md"
              >
                {switchingMode ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>Enable Continuous Translation</span>
              </button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* OCR Engine Card */}
            <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">Scanned Page OCR</span>
                <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded-full font-bold">
                  ✓ READY
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Primary: <strong>Qari-OCR-0.4.0 (MLX)</strong> with automatic fallback to <strong>Qwen2-VL / Apple Vision OCR</strong>.
              </p>
              <div className="text-[11px] font-mono text-slate-400 bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                Active Selection: {arbiter?.ocr.label || 'Apple Vision OCR'}
              </div>
            </div>

            {/* Translation Engine Card */}
            <div className="bg-slate-950 p-5 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">Arabic → Urdu Translation</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                  arbiter?.translation.ready
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}>
                  {arbiter?.translation.ready ? '✓ READY' : 'INSTALL REQUIRED'}
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Primary: <strong>Meta NLLB-200 1.3B</strong> (Direct ar → ur) | Fallback: <strong>Argos Translate</strong> (ar → en → ur).
              </p>
              <div className="text-[11px] font-mono text-slate-400 bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                Active Selection: {arbiter?.translation.label || 'Argos Translate'}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              onClick={() => setCurrentStep(1)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-4 py-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Upload</span>
            </button>

            <button
              onClick={() => {
                setCurrentStep(3);
                if (!projectStats?.is_running) handleToggleStartPause();
              }}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition-all shadow-md shadow-emerald-600/20"
            >
              <Play className="w-4 h-4" />
              <span>Start 1-Click Translation</span>
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: RUN TRANSLATION */}
      {currentStep === 3 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Play className="w-5 h-5 text-indigo-400" />
                3. Translation Queue Progress
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                {isReviewModeStepping
                  ? 'Review Mode: translates one chunk, then stops for your approval by design.'
                  : 'Continuous on-device execution with real-time memory safety throttling.'}
              </p>
            </div>

            <button
              onClick={handleToggleStartPause}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white transition-all shadow-md ${
                projectStats?.is_running
                  ? 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/20'
                  : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
              }`}
            >
              {projectStats?.is_running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>
                {projectStats?.is_running
                  ? 'Pause Translation'
                  : isReviewModeStepping
                  ? 'Translate Next Chunk'
                  : 'Resume Translation'}
              </span>
            </button>
          </div>

          {isReviewModeStepping && (
            <div className="bg-cyan-950/30 border border-cyan-900/50 rounded-lg px-3 py-2 text-[11px] text-cyan-300 flex items-center justify-between gap-3">
              <span>Stuck clicking through chunks one at a time? Switch to continuous processing in Step 2.</span>
              <button
                onClick={handleEnableContinuousMode}
                disabled={switchingMode}
                className="text-cyan-200 hover:text-white underline font-bold whitespace-nowrap"
              >
                {switchingMode ? 'Switching...' : 'Enable Continuous Mode'}
              </button>
            </div>
          )}

          {/* Progress Bar */}
          {projectStats && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
                <span className="flex items-center gap-2">
                  <span>Translation: {projectStats.translated_chunks ?? (projectStats.approved_chunks + projectStats.awaiting_review_chunks)} of {projectStats.total_chunks} chunks ({projectStats.progress_percentage ?? 0}%)</span>
                  {projectStats.is_running && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-bold bg-emerald-950/80 border border-emerald-800 px-2 py-0.5 rounded-full animate-pulse">
                      ● TRANSLATING
                    </span>
                  )}
                </span>
                <span>{projectStats.total_documents} PDF(s)</span>
              </div>
              <div className="w-full bg-slate-950 h-3.5 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="bg-indigo-600 h-full transition-all duration-500 rounded-full"
                  style={{ width: `${projectStats.progress_percentage ?? 0}%` }}
                />
              </div>
            </div>
          )}

          {/* 4 Stat Cards */}
          {projectStats && (
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Total Chunks</span>
                <p className="text-xl font-bold text-white mt-1">{projectStats.total_chunks}</p>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Approved</span>
                <p className="text-xl font-bold text-emerald-400 mt-1">{projectStats.approved_chunks}</p>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Awaiting Review</span>
                <p className="text-xl font-bold text-amber-400 mt-1">{projectStats.awaiting_review_chunks}</p>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Failed / Errors</span>
                <p className="text-xl font-bold text-rose-400 mt-1">{projectStats.failed_chunks}</p>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              onClick={() => setCurrentStep(2)}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-4 py-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>

            <button
              onClick={() => setCurrentStep(4)}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition-all shadow-md shadow-indigo-600/20"
            >
              <span>Review Translations</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: STREAMLINED REVIEW */}
      {currentStep === 4 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                4. Streamlined Proofreading & Review
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Review Arabic source chunks and refine Urdu output. Approved text updates Translation Memory automatically.
              </p>
            </div>

            {reviewChunks.length > 0 && (
              <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                <span>Chunk {reviewIndex + 1} of {reviewChunks.length}</span>
              </div>
            )}
          </div>

          {currentReviewChunk ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {/* Arabic Source */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-xs font-bold text-slate-400 uppercase">Arabic Source (Page {currentReviewChunk.page_number})</span>
                  <p className="text-lg font-arabic-text text-slate-100 leading-relaxed text-right pt-1">
                    {currentReviewChunk.source_text}
                  </p>
                </div>

                {/* Urdu Translation Editor */}
                <div className="bg-slate-950 p-4 rounded-xl border border-indigo-900/40 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-400 uppercase">Urdu Translation</span>
                    <span className="text-[10px] font-mono text-slate-400">
                      {currentReviewChunk.primary_model ? `by ${currentReviewChunk.primary_model}` : 'No model metadata'}
                    </span>
                  </div>
                  <textarea
                    value={editedUrdu}
                    onChange={(e) => setEditedUrdu(e.target.value)}
                    rows={6}
                    dir="rtl"
                    className="w-full bg-slate-900 p-3 rounded-lg border border-slate-700 text-emerald-300 font-urdu-body text-lg focus:outline-none focus:border-indigo-500 leading-relaxed text-right"
                  />
                  <div className="text-[11px] font-mono text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">Primary:</span>
                      <span className="text-emerald-300 font-bold">{currentReviewChunk.primary_model || 'Unknown'}</span>
                      <span className="text-slate-500">({currentReviewChunk.execution_backend || 'n/a'})</span>
                    </div>
                    {currentReviewChunk.secondary_model && (
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">Secondary:</span>
                        <span className="text-cyan-300">{currentReviewChunk.secondary_model}</span>
                      </div>
                    )}
                    {currentReviewChunk.review_model && (
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">Reviewer:</span>
                        <span className="text-indigo-300">{currentReviewChunk.review_model}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">OCR:</span>
                      <span className="text-amber-300">{currentReviewChunk.ocr_engine || 'Apple Vision OCR'}</span>
                      {currentReviewChunk.latency_ms != null && <span className="text-slate-500 ml-2">· {currentReviewChunk.latency_ms}ms</span>}
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setReviewIndex((prev) => Math.max(0, prev - 1))}
                    disabled={reviewIndex === 0}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-750 disabled:opacity-40 text-slate-300 text-xs font-bold rounded-lg border border-slate-700"
                  >
                    Previous Chunk
                  </button>
                  <button
                    onClick={() => setReviewIndex((prev) => Math.min(reviewChunks.length - 1, prev + 1))}
                    disabled={reviewIndex >= reviewChunks.length - 1}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-750 disabled:opacity-40 text-slate-300 text-xs font-bold rounded-lg border border-slate-700"
                  >
                    Skip to Next
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleApproveCurrentChunk}
                    disabled={savingReview || !editedUrdu.trim()}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold px-6 py-2.5 rounded-xl shadow-md shadow-emerald-600/20"
                  >
                    {savingReview ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    <span>Approve Translation (Next)</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 space-y-4">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
              <h4 className="text-base font-bold text-white">All Chunks Reviewed & Ready!</h4>
              <p className="text-xs text-slate-400">You can now proceed to export your formatted Urdu book.</p>
              <button
                onClick={() => setCurrentStep(5)}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md"
              >
                Proceed to Export
              </button>
            </div>
          )}
        </div>
      )}

      {/* STEP 5: 1-CLICK EXPORT */}
      {currentStep === 5 && activeProject && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Download className="w-5 h-5 text-indigo-400" />
              5. Export Formatted Urdu Output
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Download your complete translated book in your preferred format.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {/* Formatted Urdu PDF */}
            <a
              href={api.getPdfUrduExportUrl(activeProject.id)}
              download
              className="bg-slate-950 hover:bg-indigo-950/40 p-5 rounded-2xl border border-slate-800 hover:border-indigo-500/50 transition-all text-center space-y-3 group shadow-lg"
            >
              <div className="p-3 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-2xl w-fit mx-auto group-hover:scale-110 transition-transform">
                <Download className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Urdu Translated PDF</h4>
                <p className="text-[11px] text-slate-400 mt-1">Formatted RTL Urdu PDF with original page structure.</p>
              </div>
            </a>

            {/* Bilingual PDF */}
            <a
              href={api.getPdfBilingualExportUrl(activeProject.id, 'stacked')}
              download
              className="bg-slate-950 hover:bg-cyan-950/40 p-5 rounded-2xl border border-slate-800 hover:border-cyan-500/50 transition-all text-center space-y-3 group shadow-lg"
            >
              <div className="p-3 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-2xl w-fit mx-auto group-hover:scale-110 transition-transform">
                <Layers className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Bilingual Arabic-Urdu PDF</h4>
                <p className="text-[11px] text-slate-400 mt-1">Stacked Arabic source alongside Urdu translation.</p>
              </div>
            </a>

            {/* Word DOCX */}
            <a
              href={api.getDocxExportUrl(activeProject.id)}
              download
              className="bg-slate-950 hover:bg-blue-950/40 p-5 rounded-2xl border border-slate-800 hover:border-blue-500/50 transition-all text-center space-y-3 group shadow-lg"
            >
              <div className="p-3 bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-2xl w-fit mx-auto group-hover:scale-110 transition-transform">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Microsoft Word (.docx)</h4>
                <p className="text-[11px] text-slate-400 mt-1">Editable Word document with RTL Urdu typography.</p>
              </div>
            </a>
          </div>

          {/* Live Document Preview Viewer */}
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Eye className="w-4 h-4 text-indigo-400" />
                Live PDF Document Preview (Urdu Typeset)
              </h4>
              <div className="flex items-center gap-3">
                <a
                  href={api.getPdfUrduExportUrl(activeProject.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                >
                  Open in New Tab ↗
                </a>
              </div>
            </div>

            <div className="w-full h-[650px] rounded-xl overflow-hidden border border-slate-800 bg-slate-900 shadow-inner">
              <iframe
                src={`${api.getPdfUrduExportUrl(activeProject.id)}#toolbar=1&navpanes=0`}
                className="w-full h-full border-0"
                title="Live Urdu PDF Preview"
              />
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
