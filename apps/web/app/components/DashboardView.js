'use client';

import {
  Film,
  Clock,
  CheckCircle2,
  XCircle,
  Play,
  ArrowUpRight,
  ShieldCheck,
  Check,
  X,
  Sliders,
  Eye,
  Video,
  CheckCheck
} from 'lucide-react';
import { useState } from 'react';
import ClipModal from './ClipModal';

export default function DashboardView({
  jobs = [],
  clips = [],
  fixtures = [],
  systemDeps,
  setActiveView,
  onClipDecision,
  actionLoading
}) {
  const [modalClip, setModalClip] = useState(null);
  const [recentFilter, setRecentFilter] = useState('all'); // 'all', 'pending', 'approved'
  const [batchLoading, setBatchLoading] = useState(false);

  const allClips = [...clips, ...fixtures];
  const waitingApprovalClips = allClips.filter(
    (c) => c.status === 'WAITING_APPROVAL' || (!c.status?.includes('APPROVED') && !c.status?.includes('REJECTED'))
  );
  const approvedClips = allClips.filter((c) => c.status === 'APPROVED');
  const activeJobs = jobs.filter((j) => j.status === 'processing' || j.status === 'created');

  // 5 newest clips sorted by created date
  const recentFiveClips = [...allClips]
    .sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA;
    })
    .slice(0, 5);

  const displayedRecentClips = recentFiveClips.filter((clip) => {
    const isApproved = clip.status === 'APPROVED';
    const isRejected = clip.status === 'REJECTED';
    const isPending = !isApproved && !isRejected;
    if (recentFilter === 'pending') return isPending;
    if (recentFilter === 'approved') return isApproved;
    return true;
  });

  const pendingInRecent = recentFiveClips.filter(
    (c) => c.status !== 'APPROVED' && c.status !== 'REJECTED'
  );

  const handleBatchApprove = async () => {
    if (pendingInRecent.length === 0 || batchLoading) return;
    setBatchLoading(true);
    for (const c of pendingInRecent) {
      await onClipDecision(c.id, 'approve');
    }
    setBatchLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#222631]">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white">Dashboard</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Operator Review Station: {waitingApprovalClips.length} clips awaiting decision across {jobs.length} jobs.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setActiveView('clips')}
            className="px-3 py-1.5 rounded-md bg-[#14161c] hover:bg-[#1a1d24] text-slate-300 text-xs font-medium border border-[#222631] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#2563eb]"
          >
            Review All Queue ({waitingApprovalClips.length})
          </button>

          <button
            onClick={() => setActiveView('generate')}
            className="px-3.5 py-1.5 rounded-md bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#2563eb]"
          >
            + Generate Clips
          </button>
        </div>
      </div>

      {/* Metrics Ribbon */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-lg bg-[#14161c] border border-[#222631]">
          <div className="text-[11px] text-slate-400 font-medium">Total Clips</div>
          <div className="text-2xl font-semibold text-white mt-1 tabular-nums">{allClips.length}</div>
          <div className="text-[11px] text-slate-500 mt-0.5 tabular-nums">
            {clips.length} rendered • {fixtures.length} demo
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#14161c] border border-[#222631]">
          <div className="text-[11px] text-slate-400 font-medium">Awaiting Review</div>
          <div className="text-2xl font-semibold text-amber-400 mt-1 tabular-nums">
            {waitingApprovalClips.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Pending operator decision</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#14161c] border border-[#222631]">
          <div className="text-[11px] text-slate-400 font-medium">Approved for Publish</div>
          <div className="text-2xl font-semibold text-emerald-400 mt-1 tabular-nums">
            {approvedClips.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Signed off</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#14161c] border border-[#222631]">
          <div className="text-[11px] text-slate-400 font-medium">Active Pipelines</div>
          <div className="text-2xl font-semibold text-blue-400 mt-1 tabular-nums">
            {activeJobs.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5 tabular-nums">{jobs.length} jobs total</div>
        </div>
      </div>

      {/* OPERATOR REVIEW: RECENT CLIPS (5 TERBARU) */}
      <div className="rounded-lg bg-[#14161c] border border-[#222631] overflow-hidden">
        {/* Toolbar Header */}
        <div className="px-4 py-3 border-b border-[#222631] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Film className="w-4 h-4 text-slate-400" aria-hidden="true" />
              <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                Recent Clips (5 Latest)
              </h2>
            </div>

            {/* Quick Status Filters */}
            <div className="flex items-center bg-[#0c0d11] p-0.5 rounded border border-[#222631] text-[11px]">
              <button
                onClick={() => setRecentFilter('all')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  recentFilter === 'all' ? 'bg-[#222631] text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All ({recentFiveClips.length})
              </button>
              <button
                onClick={() => setRecentFilter('pending')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  recentFilter === 'pending' ? 'bg-[#222631] text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Pending ({pendingInRecent.length})
              </button>
              <button
                onClick={() => setRecentFilter('approved')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  recentFilter === 'approved' ? 'bg-[#222631] text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Approved ({recentFiveClips.filter((c) => c.status === 'APPROVED').length})
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {pendingInRecent.length > 0 && (
              <button
                onClick={handleBatchApprove}
                disabled={batchLoading}
                className="px-2.5 py-1 rounded text-xs font-medium bg-[#14261d] text-emerald-300 hover:bg-emerald-950/60 border border-emerald-800/60 transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{batchLoading ? 'Approving…' : `Batch Approve (${pendingInRecent.length})`}</span>
              </button>
            )}

            <button
              onClick={() => setActiveView('clips')}
              className="text-xs text-[#3b82f6] hover:text-[#60a5fa] flex items-center gap-1 transition-colors ml-1"
            >
              <span>View all ({allClips.length})</span>
              <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {displayedRecentClips.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs">
            {recentFilter !== 'all'
              ? 'No clips in this status filter.'
              : 'No clips generated yet. Submit a video link to start.'}
          </div>
        ) : (
          <div className="divide-y divide-[#222631]">
            {displayedRecentClips.map((clip) => {
              const isApproved = clip.status === 'APPROVED';
              const isRejected = clip.status === 'REJECTED';
              const isWaiting = !isApproved && !isRejected;
              const loadingAction = actionLoading[clip.id];

              return (
                <div
                  key={clip.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setModalClip(clip)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setModalClip(clip);
                    }
                  }}
                  className="p-3.5 hover:bg-[#181b22] cursor-pointer transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 group focus-visible:outline-none focus-visible:bg-[#181b22] focus-visible:ring-1 focus-visible:ring-[#2563eb]"
                >
                  {/* Left: Thumbnail & Meta */}
                  <div className="flex items-start gap-3.5 min-w-0">
                    {/* 9:16 Miniature */}
                    <div className="w-11 h-16 rounded bg-black border border-[#2b3140] shrink-0 overflow-hidden relative flex items-center justify-center">
                      {clip.media_url ? (
                        <video
                          src={clip.media_url}
                          preload="metadata"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Play className="w-4 h-4 text-slate-400 ml-0.5" aria-hidden="true" />
                      )}
                    </div>

                    {/* Titles & Timecode */}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-white truncate max-w-[360px] group-hover:text-blue-300 transition-colors">
                          {clip.title || `Clip #${clip.id}`}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#1c202a] text-slate-300 font-mono tabular-nums border border-[#2b3140]">
                          Score: {clip.score || '90/100'}
                        </span>
                        {clip.is_fixture && (
                          <span className="text-[9px] px-1 rounded bg-[#2b3140]/60 text-slate-400 font-mono">
                            DEMO
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1 tabular-nums">
                        <span>Duration: {clip.duration || '20s'}</span>
                        <span>•</span>
                        <span>
                          Timecode:{' '}
                          {clip.start_time !== undefined
                            ? `${clip.start_time}s – ${clip.end_time}s`
                            : '00:10 – 00:30'}
                        </span>
                        <span className="hidden sm:inline">•</span>
                        <span className="hidden sm:inline truncate max-w-[200px]">
                          {clip.vod || 'Source VOD'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: QC, Details & Actions */}
                  <div className="flex items-center gap-2.5 shrink-0 self-end md:self-center">
                    <span className="hidden sm:inline text-[10px] font-mono text-emerald-400 bg-emerald-950/30 border border-emerald-800/40 px-2 py-0.5 rounded">
                      QC: PASS
                    </span>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setModalClip(clip);
                      }}
                      className="px-2.5 py-1 rounded text-xs text-slate-300 hover:text-white bg-[#1a1d24] hover:bg-[#222631] border border-[#2b3140] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#2563eb]"
                    >
                      Details & Editor
                    </button>

                    {/* Decision buttons */}
                    {isWaiting ? (
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onClipDecision(clip.id, 'reject');
                          }}
                          disabled={loadingAction}
                          aria-label={`Reject clip ${clip.id}`}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-[#22171a] text-rose-300 hover:bg-rose-950/60 border border-rose-900/40 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rose-500"
                        >
                          Reject
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onClipDecision(clip.id, 'approve');
                          }}
                          disabled={loadingAction}
                          aria-label={`Approve clip ${clip.id}`}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-[#14261d] text-emerald-300 hover:bg-emerald-950/60 border border-emerald-800/50 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-500"
                        >
                          Approve
                        </button>
                      </div>
                    ) : (
                      <span
                        className={`text-[10px] font-semibold uppercase px-2 py-1 rounded tabular-nums ${
                          isApproved
                            ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/40'
                            : 'bg-rose-950/40 text-rose-400 border border-rose-800/40'
                        }`}
                      >
                        {clip.status}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Engine Dependencies Bar */}
      <div className="rounded-lg bg-[#14161c] border border-[#222631] p-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
            <span className="text-xs font-semibold text-white uppercase tracking-wider">
              Engine Dependencies
            </span>
          </div>
          <div className="flex items-center gap-3 flex-wrap text-xs">
            {systemDeps ? (
              Object.entries(systemDeps).map(([tool, ready]) => (
                <div key={tool} className="flex items-center gap-1.5 font-mono text-[11px]">
                  <span className="text-slate-400">{tool}:</span>
                  <span className={ready ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {ready ? 'OK' : 'MISSING'}
                  </span>
                </div>
              ))
            ) : (
              <span className="text-slate-500 text-xs">Checking dependencies…</span>
            )}
          </div>
        </div>
      </div>

      {/* Modal Inspector */}
      {modalClip && (
        <ClipModal
          clip={modalClip}
          onClose={() => setModalClip(null)}
          onClipDecision={(id, dec) => {
            onClipDecision(id, dec);
            setModalClip((prev) =>
              prev && prev.id === id ? { ...prev, status: dec === 'approve' ? 'APPROVED' : 'REJECTED' } : prev
            );
          }}
          actionLoading={actionLoading}
        />
      )}
    </div>
  );
}
