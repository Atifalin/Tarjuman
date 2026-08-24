import React, { useState, useEffect } from 'react';
import { Cpu, HardDrive, Zap, Activity, ShieldAlert, CheckCircle, AlertTriangle } from 'lucide-react';
import { HardwareMetrics, ThrottlePolicy, GeminiQuotaResponse } from '../../types';
import { api } from '../../services/api';

interface HardwareMonitorBarProps {
  metrics: HardwareMetrics | null;
  throttle: ThrottlePolicy | null;
  activeModelName?: string;
  chunksPerMin?: number;
}

export const HardwareMonitorBar: React.FC<HardwareMonitorBarProps> = ({
  metrics,
  throttle,
  activeModelName,
  chunksPerMin = 0
}) => {
  const [geminiQuota, setGeminiQuota] = useState<GeminiQuotaResponse | null>(null);

  useEffect(() => {
    const fetchQuota = async () => {
      try {
        const q = await api.getGeminiQuota();
        setGeminiQuota(q);
      } catch (e) {
        console.debug(e);
      }
    };
    fetchQuota();
    const interval = setInterval(fetchQuota, 8000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) {
    return (
      <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-2 text-xs text-slate-400 flex items-center justify-between">
        <span>Loading hardware telemetry...</span>
      </div>
    );
  }

  const pressureColors = {
    GREEN: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    YELLOW: 'bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse',
    RED: 'bg-rose-500/20 text-rose-400 border-rose-500/30 animate-bounce',
    UNKNOWN: 'bg-slate-800 text-slate-400 border-slate-700'
  };

  const pressureIcons = {
    GREEN: <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />,
    YELLOW: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
    RED: <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />,
    UNKNOWN: null
  };

  return (
    <div className="bg-slate-900/95 border-b border-slate-800/80 px-6 py-2 text-xs text-slate-300 flex flex-wrap items-center justify-between gap-4">
      
      {/* Left Chip and Profile */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 font-medium text-slate-200">
          <Cpu className="w-4 h-4 text-indigo-400" />
          <span>{metrics.chip_name}</span>
          <span className="text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-1.5 py-0.5 rounded font-mono">
            {metrics.hardware_profile.replace('_', ' ')}
          </span>
        </div>

        {/* Unified Memory & Pressure */}
        <div className="flex items-center gap-2 border-l border-slate-800 pl-4">
          <span className="text-slate-400">RAM:</span>
          <span className="font-semibold text-slate-100">
            {metrics.used_ram_gb} / {metrics.total_ram_gb} GB ({metrics.ram_percent}%)
          </span>
          <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                metrics.ram_percent > 85
                  ? 'bg-rose-500'
                  : metrics.ram_percent > 70
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${metrics.ram_percent}%` }}
            />
          </div>
          <span
            className={`flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded border ${
              pressureColors[metrics.memory_pressure]
            }`}
          >
            {pressureIcons[metrics.memory_pressure]}
            {metrics.memory_pressure}
          </span>
        </div>

        {/* CPU */}
        <div className="flex items-center gap-1.5 border-l border-slate-800 pl-4">
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">CPU:</span>
          <span className="font-semibold text-slate-100">{metrics.cpu_percent}%</span>
        </div>
      </div>

      {/* Right Metrics: Disk, Active Model, Translation Throughput */}
      <div className="flex items-center gap-4">
        {/* Storage */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <HardDrive className="w-3.5 h-3.5 text-slate-400" />
          <span>Disk Free:</span>
          <span className="font-medium text-slate-200">{metrics.disk_free_gb} GB</span>
        </div>

        {/* Active Model */}
        {activeModelName && (
          <div className="flex items-center gap-1.5 border-l border-slate-800 pl-4">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">Model:</span>
            <span className="font-medium text-emerald-300 font-mono text-[11px]">{activeModelName}</span>
          </div>
        )}

        {/* Speed */}
        <div className="flex items-center gap-1.5 border-l border-slate-800 pl-4">
          <span className="text-slate-400">Throughput:</span>
          <span className="font-bold text-indigo-300">{chunksPerMin.toFixed(1)} chunks/min</span>
        </div>

        {/* Gemini Free Tier Daily Quota Guard */}
        {geminiQuota?.tiers?.flash && (
          <div className="flex items-center gap-1.5 border-l border-slate-800 pl-4" title="Google Cloud Free Tier Caps (per GCP project): Flash: 10 RPM / 250 RPD; Flash-Lite: 15 RPM / 1000 RPD; Pro: 2 RPM / 50 RPD">
            <span className="text-slate-400">Cloud Quota:</span>
            <span className={`font-mono text-[11px] font-bold px-1.5 py-0.5 rounded border ${
              geminiQuota.tiers.flash.is_exhausted
                ? 'bg-rose-950 text-rose-300 border-rose-800 animate-pulse'
                : geminiQuota.tiers.flash.is_approaching_limit
                ? 'bg-amber-950 text-amber-300 border-amber-800'
                : 'bg-indigo-950 text-indigo-300 border-indigo-800'
            }`}>
              {geminiQuota.tiers.flash.rpd_used} / {geminiQuota.tiers.flash.rpd_cap} RPD ({geminiQuota.tiers.flash.rpm_active}/{geminiQuota.tiers.flash.rpm_cap} RPM)
            </span>
          </div>
        )}
      </div>

    </div>
  );
};
