import React, { useState, useEffect, useRef } from 'react';
import {
  FolderPlus,
  Play,
  Pause,
  FileText,
  Download,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileCode,
  Layers,
  ArrowRight,
  UploadCloud,
  FolderOpen,
  Trash2,
  Eye,
  Copy,
  X,
  Cpu,
  ShieldCheck
} from 'lucide-react';
import { ProjectRecord, DocumentRecord, ModelCapability, SystemDependenciesResponse } from '../../types';
import { api } from '../../services/api';

interface DocumentQueueViewProps {
  activeProject: ProjectRecord | null;
  onSelectProject: (proj: ProjectRecord) => void;
  models: ModelCapability[];
  onOpenReview: () => void;
  onOpenBenchmark: () => void;
  onOpenWizard: () => void;
}

export const DocumentQueueView: React.FC<DocumentQueueViewProps> = ({
  activeProject,
  onSelectProject,
  models,
  onOpenReview,
  onOpenBenchmark,
  onOpenWizard
}) => {
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [projectStats, setProjectStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [deps, setDeps] = useState<SystemDependenciesResponse | null>(null);
  const [switchingModel, setSwitchingModel] = useState(false);

  // Drag & Drop / Upload State
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // New Project Form Modal State
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [mode, setMode] = useState<'review' | 'automatic' | 'hybrid'>('review');
  const [strategy, setStrategy] = useState<'local_only' | 'local_gemini_review' | 'gemini_primary' | 'compare'>('local_only');
  const [primaryModel, setPrimaryModel] = useState('nllb-200-distilled-1.3b');
  const [reviewerModel, setReviewerModel] = useState('qwen3:8b');
  const [customGeminiModel, setCustomGeminiModel] = useState('gemini-3.6-flash');

  const loadProjects = async () => {
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

  const handleUploadFiles = async (files: FileList | File[]) => {
    if (!activeProject || files.length === 0) return;
    const pdfFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfFiles.length === 0) {
      alert('Please select or drop valid .pdf files.');
      return;
    }

    setUploading(true);
    setUploadMsg(`Ingesting & extracting Arabic chunks from ${pdfFiles.length} PDF(s)...`);
    try {
      const res = await api.uploadPdfs(activeProject.id, pdfFiles);
      setUploadMsg(`✓ Successfully ingested ${res.uploaded.length} PDF(s)!`);
      await loadProjectDetails(activeProject.id);
      setTimeout(() => setUploadMsg(null), 4000);
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
      setUploadMsg(null);
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUploadFiles(e.dataTransfer.files);
    }
  };

  const loadProjectDetails = async (projId: string) => {
    setLoading(true);
    try {
      const details = await api.getProjectDetails(projId);
      setProjectStats(details.stats);
      const docs = await api.listProjectDocuments(projId);
      setDocuments(docs);
      const d = await api.getDependencies();
      setDeps(d);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleChangePrimaryModel = async (modelId: string) => {
    if (!activeProject || !modelId || modelId === activeProject.primary_model_id) return;
    setSwitchingModel(true);
    try {
      const updated = await api.updateProjectModels(activeProject.id, { primary_model_id: modelId });
      onSelectProject(updated);
    } catch (err: any) {
      alert(`Failed to switch model: ${err.message}`);
    } finally {
      setSwitchingModel(false);
    }
  };

  const handleChangePrivacy = async (mode: ProjectRecord['privacy_mode']) => {
    if (!activeProject || mode === activeProject.privacy_mode) return;
    try {
      const updated = await api.updateProjectModels(activeProject.id, { privacy_mode: mode });
      onSelectProject(updated);
    } catch (err: any) {
      alert(`Failed to update privacy: ${err.message}`);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (!activeProject) return;
    loadProjectDetails(activeProject.id);
    const interval = setInterval(() => {
      loadProjectDetails(activeProject.id);
    }, 3000);
    return () => clearInterval(interval);
  }, [activeProject?.id]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim() || !folderPath.trim()) return;

    try {
      const newProj = await api.createProject({
        name: projectName.trim(),
        folder_path: folderPath.trim(),
        mode,
        routing_strategy: strategy,
        primary_model_id: primaryModel,
        reviewer_model_id: reviewerModel,
        gemini_model_id: customGeminiModel || 'gemini-3.6-flash',
      });
      setShowNewProjectModal(false);
      setProjectName('');
      setFolderPath('');
      await loadProjects();
      onSelectProject(newProj);
    } catch (err: any) {
      alert(`Failed to create project: ${err.message}`);
    }
  };

  const [rescanning, setRescanning] = useState(false);

  // OCR Transcript Viewer Modal State
  const [transcriptDoc, setTranscriptDoc] = useState<DocumentRecord | null>(null);
  const [transcript, setTranscript] = useState<{ full_text: string; ocr_engines_used: string[]; chunks: any[] } | null>(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [transcriptCopied, setTranscriptCopied] = useState(false);

  const handleViewTranscript = async (doc: DocumentRecord) => {
    if (!activeProject) return;
    setTranscriptDoc(doc);
    setTranscript(null);
    setTranscriptLoading(true);
    try {
      const res = await api.getDocumentTranscript(activeProject.id, doc.id);
      setTranscript(res);
    } catch (err: any) {
      alert(`Failed to load transcript: ${err.message}`);
      setTranscriptDoc(null);
    } finally {
      setTranscriptLoading(false);
    }
  };

  const handleCopyTranscript = async () => {
    if (!transcript) return;
    try {
      await navigator.clipboard.writeText(transcript.full_text);
      setTranscriptCopied(true);
      setTimeout(() => setTranscriptCopied(false), 2000);
    } catch {
      alert('Could not copy to clipboard — select and copy the text manually.');
    }
  };

  const handleToggleStartPause = async () => {
    if (!activeProject) return;
    if (projectStats?.is_running) {
      await api.pauseProject(activeProject.id);
    } else {
      await api.startProject(activeProject.id);
    }
    loadProjectDetails(activeProject.id);
  };

  const handleRescan = async () => {
    if (!activeProject || rescanning) return;
    setRescanning(true);
    try {
      await api.rescanProject(activeProject.id);
      await loadProjectDetails(activeProject.id);
    } catch (err: any) {
      alert(`Failed to rescan folder: ${err.message}`);
    } finally {
      setRescanning(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!activeProject) return;
    if (!confirm('Are you sure you want to remove this PDF from the queue?')) return;
    try {
      await api.deleteDocument(activeProject.id, docId);
      await loadProjectDetails(activeProject.id);
    } catch (err: any) {
      alert(`Failed to delete document: ${err.message}`);
    }
  };

  const handleClearQueue = async () => {
    if (!activeProject) return;
    if (!confirm('Are you sure you want to clear all documents and chunks from this queue?')) return;
    try {
      await api.clearProjectQueue(activeProject.id);
      await loadProjectDetails(activeProject.id);
    } catch (err: any) {
      alert(`Failed to clear queue: ${err.message}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      
      {/* Top Action Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            Batch Document Queue
          </h2>
          <p className="text-xs text-slate-400">
            Scan folders of Arabic PDFs, track chunk processing, and manage bulk translation jobs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {projects.length > 0 && (
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5">
              <FolderOpen className="w-4 h-4 text-indigo-400" />
              <select
                value={activeProject?.id || ''}
                onChange={(e) => {
                  const p = projects.find(x => x.id === e.target.value);
                  if (p) onSelectProject(p);
                }}
                className="bg-transparent text-xs text-white font-medium focus:outline-none cursor-pointer"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-slate-900 text-white">
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => setShowNewProjectModal(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition-colors shadow-lg shadow-indigo-600/20"
          >
            <FolderPlus className="w-4 h-4" />
            <span>New Translation Project</span>
          </button>
        </div>
      </div>

      {/* Benchmark before large-scale translation banner */}
      <div className="bg-gradient-to-r from-indigo-950/70 via-slate-900 to-indigo-950/70 border border-indigo-500/30 rounded-2xl p-4 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/30 text-indigo-300 rounded-xl border border-indigo-400/30">
            <Layers className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white flex items-center gap-2">
              <span>Benchmark Before Large-Scale Translation</span>
              <span className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 px-2 py-0.5 rounded font-mono">Recommended</span>
            </h4>
            <p className="text-[11px] text-slate-300 mt-0.5">
              Empirically evaluate MADLAD-400, NLLB-200, Qwen3 8B, and Gemini on your specific Arabic text before processing thousands of pages.
            </p>
          </div>
        </div>
        <button
          onClick={onOpenBenchmark}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-1.5 whitespace-nowrap"
        >
          <span>Open Benchmark Suite</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Active Project Card */}
      {activeProject ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-bold text-white">{activeProject.name}</h3>
                <span className="text-[11px] bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded-full font-mono">
                  Mode: {activeProject.mode.toUpperCase()}
                </span>
                <span className="text-[11px] bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded-full font-mono">
                  Route: {activeProject.routing_strategy.replace('_', ' ').toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">{activeProject.folder_path}</p>
            </div>

            {/* Queue Controls & Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleRescan}
                disabled={rescanning}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors shadow-sm"
                title="Rescan folder for added or removed PDF files"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${rescanning ? 'animate-spin' : ''}`} />
                <span>{rescanning ? 'Rescanning...' : 'Rescan Folder'}</span>
              </button>
              <button
                onClick={handleToggleStartPause}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all shadow-md ${
                  projectStats?.is_running
                    ? 'bg-amber-600 hover:bg-amber-500 shadow-amber-600/20'
                    : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
                }`}
              >
                {projectStats?.is_running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                <span>{projectStats?.is_running ? 'Pause Queue' : 'Start Translation'}</span>
              </button>

              <button
                onClick={onOpenReview}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-colors"
              >
                <span>Open Review Workstation</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              {/* PDF & Document Exports */}
              <div className="flex items-center gap-1.5 border-l border-slate-800 pl-2">
                <a
                  href={api.getPdfUrduExportUrl(activeProject.id)}
                  download
                  className="flex items-center gap-1 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-600/20"
                  title="Export Translated Urdu PDF (Mode A)"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Urdu PDF</span>
                </a>

                <div className="relative group">
                  <button
                    className="flex items-center gap-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-slate-700"
                    title="Additional PDF Export Formats"
                  >
                    <span>More PDF</span>
                  </button>
                  <div className="absolute right-0 mt-2 w-48 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-1 hidden group-hover:block z-20">
                    <a
                      href={api.getPdfBilingualExportUrl(activeProject.id, 'stacked')}
                      download
                      className="block px-3 py-1.5 hover:bg-slate-800 rounded-lg text-[11px] text-slate-200"
                    >
                      Bilingual (Stacked Layout)
                    </a>
                    <a
                      href={api.getPdfBilingualExportUrl(activeProject.id, 'side_by_side')}
                      download
                      className="block px-3 py-1.5 hover:bg-slate-800 rounded-lg text-[11px] text-slate-200"
                    >
                      Bilingual (Side-by-Side)
                    </a>
                    <a
                      href={api.getPdfTrilingualExportUrl(activeProject.id)}
                      download
                      className="block px-3 py-1.5 hover:bg-slate-800 rounded-lg text-[11px] text-slate-200"
                    >
                      Trilingual (English Ref)
                    </a>
                    <a
                      href={api.getPdfReviewExportUrl(activeProject.id)}
                      download
                      className="block px-3 py-1.5 hover:bg-slate-800 rounded-lg text-[11px] text-cyan-300 font-semibold"
                    >
                      Proofreading Review Sheet
                    </a>
                  </div>
                </div>

                <a
                  href={api.getDocxExportUrl(activeProject.id)}
                  download
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs border border-slate-700"
                  title="Export to Microsoft Word (.docx) with Urdu RTL"
                >
                  <FileText className="w-3.5 h-3.5 text-blue-400" />
                </a>
                <a
                  href={api.getTxtExportUrl(activeProject.id, true)}
                  download
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs border border-slate-700"
                  title="Export Bilingual Plain Text (.txt)"
                >
                  <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                </a>
                <a
                  href={api.getJsonExportUrl(activeProject.id)}
                  download
                  className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs border border-slate-700"
                  title="Export Structured JSON Dataset"
                >
                  <Download className="w-3.5 h-3.5 text-amber-400" />
                </a>
              </div>
            </div>
          </div>

          {/* Translation Model Readiness / Selector — check before starting a large run */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center gap-3">
            <Cpu className="w-4 h-4 text-indigo-400 shrink-0" />
            <span className="text-xs text-slate-400 shrink-0">Translation Model:</span>
            <select
              value={activeProject.primary_model_id}
              onChange={(e) => handleChangePrimaryModel(e.target.value)}
              disabled={switchingModel}
              className="bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-slate-100 font-mono disabled:opacity-50"
            >
              {models.filter((m) => m.translation_capable).map((m) => {
                const ready = deps?.readiness_matrix?.[m.model_id]?.ready;
                const isPublicOrCloud = m.provider_class === 'PUBLIC_WEB' || m.provider_class === 'CLOUD_AI';
                const blocked = isPublicOrCloud && activeProject.privacy_mode === 'LOCAL_ONLY';
                const ramNote = m.minimum_recommended_ram_gb > 16 ? ` (${m.minimum_recommended_ram_gb}GB+ RAM)` : '';
                return (
                  <option key={m.model_id} value={m.model_id} disabled={blocked}>
                    {ready ? '✓ ' : '○ '}{m.display_name}{ramNote}{ready ? '' : ' (not downloaded)'}{blocked ? ' — blocked (Local Only)' : ''}
                  </option>
                );
              })}
            </select>

            {deps?.readiness_matrix?.[activeProject.primary_model_id] && (
              deps.readiness_matrix[activeProject.primary_model_id].ready ? (
                <span className="text-[11px] text-emerald-400 font-mono">✓ Ready</span>
              ) : (
                <div className="flex items-center gap-2 text-[11px] text-amber-300">
                  <span>{deps.readiness_matrix[activeProject.primary_model_id].reason}</span>
                  <button
                    onClick={onOpenWizard}
                    className="bg-amber-600 hover:bg-amber-500 text-white font-bold px-2.5 py-1 rounded-lg whitespace-nowrap"
                  >
                    Download in Setup Wizard
                  </button>
                </div>
              )
            )}

            <div className="flex items-center gap-1.5 ml-auto">
              <ShieldCheck className="w-4 h-4 text-slate-500" />
              <span className="text-xs text-slate-400">Privacy</span>
              <select
                value={activeProject.privacy_mode || 'LOCAL_ONLY'}
                onChange={(e) => handleChangePrivacy(e.target.value as ProjectRecord['privacy_mode'])}
                className="bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-slate-100 font-mono"
                title="Project privacy mode: which model types are allowed for translation"
              >
                <option value="LOCAL_ONLY">Local Only</option>
                <option value="LOCAL_AND_CLOUD">Local + Gemini Cloud</option>
                <option value="ALLOW_PUBLIC_WEB">Allow Public Web (Google)</option>
              </select>
            </div>
          </div>

          {/* Drag & Drop PDF Dropzone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`p-6 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center space-y-2 ${
              isDragging
                ? 'bg-indigo-950/60 border-indigo-400 text-indigo-200 scale-[1.01]'
                : 'bg-slate-950/60 hover:bg-slate-950 border-slate-800 hover:border-indigo-500/50 text-slate-400'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleUploadFiles(e.target.files);
                }
              }}
              multiple
              accept=".pdf"
              className="hidden"
            />
            <div className="flex justify-center">
              <div className={`p-3 rounded-2xl border transition-colors ${
                isDragging ? 'bg-indigo-600/30 text-indigo-300 border-indigo-400' : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}>
                <UploadCloud className={`w-6 h-6 ${uploading ? 'animate-bounce text-indigo-400' : ''}`} />
              </div>
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">
                {uploading ? 'Ingesting PDF & Extracting Arabic Chunks...' : isDragging ? 'Drop Arabic PDF Files Here' : 'Drag & Drop Arabic PDF files here, or click to browse'}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Supports text PDFs & scanned books with automatic Apple Vision OCR. Multiple files supported.
              </p>
            </div>
            {uploadMsg && (
              <p className="text-xs font-mono font-bold text-emerald-400 mt-2 bg-emerald-950/50 border border-emerald-800/60 py-1.5 px-3 rounded-lg inline-block">
                {uploadMsg}
              </p>
            )}
          </div>

          {/* Progress Counters */}
          {projectStats && (
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Total Documents</span>
                <p className="text-xl font-bold text-white mt-1">{projectStats.total_documents} PDFs</p>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Total Chunks</span>
                <p className="text-xl font-bold text-slate-200 mt-1">{projectStats.total_chunks}</p>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Approved Translations</span>
                <p className="text-xl font-bold text-emerald-400 mt-1">{projectStats.approved_chunks}</p>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Awaiting Review</span>
                <p className="text-xl font-bold text-amber-400 mt-1">{projectStats.awaiting_review_chunks}</p>
              </div>
            </div>
          )}

          {/* Document Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">PDF Document Queue</h4>
              {documents.length > 0 && (
                <button
                  onClick={handleClearQueue}
                  className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear Entire Queue
                </button>
              )}
            </div>
            
            {documents.length === 0 ? (
              <div className="bg-slate-950/50 p-8 rounded-xl border border-dashed border-slate-800 text-center text-xs text-slate-500">
                No PDF files ingested yet. Check that the folder contains .pdf files.
              </div>
            ) : (
              <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3">PDF Filename</th>
                      <th className="p-3">Pages</th>
                      <th className="p-3">Chunks</th>
                      <th className="p-3">Type</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850">
                    {documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-900/50 transition-colors">
                        <td className="p-3 font-medium text-white flex items-center gap-2">
                          <FileText className="w-4 h-4 text-slate-400" />
                          {doc.filename}
                        </td>
                        <td className="p-3">{doc.total_pages} pages</td>
                        <td className="p-3">
                          {doc.completed_chunks} / {doc.total_chunks}
                        </td>
                        <td className="p-3">
                          <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${doc.is_scanned ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'bg-slate-800 text-slate-300'}`}>
                            {doc.is_scanned ? 'Scanned (OCR)' : 'Text PDF'}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                            doc.status === 'completed'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}>
                            {doc.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleViewTranscript(doc)}
                              disabled={doc.total_chunks === 0}
                              className="flex items-center gap-1 px-2 py-1.5 text-slate-400 hover:text-indigo-300 hover:bg-slate-850 rounded-lg transition-colors text-[11px] font-medium disabled:opacity-30 disabled:cursor-not-allowed"
                              title="View extracted/OCR'd Arabic transcription (no translation required)"
                            >
                              <Eye className="w-4 h-4" />
                              <span>Transcript</span>
                            </button>
                            <button
                              onClick={() => handleDeleteDocument(doc.id)}
                              className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-slate-850 rounded-lg transition-colors"
                              title="Delete PDF from queue"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      ) : (
        <div className="bg-slate-900 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <FolderPlus className="w-10 h-10 text-indigo-400 mx-auto" />
          <h3 className="text-base font-bold text-white">No Project Selected</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Create a new translation project and point it to a folder containing your Arabic PDF collection.
          </p>
          <button
            onClick={() => setShowNewProjectModal(true)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition-colors"
          >
            Create New Project
          </button>
        </div>
      )}

      {/* OCR Transcript Viewer Modal */}
      {transcriptDoc && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] shadow-2xl flex flex-col">
            <div className="flex items-start justify-between p-5 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Eye className="w-4 h-4 text-indigo-400" />
                  Extracted Transcription — {transcriptDoc.filename}
                </h3>
                {transcript && (
                  <p className="text-[11px] text-slate-400 mt-1">
                    OCR engine{transcript.ocr_engines_used.length !== 1 ? 's' : ''} used:{' '}
                    <span className="font-mono text-indigo-300">
                      {transcript.ocr_engines_used.length > 0 ? transcript.ocr_engines_used.join(', ') : 'N/A (native text PDF, no OCR needed)'}
                    </span>
                    {' '}· {transcript.chunks.length} chunk(s)
                  </p>
                )}
              </div>
              <button
                onClick={() => { setTranscriptDoc(null); setTranscript(null); }}
                className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5">
              {transcriptLoading ? (
                <div className="text-xs text-slate-400 text-center py-10">Loading transcription...</div>
              ) : transcript && transcript.full_text ? (
                <p dir="rtl" lang="ar" className="text-sm text-slate-100 leading-relaxed whitespace-pre-wrap font-arabic">
                  {transcript.full_text}
                </p>
              ) : (
                <div className="text-xs text-slate-500 text-center py-10">
                  No transcription available yet — this document may still be processing.
                </div>
              )}
            </div>

            {transcript && transcript.full_text && (
              <div className="flex items-center justify-end gap-2 p-4 border-t border-slate-800">
                <button
                  onClick={handleCopyTranscript}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>{transcriptCopied ? 'Copied!' : 'Copy Text'}</span>
                </button>
                <a
                  href={api.getDocumentTranscriptDownloadUrl(activeProject!.id, transcriptDoc.id)}
                  download
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download .txt</span>
                </a>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateProject}
            className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 space-y-4"
          >
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FolderPlus className="w-5 h-5 text-indigo-400" />
              New Translation Project
            </h3>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Project Name</label>
              <input
                type="text"
                required
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. Fiqh & Hadith Library Volume 1"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">Folder Path containing Arabic PDFs</label>
              <input
                type="text"
                required
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                placeholder="/Users/username/Books/Arabic_PDFs"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Translation Mode</label>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100"
                >
                  <option value="review">Review Mode (Step-by-step)</option>
                  <option value="automatic">Automatic Mode (Unattended)</option>
                  <option value="hybrid">Hybrid Mode (QA threshold)</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Routing Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value as any)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100"
                >
                  <option value="local_only">Local Only (✓ Zero Cloud)</option>
                  <option value="local_gemini_review">Local + Gemini Review</option>
                  <option value="gemini_primary">Gemini Primary (Cloud)</option>
                  <option value="compare">Compare Mode</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Primary Translator</label>
                <select
                  value={primaryModel}
                  onChange={(e) => setPrimaryModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                >
                  {models.filter((m) => m.translation_capable).map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.display_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Reviewer Model</label>
                <select
                  value={reviewerModel}
                  onChange={(e) => setReviewerModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                >
                  {models.filter((m) => m.review_capable).map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.display_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {strategy !== 'local_only' && (
              <div>
                <label className="text-xs text-slate-400 block mb-1">Configurable Gemini Cloud Model</label>
                <input
                  type="text"
                  value={customGeminiModel}
                  onChange={(e) => setCustomGeminiModel(e.target.value)}
                  placeholder="e.g. gemini-2.5-flash, gemini-2.5-pro"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 font-mono"
                />
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowNewProjectModal(false)}
                className="px-4 py-2 bg-slate-800 text-slate-300 text-xs rounded-xl hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md"
              >
                Create Project & Scan
              </button>
            </div>
          </form>
        </div>
      )}

    </div>
  );
};
