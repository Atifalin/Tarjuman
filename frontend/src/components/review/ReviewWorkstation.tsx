import React, { useState, useEffect } from 'react';
import {
  Check,
  RotateCw,
  Sparkles,
  X,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Edit3,
  Cpu,
  Layers,
  Save,
  Clock,
  Zap,
  Download,
  RotateCcw,
  FileText,
  BookOpen
} from 'lucide-react';
import { ProjectRecord, ChunkRecord, ModelCapability } from '../../types';
import { api } from '../../services/api';

interface ReviewWorkstationProps {
  activeProject: ProjectRecord | null;
  models: ModelCapability[];
}

export const ReviewWorkstation: React.FC<ReviewWorkstationProps> = ({
  activeProject,
  models
}) => {
  const [currentChunk, setCurrentChunk] = useState<ChunkRecord | null>(null);
  const [editedUrdu, setEditedUrdu] = useState('');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [saveToTm, setSaveToTm] = useState(true);
  const [selectedRegenModel, setSelectedRegenModel] = useState('');
  const [showEnglishRef, setShowEnglishRef] = useState(false);
  const [englishModel, setEnglishModel] = useState('qwen3:8b');
  const [fetchingEnglish, setFetchingEnglish] = useState(false);
  const [allProjectChunks, setAllProjectChunks] = useState<ChunkRecord[]>([]);
  const [resettingStatus, setResettingStatus] = useState(false);

  const loadAllChunks = async () => {
    if (!activeProject) return;
    try {
      const chunks = await api.listProjectChunks(activeProject.id);
      setAllProjectChunks(chunks);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFetchEnglish = async () => {
    if (!currentChunk || fetchingEnglish) return;
    setFetchingEnglish(true);
    try {
      const res = await api.fetchEnglishReference(currentChunk.id, englishModel);
      setCurrentChunk(res.chunk);
    } catch (e: any) {
      alert(`English reference error: ${e.message}`);
    } finally {
      setFetchingEnglish(false);
    }
  };

  const loadNextChunk = async () => {
    if (!activeProject) return;
    setLoading(true);
    try {
      const res = await api.getNextReviewChunk(activeProject.id);
      setCurrentChunk(res.chunk);
      if (res.chunk) {
        setEditedUrdu(res.chunk.final_urdu || res.chunk.target_urdu || '');
      } else {
        await loadAllChunks();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleResetReviewStatus = async (targetStatus: string) => {
    if (!activeProject) return;
    setResettingStatus(true);
    try {
      await api.resetProjectReviewStatus(activeProject.id, targetStatus);
      await loadNextChunk();
    } catch (e: any) {
      alert(`Reset error: ${e.message}`);
    } finally {
      setResettingStatus(false);
    }
  };

  useEffect(() => {
    loadNextChunk();
  }, [activeProject?.id]);

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts if user is typing in textarea or input
      const target = e.target as HTMLElement;
      if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
          e.preventDefault();
          handleApprove();
        }
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        handleApprove();
      } else if (e.key.toLowerCase() === 'r') {
        e.preventDefault();
        handleRegenerate();
      } else if (e.key.toLowerCase() === 'g') {
        e.preventDefault();
        handleGeminiReview();
      } else if (e.key.toLowerCase() === 'x') {
        e.preventDefault();
        handleReject();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentChunk?.id, editedUrdu, saveToTm]);

  const handleApprove = async () => {
    if (!currentChunk || actionLoading) return;
    setActionLoading(true);
    try {
      await api.approveChunk(currentChunk.id, editedUrdu, saveToTm);
      await loadNextChunk();
    } catch (e: any) {
      alert(`Approval error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!currentChunk || actionLoading) return;
    setActionLoading(true);
    try {
      await api.rejectChunk(currentChunk.id);
      await loadNextChunk();
    } catch (e: any) {
      alert(`Reject error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (!currentChunk || actionLoading) return;
    setActionLoading(true);
    try {
      const res = await api.regenerateChunk(currentChunk.id, selectedRegenModel || undefined);
      setCurrentChunk(res.chunk);
      setEditedUrdu(res.chunk.final_urdu || res.chunk.target_urdu || '');
    } catch (e: any) {
      setCurrentChunk(prev => prev ? {
        ...prev,
        status: 'failed',
        qa_status: 'FAILED',
        qa_issues: [e.message || 'Translation failed']
      } : null);
    } finally {
      setActionLoading(false);
    }
  };

  const handleGeminiReview = async () => {
    if (!currentChunk || actionLoading) return;
    setActionLoading(true);
    try {
      const res = await api.geminiReviewChunk(currentChunk.id);
      setCurrentChunk(res.chunk);
      setEditedUrdu(res.chunk.final_urdu || '');
    } catch (e: any) {
      alert(`Gemini review error: ${e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (!activeProject) {
    return (
      <div className="max-w-7xl mx-auto p-12 text-center text-slate-400">
        Please select or create a project from the Document Queue first.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-12 text-center text-slate-400">
        Loading next review chunk...
      </div>
    );
  }

  if (!currentChunk) {
    return (
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Top Status Header */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center space-y-4 shadow-xl">
          <div className="p-3 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded-2xl w-fit mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">All Chunks Reviewed & Approved!</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              All document chunks in <strong className="text-white">{activeProject.name}</strong> have been proofread and saved to Translation Memory.
            </p>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={() => handleResetReviewStatus('awaiting_review')}
              disabled={resettingStatus}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-bold px-4 py-2.5 rounded-xl border border-slate-700 transition-colors shadow-sm"
            >
              <RotateCcw className="w-4 h-4 text-indigo-400" />
              <span>Re-Open All Chunks for Review</span>
            </button>

            <button
              onClick={() => handleResetReviewStatus('pending')}
              disabled={resettingStatus}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-bold px-4 py-2.5 rounded-xl border border-slate-700 transition-colors shadow-sm"
            >
              <RotateCw className="w-4 h-4 text-amber-400" />
              <span>Re-Translate All Chunks</span>
            </button>

            <button
              onClick={loadNextChunk}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-md transition-colors"
            >
              <Zap className="w-4 h-4" />
              <span>Refresh Workstation</span>
            </button>
          </div>
        </div>

        {/* 1-Click Export Center */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Download className="w-4 h-4 text-indigo-400" />
            1-Click Document Export Center
          </h4>
          <div className="grid grid-cols-3 gap-4">
            <a
              href={api.getPdfUrduExportUrl(activeProject.id)}
              download
              className="bg-slate-950 hover:bg-indigo-950/40 p-4 rounded-xl border border-slate-800 hover:border-indigo-500/50 transition-all text-center space-y-2 group"
            >
              <Download className="w-5 h-5 text-indigo-400 mx-auto group-hover:scale-110 transition-transform" />
              <h5 className="text-xs font-bold text-white">Urdu Translated PDF</h5>
              <p className="text-[10px] text-slate-400">Formatted RTL PDF with original page geometry.</p>
            </a>

            <a
              href={api.getPdfBilingualExportUrl(activeProject.id, 'stacked')}
              download
              className="bg-slate-950 hover:bg-cyan-950/40 p-4 rounded-xl border border-slate-800 hover:border-cyan-500/50 transition-all text-center space-y-2 group"
            >
              <Layers className="w-5 h-5 text-cyan-400 mx-auto group-hover:scale-110 transition-transform" />
              <h5 className="text-xs font-bold text-white">Bilingual PDF (Stacked)</h5>
              <p className="text-[10px] text-slate-400">Side-by-side Arabic source and Urdu translation.</p>
            </a>

            <a
              href={api.getDocxExportUrl(activeProject.id)}
              download
              className="bg-slate-950 hover:bg-blue-950/40 p-4 rounded-xl border border-slate-800 hover:border-blue-500/50 transition-all text-center space-y-2 group"
            >
              <FileText className="w-5 h-5 text-blue-400 mx-auto group-hover:scale-110 transition-transform" />
              <h5 className="text-xs font-bold text-white">Microsoft Word (.docx)</h5>
              <p className="text-[10px] text-slate-400">Editable Word document with RTL typography.</p>
            </a>
          </div>
        </div>

        {/* Chunk Navigator / Browser */}
        {allProjectChunks.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" />
                Project Chunk Browser ({allProjectChunks.length} Chunks)
              </h4>
              <span className="text-[11px] text-slate-400 font-mono">Click any chunk to re-edit in workstation</span>
            </div>

            <div className="grid grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
              {allProjectChunks.map((chunk) => (
                <div
                  key={chunk.id}
                  onClick={() => {
                    setCurrentChunk(chunk);
                    setEditedUrdu(chunk.final_urdu || chunk.target_urdu || '');
                  }}
                  className="bg-slate-950 hover:bg-slate-850 p-3 rounded-xl border border-slate-800 hover:border-indigo-500/50 cursor-pointer transition-all space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-indigo-300 font-mono">
                      Page {chunk.page_number} • Chunk #{chunk.chunk_index}
                    </span>
                    <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase ${
                      chunk.status === 'approved' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {chunk.status}
                    </span>
                  </div>
                  <p className="text-xs font-urdu-body text-emerald-300 truncate text-right" dir="rtl">
                    {chunk.final_urdu || chunk.target_urdu || 'No translation'}
                  </p>
                  <p className="text-[11px] text-slate-400 font-arabic truncate text-right" dir="rtl">
                    {chunk.source_text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  const qaBadgeColors: Record<string, string> = {
    PASS: 'bg-emerald-950 text-emerald-300 border-emerald-800',
    WARNING: 'bg-amber-950 text-amber-300 border-amber-800',
    REVIEW_REQUIRED: 'bg-rose-950 text-rose-300 border-rose-800',
    FAILED: 'bg-rose-950 text-rose-200 border-rose-700 animate-pulse',
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-4">
      
      {/* Chunk Header & Provenance */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-lg">
        
        {/* Left: Document & Page ID */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-xl">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white">Page {currentChunk.page_number}</span>
              <span className="text-xs text-slate-400 font-mono">Chunk #{currentChunk.chunk_index}</span>
            </div>
            <p className="text-xs text-slate-400 font-mono">{currentChunk.id}</p>
          </div>
        </div>

        {/* Center: Model & Route Provenance */}
        <div className="flex flex-wrap items-center gap-2 text-xs bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
          <Cpu className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-400">Primary:</span>
          <span className="font-semibold text-slate-200 font-mono text-[11px]">{currentChunk.primary_model || 'Local MT'}</span>
          
          {currentChunk.route && (
            <>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400">Route:</span>
              <span className="font-semibold text-cyan-300 font-mono text-[11px]">{currentChunk.route}</span>
            </>
          )}

          {currentChunk.review_model && (
            <>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400">Reviewer:</span>
              <span className="font-semibold text-emerald-300 font-mono text-[11px]">{currentChunk.review_model}</span>
            </>
          )}

          {currentChunk.latency_ms && (
            <span className="text-[10px] text-slate-500 font-mono pl-1">
              ({currentChunk.latency_ms} ms)
            </span>
          )}
        </div>

        {/* Right: English Ref Toggle & QA Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowEnglishRef(!showEnglishRef)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
              showEnglishRef
                ? 'bg-cyan-950/80 text-cyan-300 border-cyan-700 shadow-md shadow-cyan-950/50'
                : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-750'
            }`}
          >
            <span>🇬🇧 English Reference</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${showEnglishRef ? 'bg-cyan-800 text-white' : 'bg-slate-700 text-slate-400'}`}>
              {showEnglishRef ? 'ON' : 'OFF'}
            </span>
          </button>

          {currentChunk.qa_status && (
            <span className={`text-xs font-bold px-2.5 py-1 rounded-lg border flex items-center gap-1.5 ${qaBadgeColors[currentChunk.qa_status] || qaBadgeColors.PASS}`}>
              {currentChunk.qa_status === 'PASS' ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              )}
              QA: {currentChunk.qa_status}
            </span>
          )}
        </div>

      </div>

      {/* QA Warning Drawer if issues found */}
      {currentChunk.qa_issues && currentChunk.qa_issues.length > 0 && (
        <div className="bg-amber-950/40 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-200 space-y-1">
          <div className="font-bold flex items-center gap-1.5 text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Deterministic QA Signals:
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-200/90 pl-1 text-[11px]">
            {currentChunk.qa_issues.map((iss, i) => (
              <li key={i}>{iss}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Dynamic 2-Panel or 3-Panel Grid Layout */}
      <div className={`grid gap-6 ${showEnglishRef ? 'grid-cols-3' : 'grid-cols-2'}`}>
        
        {/* PANEL 1: ARABIC ORIGINAL */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Arabic Source</span>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">Original RTL</span>
            </div>
            <span className="text-xs text-slate-400 font-mono">{currentChunk.source_text.split(' ').length} words</span>
          </div>

          <div className="flex-1 overflow-y-auto bg-slate-950 p-5 rounded-xl border border-slate-800/80">
            <p className="font-arabic-text text-xl text-slate-100 selection:bg-indigo-600">
              {currentChunk.source_text}
            </p>
          </div>
        </div>

        {/* PANEL 2: ENGLISH REFERENCE (COLLAPSIBLE / TOGGLEABLE) */}
        {showEnglishRef && (
          <div className="bg-slate-900 border border-cyan-900/60 rounded-2xl p-6 flex flex-col space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider">English Reference</span>
                  <span className="text-[10px] bg-cyan-950 text-cyan-400 border border-cyan-800 px-1.5 py-0.5 rounded font-mono">Scholarly LTR</span>
                </div>
                <p className="text-[10px] text-slate-500 pt-0.5">For review/reference only — Arabic source remains authoritative.</p>
              </div>
            </div>

            <div className="flex-1 flex flex-col justify-between overflow-y-auto bg-slate-950 p-5 rounded-xl border border-slate-800/80 space-y-3">
              {currentChunk.english_reference ? (
                <div>
                  <p className="text-sm text-slate-200 leading-relaxed font-sans">
                    {currentChunk.english_reference}
                  </p>
                  {currentChunk.english_reference_route && (
                    <p className="text-[10px] text-cyan-400 font-mono pt-3 border-t border-slate-850 mt-3">
                      Generated via {currentChunk.english_reference_route}
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4 space-y-3">
                  <p className="text-xs text-slate-400 max-w-xs">
                    No English reference generated yet for this chunk.
                  </p>
                  <div className="flex items-center gap-2">
                    <select
                      value={englishModel}
                      onChange={(e) => setEnglishModel(e.target.value)}
                      className="bg-slate-900 border border-slate-700 text-slate-200 text-xs px-2.5 py-1.5 rounded-lg"
                    >
                      <option value="qwen3:8b">Qwen3 8B (Local)</option>
                      <option value="argos-translate">Argos Translate (ar_en)</option>
                      <option value="google-web-unofficial">Google Web (Unofficial)</option>
                      <option value="gemini-3.6-flash">Gemini 3.6 Flash (Cloud)</option>
                    </select>
                    <button
                      onClick={handleFetchEnglish}
                      disabled={fetchingEnglish}
                      className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-md shadow-cyan-600/20"
                    >
                      {fetchingEnglish ? 'Generating...' : 'Fetch English'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* PANEL 3: URDU TRANSLATION EDITOR */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Urdu Translation</span>
              <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 px-1.5 py-0.5 rounded font-mono">Nastaliq RTL</span>
            </div>
            <span className="text-xs text-slate-400 font-mono">{editedUrdu.split(' ').filter(Boolean).length} words</span>
          </div>

          <div className="flex-1 flex flex-col relative">
            {!editedUrdu && currentChunk.status === 'failed' && (
              <div className="absolute inset-0 bg-slate-950/95 backdrop-blur-xs rounded-xl flex flex-col items-center justify-center p-6 text-center z-10 border border-rose-900/60 space-y-3">
                <div className="p-3 bg-rose-600/20 text-rose-400 border border-rose-500/30 rounded-2xl">
                  <ShieldAlert className="w-7 h-7 animate-pulse text-rose-400" />
                </div>
                <div className="max-w-md space-y-1">
                  <h4 className="text-sm font-bold text-rose-200">Translation Attempt Failed</h4>
                  <p className="text-xs text-rose-300/90 font-mono bg-rose-950/60 p-2 rounded-lg border border-rose-900/80 break-words max-h-24 overflow-y-auto">
                    {currentChunk.qa_issues?.[0] || 'Unknown inference error. Check backend logs or API credentials.'}
                  </p>
                  <p className="text-[11px] text-slate-400 pt-1">
                    You can type the Urdu translation manually below, or click retry to try another engine.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRegenerate}
                    disabled={actionLoading}
                    className="flex items-center gap-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-rose-600/20 transition-all"
                  >
                    <RotateCw className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} />
                    <span>{actionLoading ? 'Retrying...' : 'Retry Translation [R]'}</span>
                  </button>
                  <button
                    onClick={() => setEditedUrdu(' ')}
                    className="px-3 py-2 text-xs text-slate-400 hover:text-slate-200 border border-slate-700 rounded-xl"
                  >
                    Write Manually
                  </button>
                </div>
              </div>
            )}

            {!editedUrdu && currentChunk.status === 'pending' && (
              <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-xs rounded-xl flex flex-col items-center justify-center p-6 text-center z-10 border border-slate-850 space-y-3">
                <div className="p-3 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-2xl">
                  <Zap className="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Pending Translation</h4>
                  <p className="text-xs text-slate-400 max-w-sm mt-1">
                    This Arabic passage has been extracted from the PDF. Click below or press <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-300 font-mono">R</kbd> to generate the Urdu translation.
                  </p>
                </div>
                <button
                  onClick={handleRegenerate}
                  disabled={actionLoading}
                  className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
                >
                  <RotateCw className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} />
                  <span>{actionLoading ? 'Translating Passage...' : 'Translate Passage Now [R]'}</span>
                </button>
              </div>
            )}

            <textarea
              value={editedUrdu}
              onChange={(e) => setEditedUrdu(e.target.value)}
              className="w-full flex-1 min-h-[220px] bg-slate-950 p-5 rounded-xl border border-slate-700 text-slate-100 font-urdu-text text-2xl focus:outline-none focus:border-indigo-500 resize-none shadow-inner"
              placeholder="اردو ترجمہ یہاں درج کریں..."
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={saveToTm}
                onChange={(e) => setSaveToTm(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
              />
              <span>Save approved sentence to Translation Memory</span>
            </label>

            <span className="text-[11px] text-slate-500 font-mono">Press ⌘+Enter to Approve</span>
          </div>
        </div>

      </div>

      {/* Action Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        
        {/* Left: Secondary / Gemini on demand */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleGeminiReview}
            disabled={actionLoading}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 text-xs px-3.5 py-2 rounded-xl font-medium transition-colors"
            title="Send this chunk to Google Gemini for deep scholarly review"
          >
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Gemini Review [G]</span>
          </button>

          <button
            onClick={handleRegenerate}
            disabled={actionLoading}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3.5 py-2 rounded-xl font-medium transition-colors border border-slate-700"
            title="Re-translate using local engine"
          >
            <RotateCw className={`w-4 h-4 text-indigo-400 ${actionLoading ? 'animate-spin' : ''}`} />
            <span>Regenerate [R]</span>
          </button>
        </div>

        {/* Right: Approve & Reject Primary Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleReject}
            disabled={actionLoading}
            className="flex items-center gap-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs px-4 py-2.5 rounded-xl font-bold transition-colors"
          >
            <X className="w-4 h-4" />
            <span>Reject [X]</span>
          </button>

          <button
            onClick={handleApprove}
            disabled={actionLoading || !editedUrdu.trim()}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-emerald-600/20"
          >
            <Check className="w-4 h-4" />
            <span>Approve & Next [Enter]</span>
          </button>
        </div>

      </div>

    </div>
  );
};
