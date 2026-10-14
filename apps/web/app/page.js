'use client';

import { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import DashboardView from './components/DashboardView';
import GenerateView from './components/GenerateView';
import ClipsView from './components/ClipsView';
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
  // Studio Configurations
  const [framingMode, setFramingMode] = useState('auto_follow_speaker');
  const [captionPreset, setCaptionPreset] = useState('clean');
  const [captionLanguage, setCaptionLanguage] = useState('auto');
  const [captionSize, setCaptionSize] = useState('medium');
  const [captionPosition, setCaptionPosition] = useState('bottom_safe');
  const [captionTextColor, setCaptionTextColor] = useState('#FFFFFF');
  const [captionHighlightColor, setCaptionHighlightColor] = useState('#FFFF00');
  const [captionWordHighlight, setCaptionWordHighlight] = useState(false);
  const [showAdvancedCaptions, setShowAdvancedCaptions] = useState(false);
  const [momentDetectionMode, setMomentDetectionMode] = useState('heuristic');
  const [momentDetectionProvider, setMomentDetectionProvider] = useState('heuristic');
  const [maxClips, setMaxClips] = useState(3);
  const [minClipDuration, setMinClipDuration] = useState(30);
  const [maxClipDuration, setMaxClipDuration] = useState(120);
  const [enableSceneDetection, setEnableSceneDetection] = useState(true);

  // Data Store
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJobData, setSelectedJobData] = useState(null);
  const [clips, setClips] = useState([]);
  const [fixtures, setFixtures] = useState([]);
  const [actionLoading, setActionLoading] = useState({});

  const pollIntervalRef = useRef(null);

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

        // Auto-select latest active job or top job if none selected
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
    pollIntervalRef.current = setInterval(() => {
      fetchJobsAndClips();
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

  // URL input handler
  const handleUrlChange = (e) => {
    const val = e.target.value;
    setVodUrl(val);
    if (val.trim() && !isValidVodUrl(val)) {
      setInputError('Must be a public YouTube link (youtube.com / youtu.be) or a local video file (.mp4, .mkv, .mov)');
    } else {
      setInputError('');
    }
  };

  // Job Submission Handler
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

    try {
      const res = await fetch(`${API_BASE}/api/v4/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vod_url: trimmed,
          framing_mode: 'auto_follow_speaker',
          caption_preset: captionPreset,
          caption_language: captionLanguage,
          caption_size: captionSize,
          caption_position: captionPosition,
          caption_text_color: captionTextColor,
          caption_highlight_color: captionHighlightColor,
          caption_word_highlight: captionWordHighlight,
          moment_detection_mode: 'heuristic',
          moment_detection_provider: 'heuristic',
          max_clips: parseInt(maxClips || 3),
          min_clip_duration: parseFloat(minClipDuration || 30),
          max_clip_duration: parseFloat(maxClipDuration || 120),
          enable_scene_detection: true,
        })
      });

      const data = await res.json();
      if (res.ok) {
        const newId = data.job?.id;
        setSelectedJobId(newId);
        setBanner({
          type: 'success',
          message: data.message || `Pipeline job ${newId} initialized successfully! Processing 13 stages in background.`
        });
        setVodUrl('');
        // Switch to generate view to watch live progress
        setActiveView('generate');
        fetchJobsAndClips();
      } else {
        setBanner({
          type: 'error',
          message: data.detail || 'Failed to submit pipeline job.'
        });
      }
    } catch (err) {
      setBanner({
        type: 'error',
        message: 'Network error communicating with ClipForge backend.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Quick generate from dashboard
  const handleQuickGenerate = (e) => {
    handleVodSubmit(e);
  };

  // Clippo Sync Handler
  const handleClippoSync = async (e) => {
    e.preventDefault();
    if (clippoSubmitting) return;
    if (!clippoId.trim()) return;

    setClippoSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/v4/clippo/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clippo_job_id: clippoId.trim(),
          vod_url: vodUrl.trim() || `https://clippo.id/task/${clippoId.trim()}`
        })
      });
      const data = await res.json();
      if (res.ok) {
        const newId = data.job?.id;
        setSelectedJobId(newId);
        setBanner({
          type: 'success',
          message: data.message || `Clippo task ${clippoId} synchronized into ClipForge pipeline.`
        });
        setClippoId('');
        fetchJobsAndClips();
      } else {
        setBanner({
          type: 'error',
          message: data.detail || 'Failed to sync with Clippo.id.'
        });
      }
    } catch (err) {
      setBanner({
        type: 'error',
        message: 'Network error syncing with Clippo.id.'
      });
    } finally {
      setClippoSubmitting(false);
    }
  };

  // Operator Clip Approval / Rejection
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
          message: data.message || `Clip ${clipId} ${newStatus.toLowerCase()} successfully.`
        });
      } else {
        setBanner({
          type: 'error',
          message: data.detail || `Failed to record operator decision on clip ${clipId}.`
        });
      }
    } catch (err) {
      setBanner({
        type: 'error',
        message: 'Network error updating clip status.'
      });
    } finally {
      setActionLoading(prev => {
        const copy = { ...prev };
        delete copy[clipId];
        return copy;
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#0c0d11] text-[#f3f4f6] flex flex-col font-sans selection:bg-[#2563eb] selection:text-white">
      <Navbar
        activeView={activeView}
        setActiveView={setActiveView}
        backendOnline={backendOnline}
        systemDeps={systemDeps}
        clipsCount={clips.length}
        jobsCount={jobs.length}
      />

      {/* Global Notification Banner */}
      {banner && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full mt-4 animate-fadeIn">
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
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : banner.type === 'error' ? (
                <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
              ) : (
                <Info className="w-4 h-4 text-violet-400 shrink-0" />
              )}
              <span className="font-medium">{banner.message}</span>
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
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {activeView === 'dashboard' && (
          <DashboardView
            jobs={jobs}
            clips={clips}
            fixtures={fixtures}
            systemDeps={systemDeps}
            selectedJobId={selectedJobId}
            setSelectedJobId={setSelectedJobId}
            selectedJobData={selectedJobData}
            setActiveView={setActiveView}
            onClipDecision={handleClipDecision}
            actionLoading={actionLoading}
            onQuickGenerate={handleQuickGenerate}
            vodUrl={vodUrl}
            setVodUrl={setVodUrl}
            inputError={inputError}
            submitting={submitting}
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
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#222631] bg-[#0c0d11] py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>ClipForge Studio • Operator Review Workstation</p>
          <p className="font-mono text-[11px] text-slate-600">
            9:16 Reframe Engine • YuNet Face Tracking • Whisper Word Timings
          </p>
        </div>
      </footer>
    </div>
  );
}
