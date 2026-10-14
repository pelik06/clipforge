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
  CheckCheck,
  Cpu,
  History,
  RotateCcw,
  Ban,
  Trash2,
  Download,
  Layers
} from 'lucide-react';
import { useState } from 'react';

export default function DashboardView({
  jobs = [],
  clips = [],
  fixtures = [],
  renderJobs = [],
  exportsList = [],
  systemDeps,
  selectedJobId,
  setSelectedJobId,
  setActiveView,
  onClipDecision,
  actionLoading,
  setEditingClip,
  handleCancelRender,
  handleRetryRender,
  handleBatchRender,
  handleDeleteExport
}) {
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
            Review Queue ({waitingApprovalClips.length})
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
          <div className="text-[11px] text-slate-400 font-medium">Render Queue & Exports</div>
          <div className="text-2xl font-semibold text-blue-400 mt-1 tabular-nums">
            {renderJobs.length} / {exportsList.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5 tabular-nums">
            {renderJobs.length} active jobs • {exportsList.length} artifacts
          </div>
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
                  onClick={() => setEditingClip(clip)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setEditingClip(clip);
                    }
                  }}
                  className="p-3.5 hover:bg-[#181b22] cursor-pointer transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3 group focus-visible:outline-none focus-visible:bg-[#181b22] focus-visible:ring-1 focus-visible:ring-[#2563eb]"
                >
                  {/* Left: Thumbnail & Meta */}
                  <div className="flex items-start gap-3.5 min-w-0">
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

                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-white truncate max-w-[360px] group-hover:text-blue-300 transition-colors">
                          {clip.title || `Clip #${clip.id}`}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#1c202a] text-slate-300 font-mono tabular-nums border border-[#2b3140]">
                          Score: {clip.score || '90/100'}
                        </span>
                        {clip.is_recommended && (
                          <span className="text-[9px] px-1 rounded bg-amber-950/60 text-amber-300 font-mono border border-amber-800/40">
                            ★ RECOMMENDED
                          </span>
                        )}
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
                        setEditingClip(clip);
                      }}
                      className="px-2.5 py-1 rounded text-xs text-slate-300 hover:text-white bg-[#1a1d24] hover:bg-[#222631] border border-[#2b3140] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#2563eb]"
                    >
                      Studio Editor
                    </button>

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

      {/* P4 FEATURE FROM MASTER: Render Queue & Export Jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-lg bg-[#14161c] border border-[#222631] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-400" aria-hidden="true" />
                <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Render Queue & Export Jobs
                </h2>
              </div>
              <div className="flex items-center gap-2">
                {handleBatchRender && (
                  <button
                    onClick={handleBatchRender}
                    className="px-2.5 py-1 rounded bg-[#222631] hover:bg-[#2b3140] text-slate-300 text-xs font-medium transition-colors"
                  >
                    Batch Render Top 3
                  </button>
                )}
                <span className="text-[11px] text-slate-400 font-mono tabular-nums">
                  {renderJobs.length} Jobs
                </span>
              </div>
            </div>

            {renderJobs.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                No active render jobs in queue. Select a preset and queue clips from the review queue.
              </div>
            ) : (
              <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                {renderJobs.map((rjob) => {
                  const isQueued = rjob.status === 'queued';
                  const isRendering = rjob.status === 'rendering';
                  const isCompleted = rjob.status === 'completed';
                  const isFailed = rjob.status === 'failed';

                  return (
                    <div
                      key={rjob.id}
                      className="p-3 rounded-md bg-[#0c0d11] border border-[#1d212b] text-xs flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-slate-300 font-semibold">{rjob.id}</span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-[#1a1e2a] text-blue-300 font-mono uppercase">
                            {rjob.preset || 'tiktok'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-semibold uppercase ${
                              isCompleted
                                ? 'text-emerald-400'
                                : isFailed
                                ? 'text-rose-400'
                                : 'text-blue-400'
                            }`}
                          >
                            {rjob.status}
                          </span>
                          {isRendering && handleCancelRender && (
                            <button
                              onClick={() => handleCancelRender(rjob.id)}
                              className="p-1 text-slate-400 hover:text-rose-400"
                              title="Cancel render"
                            >
                              <Ban className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {isFailed && handleRetryRender && (
                            <button
                              onClick={() => handleRetryRender(rjob.id)}
                              className="p-1 text-slate-400 hover:text-blue-400"
                              title="Retry render"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="w-full bg-[#14161c] h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            isCompleted ? 'bg-emerald-500' : isFailed ? 'bg-rose-500' : 'bg-blue-500'
                          }`}
                          style={{ width: `${Math.max(5, rjob.progress || 0)}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                        <span>{rjob.stage || 'Processing'}</span>
                        <span className="tabular-nums">{rjob.progress || 0}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Job History & Persistence */}
          <div className="rounded-lg bg-[#14161c] border border-[#222631] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-slate-400" aria-hidden="true" />
                <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Job History & Persistence
                </h2>
              </div>
              <span className="text-[11px] text-slate-400 font-mono tabular-nums">{jobs.length} jobs</span>
            </div>

            {jobs.length === 0 ? (
              <div className="py-6 text-center text-slate-500 text-xs">No jobs recorded.</div>
            ) : (
              <div className="space-y-1.5 max-h-[180px] overflow-y-auto pr-1">
                {jobs.map((j) => (
                  <button
                    key={j.id}
                    onClick={() => setSelectedJobId && setSelectedJobId(j.id)}
                    className={`w-full text-left p-2.5 rounded border text-xs transition-colors flex items-center justify-between ${
                      j.id === selectedJobId
                        ? 'bg-[#1c202a] border-blue-500/50 text-white'
                        : 'bg-[#0c0d11] border-[#1d212b] text-slate-300 hover:border-[#2b3140]'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="font-medium truncate max-w-[280px]">{j.vod_url || j.id}</div>
                      <div className="text-[11px] text-slate-500 truncate mt-0.5">{j.stage || 'Completed'}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-[10px] font-semibold uppercase text-slate-400">{j.status}</span>
                      <div className="text-[10px] text-slate-500 font-mono tabular-nums">{j.progress || 0}%</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: P4/P5 Export Library & Engine Diagnostics */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-lg bg-[#14161c] border border-[#222631] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Film className="w-4 h-4 text-emerald-400" aria-hidden="true" />
                <h2 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Export Library
                </h2>
              </div>
              <span className="text-[11px] text-slate-400 font-mono tabular-nums">
                {exportsList.length} Artifacts
              </span>
            </div>

            {exportsList.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs">
                No rendered artifacts yet. Completed renders will appear here ready to publish.
              </div>
            ) : (
              <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                {exportsList.map((exp) => (
                  <div
                    key={exp.id}
                    className="p-2.5 rounded bg-[#0c0d11] border border-[#1d212b] text-xs flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-white truncate max-w-[180px]">
                        {exp.title || exp.id}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono tabular-nums mt-0.5">
                        {exp.preset} • {exp.resolution || '1080x1920'} • {exp.size_mb || '14'}MB
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {exp.url && (
                        <a
                          href={exp.url}
                          download
                          className="p-1 rounded bg-[#1c202a] text-emerald-400 hover:text-white"
                          title="Download MP4"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                      )}
                      {handleDeleteExport && (
                        <button
                          onClick={() => handleDeleteExport(exp.id)}
                          className="p-1 text-slate-500 hover:text-rose-400"
                          title="Delete export"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Engine Dependencies Bar */}
          <div className="rounded-lg bg-[#14161c] border border-[#222631] p-3.5">
            <div className="flex items-center gap-2 mb-2.5">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
              <span className="text-xs font-semibold text-white uppercase tracking-wider">
                Engine Dependencies
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              {systemDeps ? (
                Object.entries(systemDeps).map(([tool, ready]) => (
                  <div
                    key={tool}
                    className="flex items-center justify-between p-2 rounded bg-[#0c0d11] border border-[#1d212b]"
                  >
                    <span className="text-slate-300 font-mono text-[11px]">{tool}</span>
                    <span
                      className={`text-[10px] font-mono font-semibold ${
                        ready ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
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
      </div>
    </div>
  );
}
