'use client';

import { useState } from 'react';
import {
  Film,
  Search,
  CheckCircle2,
  XCircle,
  Play,
  Check,
  X,
  ShieldCheck,
  Eye,
  Download,
  Sparkles,
  Cpu,
  Layers
} from 'lucide-react';

export default function ClipsView({
  clips = [],
  fixtures = [],
  onClipDecision,
  actionLoading,
  setActiveView,
  setEditingClip,
  handleTriggerRender,
  selectedPresetByClip = {},
  setSelectedPresetByClip
}) {
  const [sourceTab, setSourceTab] = useState('real'); // 'real' or 'fixtures'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'pending', 'approved', 'rejected'
  const [typeFilter, setTypeFilter] = useState('all'); // 'all', 'tight', 'extended', 'split', 'reaction'
  const [recommendedOnly, setRecommendedOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('score_desc');

  const baseList = sourceTab === 'real' ? clips : fixtures;

  // Filter & Search logic matching master
  const filteredClips = baseList.filter((clip) => {
    if (recommendedOnly && !clip.is_recommended) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const titleMatch = (clip.title || '').toLowerCase().includes(q);
      const vodMatch = (clip.vod || '').toLowerCase().includes(q);
      const idMatch = (clip.id || '').toLowerCase().includes(q);
      if (!titleMatch && !vodMatch && !idMatch) return false;
    }

    const isApproved = clip.status === 'APPROVED';
    const isRejected = clip.status === 'REJECTED';
    const isPending = !isApproved && !isRejected;

    if (statusFilter === 'pending' && !isPending) return false;
    if (statusFilter === 'approved' && !isApproved) return false;
    if (statusFilter === 'rejected' && !isRejected) return false;

    if (typeFilter === 'tight' && clip.variant !== 'tight') return false;
    if (typeFilter === 'extended' && clip.variant !== 'extended') return false;
    if (typeFilter === 'split' && clip.layout_mode !== 'SPLIT') return false;
    if (typeFilter === 'reaction' && !clip.audio_reaction) return false;

    return true;
  });

  // Sorting matching master
  const sortedClips = [...filteredClips].sort((a, b) => {
    if (sortBy === 'score_desc') {
      const sa = parseFloat(String(a.score || '0').split('/')[0]) || 0;
      const sb = parseFloat(String(b.score || '0').split('/')[0]) || 0;
      return sb - sa;
    }
    if (sortBy === 'newest') {
      const da = a.created_at ? new Date(a.created_at).getTime() : 0;
      const db = b.created_at ? new Date(b.created_at).getTime() : 0;
      return db - da;
    }
    if (sortBy === 'shortest') {
      const da = parseFloat(a.duration) || 0;
      const db = parseFloat(b.duration) || 0;
      return da - db;
    }
    if (sortBy === 'longest') {
      const da = parseFloat(a.duration) || 0;
      const db = parseFloat(b.duration) || 0;
      return da - db;
    }
    return 0;
  });

  const pendingCount = baseList.filter((c) => c.status !== 'APPROVED' && c.status !== 'REJECTED').length;
  const approvedCount = baseList.filter((c) => c.status === 'APPROVED').length;
  const rejectedCount = baseList.filter((c) => c.status === 'REJECTED').length;

  const handlePresetChange = (clipId, preset) => {
    if (setSelectedPresetByClip) {
      setSelectedPresetByClip((prev) => ({ ...prev, [clipId]: preset }));
    }
  };

  return (
    <div className="space-y-5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#293245]">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Review Queue & Generated Clips</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Human operator review station (P1-P5): Inspect 9:16 vertical cuts, verify subtitles, queue platform renders, or launch CapCut Studio Editor.
          </p>
        </div>

        {/* Source Switcher */}
        <div className="flex items-center bg-[#1a1e2b] p-0.5 rounded-md border border-[#293245] shrink-0">
          <button
            onClick={() => setSourceTab('real')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              sourceTab === 'real'
                ? 'bg-[#293245] text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Rendered Media ({clips.length})</span>
          </button>

          <button
            onClick={() => setSourceTab('fixtures')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              sourceTab === 'fixtures'
                ? 'bg-[#293245] text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Demo Fixtures ({fixtures.length})</span>
          </button>
        </div>
      </div>

      {/* Toolbar with Filters (from master) */}
      <div className="p-3.5 rounded-lg bg-[#1a1e2b] border border-[#293245] flex flex-col gap-3">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          {/* Search */}
          <div className="relative w-full md:w-64">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              name="search_clips"
              autoComplete="off"
              placeholder="Search title, VOD, or clip ID…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#aab9c7]"
            />
          </div>

          {/* Status Filters */}
          <div className="flex items-center gap-1.5 flex-wrap w-full md:w-auto">
            {[
              { id: 'all', label: 'All', count: baseList.length },
              { id: 'pending', label: 'Pending', count: pendingCount },
              { id: 'approved', label: 'Approved', count: approvedCount },
              { id: 'rejected', label: 'Rejected', count: rejectedCount }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors tabular-nums ${
                  statusFilter === tab.id
                    ? 'bg-[#293245] text-white border border-[#4c5e6b]'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <span>{tab.label}</span>{' '}
                <span className="text-[10px] text-slate-500">({tab.count})</span>
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2 shrink-0 w-full md:w-auto justify-end text-xs">
            <span className="text-slate-400">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-2.5 py-1 rounded bg-[#13151f] border border-[#293245] text-xs text-slate-300 focus:outline-none"
            >
              <option value="score_desc">Highest Score</option>
              <option value="newest">Newest First</option>
              <option value="shortest">Shortest Duration</option>
              <option value="longest">Longest Duration</option>
            </select>
          </div>
        </div>

        {/* P1 Variant Filters & P2 Recommended Toggle (from master) */}
        <div className="pt-2.5 border-t border-[#293245] flex items-center justify-between gap-3 flex-wrap text-xs">
          <div className="flex items-center gap-1 flex-wrap">
            <span className="text-slate-500 text-[11px] mr-1">Variants:</span>
            {[
              { id: 'all', label: 'All Variants' },
              { id: 'tight', label: 'Tight Cut (≤45s)' },
              { id: 'extended', label: 'Extended (90s+)' },
              { id: 'split', label: 'Split Layout' },
              { id: 'reaction', label: 'Audio Reaction' }
            ].map((vf) => (
              <button
                key={vf.id}
                onClick={() => setTypeFilter(vf.id)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  typeFilter === vf.id
                    ? 'bg-[#252b3d] text-blue-300 border border-blue-500/40'
                    : 'bg-[#13151f] text-slate-400 hover:text-slate-200 border border-[#293245]'
                }`}
              >
                {vf.label}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={recommendedOnly}
              onChange={(e) => setRecommendedOnly(e.target.checked)}
              className="rounded accent-[#aab9c7]"
            />
            <span className="text-[11px] font-medium">★ Recommended Only</span>
          </label>
        </div>
      </div>

      {/* Grid of 9:16 Clips */}
      {sortedClips.length === 0 ? (
        <div className="py-16 text-center rounded-lg bg-[#1a1e2b] border border-[#293245] p-6 space-y-3">
          <div className="text-sm font-semibold text-white">No Clips Found</div>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {searchQuery || statusFilter !== 'all' || typeFilter !== 'all' || recommendedOnly
              ? 'No clips match your active filters.'
              : 'No clips have been generated in this collection yet.'}
          </p>
          <button
            onClick={() => setActiveView('generate')}
            className="px-3.5 py-1.5 rounded bg-[#aab9c7] hover:bg-[#e9ecee] text-white text-xs font-medium transition-colors"
          >
            Generate New Clips
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {sortedClips.map((clip) => {
            const isApproved = clip.status === 'APPROVED';
            const isRejected = clip.status === 'REJECTED';
            const isWaiting = !isApproved && !isRejected;
            const loadingAction = actionLoading[clip.id];
            const currentPreset = selectedPresetByClip[clip.id] || 'tiktok';

            return (
              <div
                key={clip.id}
                className="rounded-lg bg-[#1a1e2b] border border-[#293245] hover:border-[#4c5e6b] overflow-hidden transition-colors flex flex-col"
              >
                {/* 9:16 Container */}
                <div className="relative aspect-[9/16] bg-black overflow-hidden flex items-center justify-center">
                  {clip.media_url ? (
                    <video
                      src={clip.media_url}
                      preload="metadata"
                      controls
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-center p-4 space-y-2">
                      <div className="w-10 h-10 rounded-full bg-[#1e2333] border border-[#4c5e6b] flex items-center justify-center mx-auto text-slate-400">
                        <Play className="w-5 h-5 ml-0.5" />
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 block">
                        9:16 PREVIEW
                      </span>
                    </div>
                  )}

                  {/* Score Tag Top Left */}
                  <div className="absolute top-2.5 left-2.5 z-10 flex flex-col gap-1 items-start">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-black/80 text-slate-200 border border-[#4c5e6b] tabular-nums">
                      Score: {clip.score || '90/100'}
                    </span>
                    {clip.is_recommended && (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-amber-950/90 text-amber-300 border border-amber-800">
                        ★ RECOMMENDED
                      </span>
                    )}
                  </div>

                  {/* Status Overlay Top Right */}
                  <div className="absolute top-2.5 right-2.5 z-10">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${
                        isApproved
                          ? 'bg-emerald-950/90 text-emerald-300 border-emerald-800'
                          : isRejected
                          ? 'bg-rose-950/90 text-rose-300 border-rose-800'
                          : 'bg-amber-950/90 text-amber-300 border-amber-800'
                      }`}
                    >
                      {clip.status || 'PENDING'}
                    </span>
                  </div>

                  {/* Duration Bottom Right */}
                  <div className="absolute bottom-2.5 right-2.5 z-10">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-black/90 text-slate-300 tabular-nums">
                      {clip.duration || '20s'}
                    </span>
                  </div>
                </div>

                {/* Card Meta & Actions */}
                <div className="p-3 flex-1 flex flex-col justify-between space-y-2.5">
                  <div>
                    <h3 className="text-xs font-semibold text-white line-clamp-2 leading-snug">
                      {clip.title || `Clip #${clip.id}`}
                    </h3>
                    <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                      {clip.vod || 'Source VOD'}
                    </p>

                    {/* P1 & P2 Intelligence tags (from master) */}
                    <div className="flex items-center gap-1 flex-wrap mt-2 text-[9px] font-mono">
                      {clip.variant && (
                        <span className="px-1 py-0.2 rounded bg-[#1e2333] text-slate-300 border border-[#4c5e6b] uppercase">
                          {clip.variant}
                        </span>
                      )}
                      {clip.layout_mode === 'SPLIT' && (
                        <span className="px-1 py-0.2 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/40">
                          SPLIT
                        </span>
                      )}
                      {clip.audio_reaction && (
                        <span className="px-1 py-0.2 rounded bg-purple-950/60 text-purple-300 border border-purple-800/40 uppercase">
                          {clip.audio_reaction}
                        </span>
                      )}
                      {clip.hook_classification && (
                        <span className="px-1 py-0.2 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                          HOOK
                        </span>
                      )}
                    </div>
                  </div>

                  {/* P4 Preset Render Action (from master) */}
                  <div className="pt-2 border-t border-[#293245] space-y-1.5">
                    <div className="flex items-center justify-between gap-1.5">
                      <select
                        value={currentPreset}
                        onChange={(e) => handlePresetChange(clip.id, e.target.value)}
                        className="flex-1 px-1.5 py-1 rounded bg-[#13151f] border border-[#293245] text-[11px] text-slate-300"
                      >
                        <option value="tiktok">TikTok (9:16)</option>
                        <option value="hyperframes">HyperFrames (HTML Motion Graphics)</option>
                        <option value="high_quality">High Quality Master (1080p)</option>
                        <option value="draft">Fast Draft (720p)</option>
                      </select>
                      {handleTriggerRender && (
                        <button
                          type="button"
                          onClick={() => handleTriggerRender(clip.id, currentPreset)}
                          className="px-2 py-1 rounded bg-[#293245] hover:bg-[#4c5e6b] text-slate-200 text-xs font-medium transition-colors flex items-center gap-1"
                          title="Queue background render with selected preset"
                        >
                          <Cpu className="w-3 h-3 text-blue-400" />
                          <span>Render</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Actions: Editor & Operator Decision */}
                  <div className="pt-1.5 flex flex-col gap-1.5">
                    {/* Open CapCut Studio Editor */}
                    <button
                      type="button"
                      onClick={() => setEditingClip && setEditingClip(clip)}
                      className="w-full py-1.5 rounded text-xs font-semibold bg-[#1a1d24] hover:bg-[#293245] text-blue-300 hover:text-white border border-[#4c5e6b] transition-colors flex items-center justify-center gap-1"
                    >
                      <Film className="w-3.5 h-3.5" />
                      <span>CapCut Studio Editor</span>
                    </button>

                    {/* Approve / Reject Decision */}
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => onClipDecision(clip.id, 'reject')}
                        disabled={loadingAction}
                        aria-label={`Reject clip ${clip.id}`}
                        className={`flex-1 py-1 rounded text-xs font-medium border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 ${
                          isRejected
                            ? 'bg-rose-950/50 text-rose-300 border-rose-900/50'
                            : 'bg-[#1e2333] hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 border-[#4c5e6b]'
                        }`}
                      >
                        {loadingAction === 'reject' ? '…' : 'Reject'}
                      </button>

                      <button
                        type="button"
                        onClick={() => onClipDecision(clip.id, 'approve')}
                        disabled={loadingAction}
                        aria-label={`Approve clip ${clip.id}`}
                        className={`flex-1 py-1 rounded text-xs font-medium border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-500 ${
                          isApproved
                            ? 'bg-emerald-600 text-white border-emerald-500'
                            : 'bg-[#1e2333] hover:bg-emerald-950/40 text-slate-300 hover:text-emerald-300 border-[#4c5e6b]'
                        }`}
                      >
                        {loadingAction === 'approve' ? '…' : isApproved ? 'Approved ✓' : 'Approve'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
