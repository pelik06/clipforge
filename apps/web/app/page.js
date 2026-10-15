'use client';

import { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import DashboardView from './components/DashboardView';
import GenerateView from './components/GenerateView';
import ClipsView from './components/ClipsView';
import ClipModal from './components/ClipModal';
import { CheckCircle2, AlertCircle, XCircle, Info, X } from 'lucide-react';

const YOUTUBE_REGEX = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?.*v=|shorts\/|live\/)|youtu\.be\/)[a-zA-Z0-9_-]{11}(.*)?$/i;
const VIDEO_EXT_REGEX = /\.(mp4|mkv|mov|webm|avi|flv)$/i;

function isValidVodUrl(url) {
  const trimmed = url.trim();
  if (!trimmed) return false;
  return YOUTUBE_REGEX.test(trimmed) || VIDEO_EXT_REGEX.test(trimmed) || trimmed.startsWith('/') || /^[a-zA-Z]:[\\/]/.test(trimmed);
}

const API_BASE = '';

export default function Home() {
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard' | 'generate' | 'clips'
  const [vodUrl, setVodUrl] = useState('');
  const [inputError, setInputError] = useState('');
  const [clippoId, setClippoId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [clippoSubmitting, setClippoSubmitting] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);
  const [systemDeps, setSystemDeps] = useState(null);
  const [banner, setBanner] = useState(null);

  // Ingestion Configurations (exact fields from master)
  const [framingMode, setFramingMode] = useState('auto_follow_speaker');
  const [captionPreset, setCaptionPreset] = useState('karaoke');
  const [captionLanguage, setCaptionLanguage] = useState('auto');
  const [captionSize, setCaptionSize] = useState('large');
  const [captionPosition, setCaptionPosition] = useState('bottom_safe');
  const [captionTextColor, setCaptionTextColor] = useState('#FFFFFF');
  const [captionHighlightColor, setCaptionHighlightColor] = useState('#FFFF00');
  const [captionWordHighlight, setCaptionWordHighlight] = useState(true);
  const [showAdvancedCaptions, setShowAdvancedCaptions] = useState(false);
  const [momentDetectionMode, setMomentDetectionMode] = useState('heuristic');
  const [momentDetectionProvider, setMomentDetectionProvider] = useState('heuristic');
  const [maxClips, setMaxClips] = useState(5);
  const [minClipDuration, setMinClipDuration] = useState(45);
  const [maxClipDuration, setMaxClipDuration] = useState(120);
  const [enableSceneDetection, setEnableSceneDetection] = useState(true);

  // Core Data Store
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJobData, setSelectedJobData] = useState(null);
  const [clips, setClips] = useState([]);
  const [fixtures, setFixtures] = useState([]);
  const [actionLoading, setActionLoading] = useState({});

  // P4 Render Queue & P5 Studio State (from master)
  const [renderJobs, setRenderJobs] = useState([]);
  const [selectedPresetByClip, setSelectedPresetByClip] = useState({});
  const [editingClip, setEditingClip] = useState(null);
  const [exportsList, setExportsList] = useState([]);

  const pollIntervalRef = useRef(null);

  // P4/P5: Fetch Exports
  const fetchExports = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/exports`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setExportsList(data.exports || []);
      }
    } catch (e) {}
  };

  const handleDeleteExport = async (exportId) => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/exports/${exportId}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchExports();
      }
    } catch (e) {}
  };

  // P4: Fetch Render Queue
  const fetchRenderJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/renders`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setRenderJobs(data.renders || []);
      }
    } catch (e) {}
  };

  const handleTriggerRender = async (clipId, preset = 'tiktok', renderType = 'final') => {
    setBanner({ type: 'info', text: `Submitting render request for ${clipId} (${preset})…` });
    try {
      const res = await fetch(`${API_BASE}/api/v4/renders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clip_id: clipId, preset: preset, render_type: renderType }),
      });
      const data = await res.json();
      if (res.ok) {
        setBanner({ type: 'success', text: `Render job ${data.job?.id} queued in render queue.` });
        await fetchRenderJobs();
      } else {
        setBanner({ type: 'error', text: `Render request rejected: ${data.detail || 'Error'}` });
      }
    } catch (err) {
      setBanner({ type: 'error', text: 'Network error submitting render job.' });
    }
  };

  const handleCancelRender = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/renders/${jobId}/cancel`, { method: 'POST' });
      if (res.ok) {
        setBanner({ type: 'info', text: `Render job ${jobId} cancelled.` });
        await fetchRenderJobs();
      }
    } catch (e) {}
  };

  const handleRetryRender = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/renders/${jobId}/retry`, { method: 'POST' });
      if (res.ok) {
        setBanner({ type: 'info', text: `Render job ${jobId} re-queued for retry.` });
        await fetchRenderJobs();
      }
    } catch (e) {}
  };

  const handleBatchRender = async () => {
    const candidateIds = clips.slice(0, 3).map((c) => c.id);
    if (candidateIds.length === 0) return;
    setBanner({ type: 'info', text: `Queueing batch render for ${candidateIds.length} clips…` });
    try {
      const res = await fetch(`${API_BASE}/api/v4/renders/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clip_ids: candidateIds, preset: 'tiktok', render_type: 'final' }),
      });
      if (res.ok) {
        setBanner({ type: 'success', text: `Batch render queued for ${candidateIds.length} clips.` });
        await fetchRenderJobs();
      }
    } catch (e) {}
  };

  // Fetch Jobs & Clips
  const fetchJobsAndClips = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/jobs`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        const jList = data.jobs || [];
        setJobs(jList);
        setClips(data.clips || []);
        if (data.fixtures) {
          setFixtures(data.fixtures);
        }
        setBackendOnline(true);

        if (!selectedJobId && jList.length > 0) {
          setSelectedJobId(jList[0].id);
        }
      } else {
        setBackendOnline(false);
      }

      const sysRes = await fetch(`${API_BASE}/api/v4/system`, { cache: 'no-store' });
      if (sysRes.ok) {
        const sysData = await sysRes.json();
        setSystemDeps(sysData.dependencies || null);
      }
    } catch (err) {
      setBackendOnline(false);
    }
  };

  const fetchSingleJob = async (jobId) => {
    if (!jobId) return;
    try {
      const res = await fetch(`${API_BASE}/api/v4/jobs/${jobId}`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        setSelectedJobData(data.job || null);
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchJobsAndClips();
    fetchRenderJobs();
    fetchExports();
    pollIntervalRef.current = setInterval(() => {
      fetchJobsAndClips();
      fetchRenderJobs();
      fetchExports();
      if (selectedJobId) {
        fetchSingleJob(selectedJobId);
      }
    }, 2000);

    return () => {
      clearInterval(pollIntervalRef.current);
    };
  }, [selectedJobId]);

  useEffect(() => {
    if (selectedJobId) {
      fetchSingleJob(selectedJobId);
    }
  }, [selectedJobId]);

  const handleUrlChange = (e) => {
    const val = e.target.value;
    setVodUrl(val);
    if (val.trim() && !isValidVodUrl(val)) {
      setInputError('Must be a public YouTube link (youtube.com / youtu.be) or a local video file (.mp4, .mkv, .mov)');
    } else {
      setInputError('');
    }
  };

  const handleVodSubmit = async (e) => {
    if (e) e.preventDefault();
    if (submitting) return;

    const trimmed = vodUrl.trim();
    if (!trimmed) {
      setInputError('Please enter a video URL or local file path.');
      return;
    }

    if (!isValidVodUrl(trimmed)) {
      setInputError('Invalid format. Enter a valid YouTube link or local video file (.mp4, .mkv, .mov).');
      return;
    }

    setSubmitting(true);
    setInputError('');
    setBanner({ type: 'info', text: `Initiating 13-stage clipping pipeline for ${trimmed}…` });

    try {
      const res = await fetch(`${API_BASE}/api/v4/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vod_url: trimmed,
          framing_mode: framingMode || 'auto_follow_speaker',
          caption_preset: captionPreset,
          caption_language: captionLanguage,
          caption_size: captionSize,
          caption_position: captionPosition,
          caption_text_color: captionTextColor,
          caption_highlight_color: captionHighlightColor,
          caption_word_highlight: captionWordHighlight,
          moment_detection_mode: momentDetectionMode,
          moment_detection_provider: momentDetectionProvider,
          max_clips: parseInt(maxClips),
          min_clip_duration: parseFloat(minClipDuration),
          max_clip_duration: parseFloat(maxClipDuration),
          enable_scene_detection: enableSceneDetection
        })
      });

      const data = await res.json();
      if (res.ok) {
        const newId = data.job?.id;
        setSelectedJobId(newId);
        setBanner({
          type: 'success',
          text: `Job ${newId} initiated! Tracking 13 stages in workspace.`
        });
        setVodUrl('');
        setActiveView('generate');
        await fetchJobsAndClips();
        if (newId) await fetchSingleJob(newId);
      } else {
        setBanner({
          type: 'error',
          text: `Submission rejected: ${data.detail || 'Backend processing error.'}`
        });
      }
    } catch (err) {
      setBanner({
        type: 'error',
        text: 'Cannot reach ClipForge backend API at 127.0.0.1:8000.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleClippoSync = async (e) => {
    e.preventDefault();
    if (clippoSubmitting) return;
    if (!clippoId.trim()) return;

    setClippoSubmitting(true);
    setBanner({ type: 'info', text: `Syncing bounty task ${clippoId} with Clippo.id…` });

    try {
      const res = await fetch(`${API_BASE}/api/v4/clippo/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clippo_job_id: clippoId.trim(),
          vod_url: `https://clippo.id/tasks/${clippoId.trim()}`
        })
      });
      const data = await res.json();
      if (res.ok) {
        const newId = data.job?.id;
        setSelectedJobId(newId);
        setBanner({
          type: 'success',
          text: `Clippo task ${clippoId} queued! Tracking live stages.`
        });
        setClippoId('');
        await fetchJobsAndClips();
      } else {
        setBanner({
          type: 'error',
          text: `Clippo sync failed: ${data.detail || 'Task not found'}`
        });
      }
    } catch (err) {
      setBanner({
        type: 'error',
        text: 'Failed to communicate with ClipForge backend for Clippo.id synchronization.'
      });
    } finally {
      setClippoSubmitting(false);
    }
  };

  const handleClipDecision = async (clipId, decision) => {
    setActionLoading(prev => ({ ...prev, [clipId]: decision }));
    try {
      const res = await fetch(`${API_BASE}/api/v4/jobs/${clipId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision })
      });
      const data = await res.json();
      if (res.ok) {
        const newStatus = decision === 'approve' ? 'APPROVED' : 'REJECTED';
        setClips(prev => prev.map(c => c.id === clipId ? { ...c, status: newStatus } : c));
        setFixtures(prev => prev.map(c => c.id === clipId ? { ...c, status: newStatus } : c));
        setBanner({
          type: 'success',
          text: `Clip ${clipId} has been ${newStatus.toLowerCase()} by human operator.`
        });
      } else {
        setBanner({
          type: 'error',
          text: `Failed to record decision: ${data.detail || 'Backend error'}`
        });
      }
    } catch (err) {
      setBanner({
        type: 'error',
        text: 'Network error submitting approval decision to backend API.'
      });
    } finally {
      setActionLoading(prev => ({ ...prev, [clipId]: null }));
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0d11] text-[#f3f4f6] flex flex-col font-sans selection:bg-[#2563eb] selection:text-white">
      {/* Top Navbar */}
      <Navbar
        activeView={activeView}
        setActiveView={setActiveView}
        backendOnline={backendOnline}
        systemDeps={systemDeps}
        clipsCount={clips.length}
        onRefresh={fetchJobsAndClips}
      />

      {/* Global Notification Banner */}
      {banner && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 w-full mt-3 animate-fadeIn">
          <div
            className={`p-3 rounded-md border flex items-center justify-between text-xs ${
              banner.type === 'success'
                ? 'bg-[#14261d] border-emerald-800/50 text-emerald-200'
                : banner.type === 'error'
                ? 'bg-[#22171a] border-rose-900/50 text-rose-200'
                : 'bg-[#1c2233] border-blue-900/50 text-blue-200'
            }`}
          >
            <div className="flex items-center gap-2.5">
              {banner.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" aria-hidden="true" />
              ) : banner.type === 'error' ? (
                <XCircle className="w-4 h-4 text-rose-400 shrink-0" aria-hidden="true" />
              ) : (
                <Info className="w-4 h-4 text-blue-400 shrink-0" aria-hidden="true" />
              )}
              <span className="font-medium">{banner.text || banner.message}</span>
            </div>
            <button
              onClick={() => setBanner(null)}
              aria-label="Dismiss notification"
              className="text-slate-400 hover:text-white p-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-400 rounded"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}

      {/* Main Content View Switcher */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 py-6 w-full">
        {activeView === 'dashboard' && (
          <DashboardView
            jobs={jobs}
            clips={clips}
            fixtures={fixtures}
            renderJobs={renderJobs}
            exportsList={exportsList}
            systemDeps={systemDeps}
            selectedJobId={selectedJobId}
            setSelectedJobId={setSelectedJobId}
            setActiveView={setActiveView}
            onClipDecision={handleClipDecision}
            actionLoading={actionLoading}
            setEditingClip={setEditingClip}
            handleCancelRender={handleCancelRender}
            handleRetryRender={handleRetryRender}
            handleBatchRender={handleBatchRender}
            handleDeleteExport={handleDeleteExport}
          />
        )}

        {activeView === 'generate' && (
          <GenerateView
            vodUrl={vodUrl}
            setVodUrl={setVodUrl}
            inputError={inputError}
            handleUrlChange={handleUrlChange}
            handleVodSubmit={handleVodSubmit}
            submitting={submitting}
            clippoId={clippoId}
            setClippoId={setClippoId}
            handleClippoSync={handleClippoSync}
            clippoSubmitting={clippoSubmitting}
            framingMode={framingMode}
            setFramingMode={setFramingMode}
            captionPreset={captionPreset}
            setCaptionPreset={setCaptionPreset}
            captionLanguage={captionLanguage}
            setCaptionLanguage={setCaptionLanguage}
            captionSize={captionSize}
            setCaptionSize={setCaptionSize}
            captionPosition={captionPosition}
            setCaptionPosition={setCaptionPosition}
            captionTextColor={captionTextColor}
            setCaptionTextColor={setCaptionTextColor}
            captionHighlightColor={captionHighlightColor}
            setCaptionHighlightColor={setCaptionHighlightColor}
            captionWordHighlight={captionWordHighlight}
            setCaptionWordHighlight={setCaptionWordHighlight}
            showAdvancedCaptions={showAdvancedCaptions}
            setShowAdvancedCaptions={setShowAdvancedCaptions}
            momentDetectionMode={momentDetectionMode}
            setMomentDetectionMode={setMomentDetectionMode}
            momentDetectionProvider={momentDetectionProvider}
            setMomentDetectionProvider={setMomentDetectionProvider}
            maxClips={maxClips}
            setMaxClips={setMaxClips}
            minClipDuration={minClipDuration}
            setMinClipDuration={setMinClipDuration}
            maxClipDuration={maxClipDuration}
            setMaxClipDuration={setMaxClipDuration}
            enableSceneDetection={enableSceneDetection}
            setEnableSceneDetection={setEnableSceneDetection}
            selectedJobData={selectedJobData}
            jobs={jobs}
            selectedJobId={selectedJobId}
            setActiveView={setActiveView}
          />
        )}

        {activeView === 'clips' && (
          <ClipsView
            clips={clips}
            fixtures={fixtures}
            onClipDecision={handleClipDecision}
            actionLoading={actionLoading}
            setActiveView={setActiveView}
            setEditingClip={setEditingClip}
            handleTriggerRender={handleTriggerRender}
            selectedPresetByClip={selectedPresetByClip}
            setSelectedPresetByClip={setSelectedPresetByClip}
          />
        )}
      </main>

      {/* P5 CapCut-Style Studio Editor Modal */}
      {editingClip && (
        <ClipModal
          clip={editingClip}
          onClose={() => setEditingClip(null)}
          onClipDecision={handleClipDecision}
          actionLoading={actionLoading}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-[#222631] bg-[#0c0d11] py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>ClipForge Studio • Video Clipping & Review Workspace</p>
          <p className="font-mono text-[11px] text-slate-600">
            YuNet 9:16 Face Tracking • Whisper Word Timings • 13-Stage Pipeline
          </p>
        </div>
      </footer>
    </div>
  );
}
