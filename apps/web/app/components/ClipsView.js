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
  Download
} from 'lucide-react';
import ClipModal from './ClipModal';

export default function ClipsView({
  clips = [],
  fixtures = [],
  onClipDecision,
  actionLoading,
  setActiveView
}) {
  const [sourceTab, setSourceTab] = useState('real'); // 'real' or 'fixtures'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'pending', 'approved', 'rejected'
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('score_desc');
  const [selectedClip, setSelectedClip] = useState(null);

  const baseList = sourceTab === 'real' ? clips : fixtures;

  // Filter & Search logic
  const filteredClips = baseList.filter((clip) => {
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

    return true;
  });

  // Sorting
  const sortedClips = [...filteredClips].sort((a, b) => {
    const scoreA = parseFloat(a.score || a.virality_score || 0);
    const scoreB = parseFloat(b.score || b.virality_score || 0);
    if (sortBy === 'score_desc') return scoreB - scoreA;
    if (sortBy === 'score_asc') return scoreA - scoreB;
    return 0;
  });

  const pendingCount = baseList.filter((c) => c.status !== 'APPROVED' && c.status !== 'REJECTED').length;
  const approvedCount = baseList.filter((c) => c.status === 'APPROVED').length;
  const rejectedCount = baseList.filter((c) => c.status === 'REJECTED').length;

  return (
    <div className="space-y-5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#222631]">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">All Generated Clips</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Operator review queue: verify 9:16 vertical crop, subtitle accuracy, and approve clips for publication.
          </p>
        </div>

        {/* Source Switcher */}
        <div className="flex items-center bg-[#14161c] p-0.5 rounded-md border border-[#222631] shrink-0">
          <button
            onClick={() => setSourceTab('real')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              sourceTab === 'real'
                ? 'bg-[#222631] text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Rendered Media ({clips.length})</span>
          </button>

          <button
            onClick={() => setSourceTab('fixtures')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              sourceTab === 'fixtures'
                ? 'bg-[#222631] text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>Demo Fixtures ({fixtures.length})</span>
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="p-3 rounded-lg bg-[#14161c] border border-[#222631] flex flex-col md:flex-row items-center justify-between gap-3">
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
            className="w-full pl-8 pr-3 py-1.5 rounded bg-[#0c0d11] border border-[#222631] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#2563eb]"
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
                  ? 'bg-[#222631] text-white border border-[#2b3140]'
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
            className="px-2.5 py-1 rounded bg-[#0c0d11] border border-[#222631] text-xs text-slate-300 focus:outline-none"
          >
            <option value="score_desc">Highest Score</option>
            <option value="score_asc">Lowest Score</option>
          </select>
        </div>
      </div>

      {/* Grid of 9:16 Clips */}
      {sortedClips.length === 0 ? (
        <div className="py-16 text-center rounded-lg bg-[#14161c] border border-[#222631] p-6 space-y-3">
          <div className="text-sm font-semibold text-white">No Clips Found</div>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {searchQuery || statusFilter !== 'all'
              ? 'No clips match your active search or status filter.'
              : 'No clips have been generated in this collection yet.'}
          </p>
          <button
            onClick={() => setActiveView('generate')}
            className="px-3.5 py-1.5 rounded bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-medium transition-colors"
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

            return (
              <div
                key={clip.id}
                className="rounded-lg bg-[#14161c] border border-[#222631] hover:border-[#323849] overflow-hidden transition-colors flex flex-col"
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
                      <div className="w-10 h-10 rounded-full bg-[#1c202a] border border-[#2b3140] flex items-center justify-center mx-auto text-slate-400">
                        <Play className="w-5 h-5 ml-0.5" />
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 block">
                        9:16 PREVIEW
                      </span>
                    </div>
                  )}

                  {/* Score Tag Top Left */}
                  <div className="absolute top-2.5 left-2.5 z-10">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-black/80 text-slate-200 border border-[#2b3140] tabular-nums">
                      Score: {clip.score || '90/100'}
                    </span>
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
                  </div>

                  {/* QC & Inspect Bar */}
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-2 border-t border-[#1d212b]">
                    <span className="text-emerald-400 flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" />
                      QC: PASS
                    </span>
                    <button
                      onClick={() => setSelectedClip(clip)}
                      className="text-[#3b82f6] hover:underline flex items-center gap-0.5"
                    >
                      <Eye className="w-3 h-3" />
                      Details
                    </button>
                  </div>

                  {/* Action Buttons */}
                  <div className="pt-1 flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => onClipDecision(clip.id, 'reject')}
                      disabled={loadingAction}
                      aria-label={`Reject clip ${clip.id}`}
                      className={`flex-1 py-1 rounded text-xs font-medium border transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 ${
                        isRejected
                          ? 'bg-rose-950/50 text-rose-300 border-rose-900/50'
                          : 'bg-[#1c202a] hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 border-[#2b3140]'
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
                          : 'bg-[#1c202a] hover:bg-emerald-950/40 text-slate-300 hover:text-emerald-300 border-[#2b3140]'
                      }`}
                    >
                      {loadingAction === 'approve' ? '…' : isApproved ? 'Approved ✓' : 'Approve'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Inspector Modal */}
      {selectedClip && (
        <ClipModal
          clip={selectedClip}
          onClose={() => setSelectedClip(null)}
          onClipDecision={(id, dec) => {
            onClipDecision(id, dec);
            setSelectedClip((prev) =>
              prev && prev.id === id ? { ...prev, status: dec === 'approve' ? 'APPROVED' : 'REJECTED' } : prev
            );
          }}
          actionLoading={actionLoading}
        />
      )}
    </div>
  );
}
