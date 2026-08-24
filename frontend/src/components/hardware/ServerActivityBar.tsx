import React from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  FileSearch,
  PauseCircle,
  RefreshCw,
  Settings,
  Sparkles,
  Zap
} from 'lucide-react';
import { ServerActivity } from '../../types';

interface ServerActivityBarProps {
  activity: ServerActivity | null;
  onOpenSettings?: () => void;
}

export const ServerActivityBar: React.FC<ServerActivityBarProps> = ({
  activity,
  onOpenSettings
}) => {
  const currentStatus = activity?.status || 'IDLE';
  const message = activity?.activity_message || 'Server idle — ready for translation.';
  const lastError = activity?.last_error;

  const statusConfig = {
    IDLE: {
      bg: 'bg-slate-900/90 border-slate-800/80 text-slate-400',
      badge: 'bg-slate-800 text-slate-400 border-slate-700',
      icon: <Activity className="w-3.5 h-3.5 text-slate-500" />,
      label: 'IDLE'
    },
    INGESTING: {
      bg: 'bg-indigo-950/80 border-indigo-800/60 text-indigo-200',
      badge: 'bg-indigo-900 text-indigo-300 border-indigo-700',
      icon: <RefreshCw className="w-3.5 h-3.5 text-indigo-400 animate-spin" />,
      label: 'SCANNING FOLDER'
    },
    OCR_PROCESSING: {
      bg: 'bg-amber-950/80 border-amber-800/60 text-amber-200',
      badge: 'bg-amber-900 text-amber-300 border-amber-700',
      icon: <FileSearch className="w-3.5 h-3.5 text-amber-400 animate-pulse" />,
      label: 'APPLE VISION OCR'
    },
    TRANSLATING: {
      bg: 'bg-blue-950/80 border-blue-800/60 text-blue-100',
      badge: 'bg-blue-900 text-blue-300 border-blue-700',
      icon: <Zap className="w-3.5 h-3.5 text-blue-400 animate-pulse" />,
      label: 'TRANSLATING'
    },
    REVIEWING: {
      bg: 'bg-purple-950/80 border-purple-800/60 text-purple-200',
      badge: 'bg-purple-900 text-purple-300 border-purple-700',
      icon: <Sparkles className="w-3.5 h-3.5 text-purple-400" />,
      label: 'AWAITING REVIEW'
    },
    COMPLETED: {
      bg: 'bg-emerald-950/80 border-emerald-800/60 text-emerald-200',
      badge: 'bg-emerald-900 text-emerald-300 border-emerald-700',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
      label: 'COMPLETED'
    },
    PAUSED: {
      bg: 'bg-slate-900/90 border-slate-800 text-amber-300',
      badge: 'bg-amber-950 text-amber-400 border-amber-800',
      icon: <PauseCircle className="w-3.5 h-3.5 text-amber-400" />,
      label: 'PAUSED'
    },
    ERROR: {
      bg: 'bg-rose-950/90 border-rose-700 text-rose-100 shadow-md shadow-rose-950/50',
      badge: 'bg-rose-900 text-rose-200 border-rose-600 animate-pulse',
      icon: <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />,
      label: 'PROCESS FAILED'
    }
  };

  const config = statusConfig[currentStatus] || statusConfig.IDLE;

  return (
    <div className={`w-full border-b transition-all duration-300 px-6 py-1.5 text-xs flex items-center justify-between gap-4 ${config.bg}`}>
      
      {/* Left: Status Badge & Live Process Message */}
      <div className="flex items-center gap-3 overflow-hidden">
        <span className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] font-bold border tracking-wider uppercase shrink-0 ${config.badge}`}>
          {config.icon}
          <span>{config.label}</span>
        </span>

        <span className={`font-medium truncate ${currentStatus === 'ERROR' ? 'font-semibold text-rose-100' : 'text-slate-200'}`}>
          {message}
        </span>
      </div>

      {/* Right: File/Chunk Meta and Action Button */}
      <div className="flex items-center gap-3 shrink-0">
        {activity?.current_file && (
          <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
            File: <strong className="text-slate-200">{activity.current_file}</strong>
          </span>
        )}

        {activity?.current_chunk && (
          <span className="text-[11px] text-slate-400 font-mono hidden md:inline">
            Passage: <strong className="text-slate-200">{activity.current_chunk}</strong>
          </span>
        )}

        {currentStatus === 'ERROR' && onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-[11px] font-bold transition-colors shadow-xs"
          >
            <Settings className="w-3 h-3" />
            <span>Check API Key / Routing</span>
          </button>
        )}
      </div>

    </div>
  );
};
