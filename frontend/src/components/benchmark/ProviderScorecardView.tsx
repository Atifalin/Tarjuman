import React, { useState, useEffect } from 'react';
import {
  Award,
  Zap,
  HardDrive,
  Shield,
  Scale,
  RefreshCw,
  Play,
  CheckCircle2,
  AlertTriangle,
  Info,
  Layers,
  Cpu
} from 'lucide-react';
import { api } from '../../services/api';
import {
  ProviderScorecard,
  PolicyRecommendationsResponse,
  ProjectRecord
} from '../../types';

interface ProviderScorecardViewProps {
  activeProject: ProjectRecord | null;
  onNavigateToBenchmark?: () => void;
}

export const ProviderScorecardView: React.FC<ProviderScorecardViewProps> = ({
  activeProject,
  onNavigateToBenchmark
}) => {
  const [data, setData] = useState<PolicyRecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [qualityTarget, setQualityTarget] = useState<number>(4.0);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.getPolicyRecommendations(
        qualityTarget,
        activeProject?.privacy_mode || 'LOCAL_ONLY'
      );
      setData(res);
    } catch (e) {
      console.error('Failed to load scorecard recommendations:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [qualityTarget, activeProject?.privacy_mode]);

  const classBadge = (pClass: string) => {
    switch (pClass) {
      case 'LOCAL_MT':
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
      case 'LOCAL_AI':
        return 'bg-purple-950/80 text-purple-300 border-purple-800';
      case 'APPLE_LOCAL':
        return 'bg-blue-950/80 text-blue-300 border-blue-800';
      case 'CLOUD_AI':
        return 'bg-amber-950/80 text-amber-300 border-amber-800';
      case 'PUBLIC_WEB':
        return 'bg-rose-950/80 text-rose-300 border-rose-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const privacyBadge = (priv: string) => {
    switch (priv) {
      case 'OFFLINE':
        return 'bg-emerald-950 text-emerald-400 border-emerald-800';
      case 'APPLE_LOCAL':
        return 'bg-blue-950 text-blue-400 border-blue-800';
      case 'CLOUD_USER_ENABLED':
        return 'bg-amber-950 text-amber-400 border-amber-800';
      case 'PUBLIC_WEB_USER_ENABLED':
        return 'bg-rose-950 text-rose-400 border-rose-800';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-xl">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Provider Performance Scorecard & Adaptive Routing</h2>
              <p className="text-xs text-slate-400">
                Empirical benchmark data drives production engine selection. No static rankings.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-xs">
            <span className="text-slate-400">Quality Target:</span>
            <select
              value={qualityTarget}
              onChange={(e) => setQualityTarget(parseFloat(e.target.value))}
              className="bg-slate-900 border border-slate-700 text-white font-bold px-2 py-0.5 rounded text-xs"
            >
              <option value="3.5">3.5 / 5.0 (Moderate)</option>
              <option value="4.0">4.0 / 5.0 (High Standard)</option>
              <option value="4.5">4.5 / 5.0 (Scholarly Strict)</option>
            </select>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-xl text-xs font-semibold border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          {onNavigateToBenchmark && (
            <button
              onClick={onNavigateToBenchmark}
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-md shadow-indigo-600/20"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Run Benchmark Suite
            </button>
          )}
        </div>
      </div>

      {/* 5 Evidence-Based Recommendations */}
      {data?.has_benchmark_data ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          
          {/* 1. Best Quality */}
          {data.recommendations.best_quality && (
            <div className="bg-slate-900 border border-indigo-900/60 rounded-2xl p-4 flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2">
                  <Award className="w-4 h-4" />
                  Best Quality
                </div>
                <h3 className="text-sm font-bold text-white">{data.recommendations.best_quality.provider_name}</h3>
                <p className="text-[11px] text-indigo-300 font-mono pt-1">
                  Quality: {data.recommendations.best_quality.score}/5.0
                </p>
                <p className="text-xs text-slate-400 pt-2 leading-relaxed">
                  {data.recommendations.best_quality.reason}
                </p>
              </div>
            </div>
          )}

          {/* 2. Fastest Verified */}
          {data.recommendations.fastest_verified && (
            <div className="bg-slate-900 border border-cyan-900/60 rounded-2xl p-4 flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold uppercase tracking-wider mb-2">
                  <Zap className="w-4 h-4" />
                  Fastest Verified
                </div>
                <h3 className="text-sm font-bold text-white">{data.recommendations.fastest_verified.provider_name}</h3>
                <p className="text-[11px] text-cyan-300 font-mono pt-1">
                  Latency: {data.recommendations.fastest_verified.latency_ms} ms/chunk
                </p>
                <p className="text-xs text-slate-400 pt-2 leading-relaxed">
                  {data.recommendations.fastest_verified.reason}
                </p>
              </div>
            </div>
          )}

          {/* 3. Lowest Memory */}
          {data.recommendations.lowest_memory && (
            <div className="bg-slate-900 border border-emerald-900/60 rounded-2xl p-4 flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-2">
                  <HardDrive className="w-4 h-4" />
                  Lowest Memory
                </div>
                <h3 className="text-sm font-bold text-white">{data.recommendations.lowest_memory.provider_name}</h3>
                <p className="text-[11px] text-emerald-300 font-mono pt-1">
                  Peak RAM: {data.recommendations.lowest_memory.peak_ram_mb} MB
                </p>
                <p className="text-xs text-slate-400 pt-2 leading-relaxed">
                  {data.recommendations.lowest_memory.reason}
                </p>
              </div>
            </div>
          )}

          {/* 4. Best Offline Local */}
          {data.recommendations.best_local && (
            <div className="bg-slate-900 border border-purple-900/60 rounded-2xl p-4 flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center gap-2 text-purple-400 text-xs font-bold uppercase tracking-wider mb-2">
                  <Shield className="w-4 h-4" />
                  Best Offline Local
                </div>
                <h3 className="text-sm font-bold text-white">{data.recommendations.best_local.provider_name}</h3>
                <p className="text-[11px] text-purple-300 font-mono pt-1">
                  Score: {data.recommendations.best_local.score}/5.0
                </p>
                <p className="text-xs text-slate-400 pt-2 leading-relaxed">
                  {data.recommendations.best_local.reason}
                </p>
              </div>
            </div>
          )}

          {/* 5. Best Balanced */}
          {data.recommendations.best_balanced && (
            <div className="bg-slate-900 border border-amber-900/60 rounded-2xl p-4 flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider mb-2">
                  <Scale className="w-4 h-4" />
                  Best Balanced
                </div>
                <h3 className="text-sm font-bold text-white">{data.recommendations.best_balanced.provider_name}</h3>
                <p className="text-[11px] text-amber-300 font-mono pt-1">
                  Quality: {data.recommendations.best_balanced.score}/5 | {data.recommendations.best_balanced.latency_ms}ms
                </p>
                <p className="text-xs text-slate-400 pt-2 leading-relaxed">
                  {data.recommendations.best_balanced.reason}
                </p>
              </div>
            </div>
          )}

        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-4 shadow-xl">
          <div className="p-3 bg-amber-600/20 text-amber-400 border border-amber-500/30 rounded-2xl inline-flex">
            <Info className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">NO BENCHMARK DATA COLLECTED YET</h3>
            <p className="text-xs text-slate-400 max-w-lg mx-auto mt-1">
              Tarjuman refuses to make assumptions or ship hard-coded model rankings. Run the benchmark suite on representative passages from your corpus to populate measured metrics and unlock evidence-backed recommendations.
            </p>
          </div>
          {onNavigateToBenchmark && (
            <button
              onClick={onNavigateToBenchmark}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/20 transition-all inline-flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Run Benchmark Suite Now</span>
            </button>
          )}
        </div>
      )}

      {/* Complete Metrics Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">All Translation Engines & Empirical Measurements</h3>
          <span className="text-xs text-slate-400 font-mono">5 Provider Classes</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
              <tr>
                <th className="py-3 px-4">Provider / Model</th>
                <th className="py-3 px-3">Class</th>
                <th className="py-3 px-3">Privacy</th>
                <th className="py-3 px-3">Route</th>
                <th className="py-3 px-3">Quality</th>
                <th className="py-3 px-3">Meaning</th>
                <th className="py-3 px-3">Fluency</th>
                <th className="py-3 px-3">Speed</th>
                <th className="py-3 px-3">RAM</th>
                <th className="py-3 px-3">Sample (n)</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {data?.scorecards?.map((s) => (
                <tr key={s.provider_id} className="hover:bg-slate-850/50 transition-colors">
                  <td className="py-3 px-4">
                    <span className="font-bold text-white block">{s.provider_name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{s.provider_id}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${classBadge(s.provider_class)}`}>
                      {s.provider_class}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${privacyBadge(s.privacy_class)}`}>
                      {s.privacy_class}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="text-[11px] text-slate-300 font-mono">
                      {s.route}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono font-bold">
                    {s.quality_score !== undefined && s.quality_score !== null ? (
                      <span className={s.quality_score >= 4.0 ? 'text-emerald-400' : 'text-amber-400'}>
                        {s.quality_score} / 5.0
                      </span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">
                    {s.meaning_score ? `${s.meaning_score}/5` : '—'}
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">
                    {s.naturalness_score ? `${s.naturalness_score}/5` : '—'}
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">
                    {s.latency_ms ? `${s.latency_ms} ms` : '—'}
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">
                    {s.peak_ram_mb ? `${(s.peak_ram_mb / 1024).toFixed(1)} GB` : '—'}
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-400">
                    {s.sample_count > 0 ? `n=${s.sample_count}` : '0'}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        s.availability_status === 'VERIFIED'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : s.availability_status === 'FAILED'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}
                    >
                      {s.availability_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
