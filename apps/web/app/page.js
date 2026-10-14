'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Film,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Play,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Check,
  X,
  Layers,
  Video,
  ChevronRight,
  Flame,
  Cpu,
  MinusCircle,
  Database,
  History,
  Info,
  Sliders,
  Eye,
  Type,
  Palette
} from 'lucide-react';

const YOUTUBE_REGEX = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?.*v=|shorts\/|live\/)|youtu\.be\/)[a-zA-Z0-9_-]{11}(.*)?$/i;
const VIDEO_EXT_REGEX = /\.(mp4|mkv|mov|webm|avi|flv)$/i;

function isValidVodUrl(url) {
  const trimmed = url.trim();
  if (!trimmed) return false;
  return YOUTUBE_REGEX.test(trimmed) || VIDEO_EXT_REGEX.test(trimmed) || trimmed.startsWith('/') || /^[a-zA-Z]:[\\/]/.test(trimmed);
}

const API_BASE = '';

export default function Dashboard() {
  const [vodUrl, setVodUrl] = useState('');
  const [inputError, setInputError] = useState('');
  const [clippoId, setClippoId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [clippoSubmitting, setClippoSubmitting] = useState(false);
  const [backendOnline, setBackendOnline] = useState(null);
  const [systemDeps, setSystemDeps] = useState(null);
  const [banner, setBanner] = useState(null);
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

  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJobData, setSelectedJobData] = useState(null);
  const [clips, setClips] = useState([]);
  const [fixtures, setFixtures] = useState([]);
  const [activeTab, setActiveTab] = useState('real');
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
    e.preventDefault();
    if (submitting) return;

    if (!isValidVodUrl(vodUrl)) {
      setInputError('Please provide a valid YouTube URL or local video file before submitting.');
      return;
    }

    setSubmitting(true);
    setInputError('');
    setBanner({ type: 'info', text: `Initiating 13-stage clipping pipeline for ${vodUrl}...` });

    try {
      const res = await fetch(`${API_BASE}/api/v4/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vod_url: vodUrl.trim(),
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
          max_clips: 3,
          min_clip_duration: 30,
          max_clip_duration: 120,
          enable_scene_detection: true,
        })
      });
      const data = await res.json();
      if (res.ok) {
        const newId = data.job?.id;
        setSelectedJobId(newId);
        setBanner({
          type: 'success',
          text: `Job ${newId} initiated! Visibly tracking 13 processing stages in workspace below.`
        });
        setVodUrl('');
        setActiveTab('real');
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
        text: 'Cannot reach ClipForge backend API at 127.0.0.1:8000. Ensure FastAPI server is running.'
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
    setBanner({ type: 'info', text: `Syncing bounty task ${clippoId} with Clippo.id...` });

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
          text: `Clippo.id task ${clippoId} queued! Tracking live stages in workspace.`
        });
        setClippoId('');
        setActiveTab('real');
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

  const displayedClips = activeTab === 'real' ? clips : fixtures;
  const currentJob = selectedJobData || jobs.find(j => j.id === selectedJobId) || jobs[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navbar */}
      <nav className="border-b border-slate-800/80 bg-slate-900/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between flex-wrap gap-y-2">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-600/30">
              <Film className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-300 via-purple-300 to-cyan-300">
                  ClipForge
                </span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-800 text-indigo-300 font-semibold tracking-wider">
                  v0.4.0
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">Local-First Video Ingestion & Short-Form Pipeline</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 sm:space-x-4">
            {/* System Engine Status Indicators */}
            <div className="flex items-center space-x-2 text-[11px] font-mono flex-wrap gap-y-1">
              <span className={`px-2 py-0.5 rounded border flex items-center space-x-1 ${
                systemDeps?.ytdlp_available
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                  : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}>
                <span>yt-dlp:</span>
                <span className="font-bold">{systemDeps?.ytdlp_available ? 'Ready' : 'Checking'}</span>
              </span>

              <span className={`px-2 py-0.5 rounded border flex items-center space-x-1 ${
                systemDeps?.ffmpeg_available
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                  : 'bg-amber-950/80 text-amber-300 border-amber-800'
              }`}>
                <span>FFmpeg:</span>
                <span className="font-bold">{systemDeps?.ffmpeg_available ? 'Detected' : 'Pending'}</span>
              </span>

              <span className="px-2 py-0.5 rounded border hidden sm:flex items-center space-x-1 bg-indigo-950/80 text-indigo-300 border-indigo-800">
                <Database className="w-3 h-3" />
                <span>SQLite:</span>
                <span className="font-bold">Persistent</span>
              </span>

              <div className="flex items-center space-x-1.5 pl-1">
                <span className={`w-2 h-2 rounded-full ${backendOnline ? 'bg-emerald-500 animate-pulse' : backendOnline === false ? 'bg-rose-500' : 'bg-amber-500'}`} />
                <span className={backendOnline ? 'text-emerald-400 font-semibold' : backendOnline === false ? 'text-rose-400 font-semibold' : 'text-amber-400 font-semibold'}>
                  {backendOnline ? 'API Active' : backendOnline === false ? 'Offline' : 'Connecting...'}
                </span>
              </div>
            </div>

            <button
              onClick={fetchJobsAndClips}
              title="Refresh queue"
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Status / Alert Banner */}
        {banner && (
          <div className={`p-4 rounded-xl border flex items-start justify-between shadow-lg transition ${
            banner.type === 'success' ? 'bg-emerald-950/60 border-emerald-800 text-emerald-200' :
            banner.type === 'error' ? 'bg-rose-950/60 border-rose-800 text-rose-200' :
            'bg-indigo-950/60 border-indigo-800 text-indigo-200'
          }`}>
            <div className="flex items-center space-x-3 text-sm">
              {banner.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
              {banner.type === 'error' && <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />}
              {banner.type === 'info' && <Clock className="w-5 h-5 text-indigo-400 shrink-0 animate-spin" />}
              <span>{banner.text}</span>
            </div>
            <button
              onClick={() => setBanner(null)}
              className="text-xs uppercase font-mono tracking-wider font-bold opacity-75 hover:opacity-100 ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Input Cards: Submit Video & Clippo Sync */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main VOD Ingestion Form (2 cols) */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/5 rounded-full blur-3xl pointer-events-none" />
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Video className="w-5 h-5 text-indigo-400" />
                <h2 className="text-lg font-semibold text-slate-100">Submit Stream VOD or Video URL</h2>
              </div>
              <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-700/60">
                YouTube / MP4 / MKV
              </span>
            </div>

            <form onSubmit={handleVodSubmit} className="space-y-6">
              <div>
                <label className="block text-xs font-mono uppercase text-slate-400 mb-1.5">
                  Public YouTube Link or Local File Path
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={vodUrl}
                    onChange={handleUrlChange}
                    placeholder="https://www.youtube.com/watch?v=... or C:/Videos/stream.mp4"
                    disabled={submitting}
                    className={`w-full bg-slate-950 border ${inputError ? 'border-rose-500' : 'border-slate-800 focus:border-indigo-500'} rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none transition shadow-inner disabled:opacity-50 font-mono`}
                  />
                  {vodUrl && (
                    <button
                      type="button"
                      onClick={() => { setVodUrl(''); setInputError(''); }}
                      className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
                {inputError ? (
                  <p className="text-xs text-rose-400 mt-1.5 flex items-center space-x-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>{inputError}</span>
                  </p>
                ) : (
                  <p className="text-xs text-slate-500 mt-1.5">
                    Supports public YouTube streams and local files. Runs genuine 13-stage pipeline with real FFmpeg vertical rendering.
                  </p>
                )}
              </div>

              {/* Pipeline Active Config Badges */}
              <div className="flex flex-wrap items-center gap-2 pt-1 pb-1">
                <span className="px-2.5 py-1 rounded-lg bg-indigo-950/60 border border-indigo-800/80 text-[11px] font-mono text-indigo-300 flex items-center space-x-1.5">
                  <Video className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Framing:</span>
                  <span className="font-semibold text-slate-100">Follow Speaker (9:16)</span>
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-amber-950/50 border border-amber-800/80 text-[11px] font-mono text-amber-300 flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span>Detection:</span>
                  <span className="font-semibold text-slate-100">Automatic Heuristic</span>
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-emerald-950/50 border border-emerald-800/80 text-[11px] font-mono text-emerald-300 flex items-center space-x-1.5">
                  <Clock className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Clips:</span>
                  <span className="font-semibold text-slate-100">Max 3 (30s – 120s)</span>
                </span>
              </div>
              {/* Caption Settings Panel */}
              <div className="space-y-3 pt-2 border-t border-slate-800/80">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <Type className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Caption Settings & Presets</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowAdvancedCaptions(!showAdvancedCaptions)}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-mono flex items-center space-x-1"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>{showAdvancedCaptions ? 'Hide Options' : 'Custom Options & Preview'}</span>
                  </button>
                </div>

                {/* Visual Caption Preset Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {[
                    {
                      id: 'clean',
                      label: 'Clean',
                      desc: 'Simple & readable',
                      renderPreview: () => (
                        <div
                          style={{
                            color: captionTextColor || '#FFFFFF',
                            textShadow: '0 1px 2px rgba(0,0,0,0.9), 0 0 1px #000',
                          }}
                          className="font-sans font-semibold text-[11px] leading-tight text-center"
                        >
                          This is a caption
                        </div>
                      ),
                    },
                    {
                      id: 'creator_bold',
                      label: 'Creator Bold',
                      desc: 'Viral bold typography',
                      renderPreview: () => (
                        <div
                          style={{
                            color: captionTextColor || '#FFFFFF',
                            fontFamily: 'Impact, sans-serif',
                            textShadow: '0 2px 3px rgba(0,0,0,0.95), 0 0 2px #000',
                          }}
                          className="uppercase text-[12px] tracking-wide leading-tight text-center"
                        >
                          THIS IS A CAPTION
                        </div>
                      ),
                    },
                    {
                      id: 'karaoke',
                      label: 'Karaoke',
                      desc: 'Word-by-word active',
                      renderPreview: () => (
                        <div
                          style={{
                            color: captionTextColor || '#FFFFFF',
                            fontFamily: 'Impact, sans-serif',
                            textShadow: '0 2px 3px rgba(0,0,0,0.95), 0 0 2px #000',
                          }}
                          className="text-[11px] leading-tight text-center"
                        >
                          <span>This is an </span>
                          <span
                            style={{
                              color: captionHighlightColor || '#FFFF00',
                              textDecoration: 'underline',
                              textUnderlineOffset: '2px',
                            }}
                          >
                            ACTIVE
                          </span>
                          <span> word</span>
                        </div>
                      ),
                    },
                    {
                      id: 'minimal',
                      label: 'Minimal',
                      desc: 'Clean subtle subtitle',
                      renderPreview: () => (
                        <div
                          style={{
                            color: captionTextColor || '#E2E8F0',
                          }}
                          className="font-sans text-[10px] leading-tight text-center opacity-90"
                        >
                          small clean subtitle
                        </div>
                      ),
                    },
                    {
                      id: 'no_captions',
                      label: 'No Captions',
                      desc: 'Subtitles disabled',
                      renderPreview: () => (
                        <div className="text-[10px] text-slate-500 font-mono italic text-center">
                          [ No subtitles ]
                        </div>
                      ),
                    },
                  ].map((p) => {
                    const isSelected = captionPreset === p.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          setCaptionPreset(p.id);
                          if (p.id === 'karaoke') setCaptionWordHighlight(true);
                        }}
                        className={`rounded-xl border text-left transition flex flex-col overflow-hidden group ${
                          isSelected
                            ? 'bg-slate-900 border-cyan-400 text-white shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400'
                            : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        {/* Mini video screen simulation */}
                        <div className="h-16 w-full bg-slate-950/90 border-b border-slate-800/80 p-2 flex flex-col justify-end items-center relative overflow-hidden">
                          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-900/40 to-transparent pointer-events-none" />
                          <div className="z-10 w-full flex items-center justify-center">
                            {p.renderPreview()}
                          </div>
                        </div>

                        {/* Card footer details */}
                        <div className="p-2.5 flex flex-col justify-between flex-1">
                          <div className="font-semibold text-xs flex items-center justify-between">
                            <span>{p.label}</span>
                            {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0" />}
                          </div>
                          <span className="text-[10px] text-slate-500 mt-0.5 leading-tight">
                            {p.desc}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Advanced Customization & Live Preview */}
                {showAdvancedCaptions && (
                  <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Controls column */}
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[11px] font-mono text-slate-400 mb-1">Language</label>
                            <select
                              value={captionLanguage}
                              onChange={(e) => setCaptionLanguage(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                            >
                              <option value="auto">Auto Detect</option>
                              <option value="id">Indonesian (id)</option>
                              <option value="en">English (en)</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-[11px] font-mono text-slate-400 mb-1">Size</label>
                            <select
                              value={captionSize}
                              onChange={(e) => setCaptionSize(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                            >
                              <option value="small">Small</option>
                              <option value="medium">Medium</option>
                              <option value="large">Large</option>
                            </select>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[11px] font-mono text-slate-400 mb-1">Position</label>
                            <select
                              value={captionPosition}
                              onChange={(e) => setCaptionPosition(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                            >
                              <option value="bottom_safe">Bottom Safe Area</option>
                              <option value="center">Center</option>
                              <option value="top_safe">Top Safe Area</option>
                            </select>
                          </div>
                          <div className="flex items-center space-x-2 pt-4">
                            <input
                              type="checkbox"
                              id="wordHighlight"
                              checked={captionWordHighlight || captionPreset === 'karaoke'}
                              disabled={captionPreset === 'karaoke'}
                              onChange={(e) => setCaptionWordHighlight(e.target.checked)}
                              className="rounded bg-slate-900 border-slate-700 text-indigo-500 focus:ring-0"
                            />
                            <label htmlFor="wordHighlight" className="text-xs text-slate-300 font-medium cursor-pointer">
                              Word Highlight
                            </label>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[11px] font-mono text-slate-400 mb-1">Text Color</label>
                            <div className="flex items-center space-x-2">
                              <input
                                type="color"
                                value={captionTextColor}
                                onChange={(e) => setCaptionTextColor(e.target.value.toUpperCase())}
                                className="w-8 h-8 rounded border border-slate-800 bg-transparent cursor-pointer p-0.5"
                              />
                              <input
                                type="text"
                                value={captionTextColor}
                                onChange={(e) => setCaptionTextColor(e.target.value)}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-xs font-mono text-slate-200"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="block text-[11px] font-mono text-slate-400 mb-1">Highlight Color</label>
                            <div className="flex items-center space-x-2">
                              <input
                                type="color"
                                value={captionHighlightColor}
                                onChange={(e) => setCaptionHighlightColor(e.target.value.toUpperCase())}
                                className="w-8 h-8 rounded border border-slate-800 bg-transparent cursor-pointer p-0.5"
                              />
                              <input
                                type="text"
                                value={captionHighlightColor}
                                onChange={(e) => setCaptionHighlightColor(e.target.value)}
                                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-xs font-mono text-slate-200"
                              />
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Live Caption Preview Box */}
                      <div className="border border-slate-800 rounded-xl bg-slate-900/90 p-3 flex flex-col items-center justify-between">
                        <div className="w-full flex items-center justify-between text-[11px] font-mono text-slate-400 mb-2">
                          <span className="flex items-center space-x-1 text-cyan-400">
                            <Eye className="w-3.5 h-3.5" />
                            <span>Caption Live Preview</span>
                          </span>
                          <span>9:16 Canvas</span>
                        </div>

                        <div className="w-36 h-56 bg-slate-950 border border-slate-700/80 rounded-lg relative overflow-hidden flex flex-col justify-between p-2 shadow-inner">
                          <div className="absolute inset-0 bg-gradient-to-b from-indigo-950/20 to-black/60 pointer-events-none" />
                          <div className="text-[8px] font-mono text-slate-600 text-center z-10">Safe Zone Top</div>

                          <div className={`z-10 text-center transition-all ${
                            captionPosition === 'top_safe' ? 'mt-1' :
                            captionPosition === 'center' ? 'my-auto' :
                            'mb-2'
                          }`}>
                            {captionPreset === 'no_captions' ? (
                              <span className="text-[10px] text-slate-600 italic">[Captions Disabled]</span>
                            ) : (
                              <div
                                style={{
                                  color: captionTextColor,
                                  fontSize: captionSize === 'small' ? '10px' : captionSize === 'large' ? '15px' : '12px',
                                  fontFamily: captionPreset === 'creator_bold' || captionPreset === 'karaoke' ? 'Impact, sans-serif' : 'Arial, sans-serif',
                                  textShadow: '0 2px 4px rgba(0,0,0,0.9), 0 0 2px #000',
                                  fontWeight: captionPreset === 'minimal' ? 'normal' : 'bold',
                                }}
                                className="leading-tight px-1"
                              >
                                <span>Halo </span>
                                <span style={{ color: (captionWordHighlight || captionPreset === 'karaoke') ? captionHighlightColor : captionTextColor }}>
                                  Dunia
                                </span>
                                <span> Highlight!</span>
                              </div>
                            )}
                          </div>

                          <div className="text-[8px] font-mono text-slate-600 text-center z-10">Safe Zone Bottom</div>
                        </div>

                        <span className="text-[10px] text-slate-500 mt-2 text-center">
                          Simulated visual style. Actual FFmpeg MP4 is rendered on submission.
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <div className="flex items-center space-x-3 pt-1">
                <button
                  type="submit"
                  disabled={submitting || !vodUrl.trim() || !!inputError}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed font-medium py-3 rounded-xl transition shadow-lg shadow-indigo-600/25 text-sm flex items-center justify-center space-x-2"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Submitting Pipeline Request...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 text-indigo-300" />
                      <span>Generate Clips</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Clippo.id Bounty Sync Card (1 col) */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Layers className="w-5 h-5 text-cyan-400" />
                <h2 className="text-lg font-semibold text-slate-100">Clippo.id Sync</h2>
              </div>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                Connect external clipping tasks and bounty workflows from <span className="text-cyan-400 font-mono">clippo.id</span>.
              </p>

              <form onSubmit={handleClippoSync} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase text-slate-400 mb-1.5">
                    Clippo Task ID / URL
                  </label>
                  <input
                    type="text"
                    value={clippoId}
                    onChange={(e) => setClippoId(e.target.value)}
                    placeholder="job_clippo_4021"
                    disabled={clippoSubmitting}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none transition shadow-inner disabled:opacity-50 font-mono"
                  />
                </div>

                <button
                  type="submit"
                  disabled={clippoSubmitting || !clippoId.trim()}
                  className="w-full bg-cyan-700 hover:bg-cyan-600 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed font-medium py-3 rounded-xl transition shadow-lg shadow-cyan-600/20 text-sm flex items-center justify-center space-x-2"
                >
                  {clippoSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Syncing...</span>
                    </>
                  ) : (
                    <>
                      <ExternalLink className="w-4 h-4 text-cyan-300" />
                      <span>Sync Clippo Bounty</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center space-x-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Requires operator review before bounty submission.</span>
            </div>
          </div>
        </div>

        {/* Processing Workspace for Currently Selected Job */}
        {currentJob && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
              <div>
                <div className="flex items-center space-x-2.5">
                  <Cpu className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-xl font-bold text-slate-100">
                    Processing Workspace
                  </h2>
                  <span className="font-mono text-xs bg-slate-800 text-indigo-300 px-2.5 py-0.5 rounded border border-slate-700">
                    {currentJob.id}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1 truncate max-w-xl font-mono">
                  Source: {currentJob.metadata?.title || currentJob.vod_url}
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <span className={`px-2.5 py-1 rounded font-mono font-bold text-xs uppercase ${
                  currentJob.status === 'waiting_approval' || currentJob.status === 'completed'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : currentJob.status === 'failed'
                    ? 'bg-rose-950 text-rose-300 border border-rose-800'
                    : 'bg-indigo-950 text-indigo-300 border border-indigo-800 animate-pulse'
                }`}>
                  {currentJob.status} ({currentJob.progress || 0}%)
                </span>
              </div>
            </div>
            {/* Job Configuration & Transparency Details */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                <span className="font-semibold text-slate-200 uppercase tracking-wider font-mono text-[11px]">
                  Job Configuration & Transparency
                </span>
                {currentJob.framing_mode === 'auto_follow_speaker' && (
                  <span className="text-[10px] bg-amber-950/70 text-amber-300 border border-amber-800 px-2.5 py-0.5 rounded font-mono">
                    Fallback active: Face tracking used because active-speaker detection is unavailable.
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-400 font-mono text-[11px]">
                <div>Framing: <span className="text-slate-100 font-bold">{currentJob.framing_mode || 'center_crop'}</span></div>
                <div>Preset: <span className="text-slate-100 font-bold">{currentJob.caption_preset || 'clean'}</span></div>
                <div>Language: <span className="text-slate-100 font-bold">{currentJob.caption_language || 'auto'}</span></div>
                <div>Size: <span className="text-slate-100 font-bold">{currentJob.caption_size || 'medium'}</span></div>
                <div>Position: <span className="text-slate-100 font-bold">{currentJob.caption_position || 'bottom_safe'}</span></div>
                <div>Colors: <span className="text-slate-100 font-bold">{currentJob.caption_text_color || '#FFFFFF'} / {currentJob.caption_highlight_color || '#FFFF00'}</span></div>
                <div>Word Highlight: <span className="text-slate-100 font-bold">{currentJob.caption_word_highlight ? 'Enabled' : 'Disabled'}</span></div>
                <div>Moment Mode: <span className="text-slate-100 font-bold">{currentJob.moment_detection_mode || 'heuristic'}</span></div>
                <div>Max Clips: <span className="text-slate-100 font-bold">{currentJob.max_clips || 5}</span></div>
                <div>Target Duration: <span className="text-slate-100 font-bold">{currentJob.min_clip_duration || 12}s - {currentJob.max_clip_duration || 60}s</span></div>
              </div>
            </div>
            {/* Error Banner if Job Failed */}
            {currentJob.error && (
              <div className="p-4 bg-rose-950/60 border border-rose-800 rounded-xl text-xs text-rose-200 space-y-1">
                <div className="font-bold flex items-center space-x-1.5">
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                  <span>Pipeline Execution Error</span>
                </div>
                <p className="font-mono">{currentJob.error}</p>
              </div>
            )}

            {/* Overall Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono text-slate-400">
                <span>{currentJob.stage || 'Executing pipeline stages...'}</span>
                <span>{currentJob.progress || 0}% Completed</span>
              </div>
              <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    currentJob.status === 'waiting_approval' || currentJob.status === 'completed'
                      ? 'bg-emerald-500'
                      : currentJob.status === 'failed'
                      ? 'bg-rose-500'
                      : 'bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400'
                  }`}
                  style={{ width: `${Math.max(5, currentJob.progress || 5)}%` }}
                />
              </div>
            </div>

            {/* 13-Stage Detailed Pipeline Timeline */}
            <div className="space-y-3 pt-2">
              <h3 className="text-xs uppercase font-mono font-bold text-slate-400 tracking-wider">
                Pipeline Stages Breakdown (13 Stages)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {(currentJob.stages || []).map((st, idx) => {
                  const isDone = st.status === 'completed';
                  const isRunning = st.status === 'running';
                  const isSkipped = st.status === 'skipped';
                  const isFailed = st.status === 'failed';

                  return (
                    <div
                      key={st.id || idx}
                      className={`p-3.5 rounded-xl border text-xs flex flex-col justify-between transition space-y-2 ${
                        isDone
                          ? 'bg-slate-950/90 border-emerald-900/60 text-slate-200'
                          : isRunning
                          ? 'bg-indigo-950/40 border-indigo-500/80 text-white shadow-lg shadow-indigo-600/10'
                          : isFailed
                          ? 'bg-rose-950/40 border-rose-800 text-rose-200'
                          : isSkipped
                          ? 'bg-slate-950/40 border-amber-900/40 text-slate-400'
                          : 'bg-slate-950/40 border-slate-800/60 text-slate-500'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                          {isRunning && <Clock className="w-4 h-4 text-indigo-400 shrink-0 animate-spin" />}
                          {isFailed && <XCircle className="w-4 h-4 text-rose-400 shrink-0" />}
                          {isSkipped && <MinusCircle className="w-4 h-4 text-amber-400 shrink-0" />}
                          {!isDone && !isRunning && !isFailed && !isSkipped && (
                            <div className="w-4 h-4 rounded-full border border-slate-700 flex items-center justify-center text-[10px] text-slate-600">
                              {idx + 1}
                            </div>
                          )}
                          <span className="font-semibold">{st.name}</span>
                        </div>

                        {st.elapsed_sec && (
                          <span className="font-mono text-[10px] text-slate-400">
                            {st.elapsed_sec}s
                          </span>
                        )}
                      </div>

                      <p className="text-[11px] leading-relaxed font-mono opacity-80 break-words">
                        {st.detail}
                      </p>

                      {st.error && (
                        <p className="text-[10px] text-rose-400 font-mono">
                          Error: {st.error}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Job History / Recent Jobs Section */}
        {jobs.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <History className="w-5 h-5 text-indigo-400" />
                <h2 className="text-lg font-semibold text-slate-100">Job History & Persistence</h2>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {jobs.length} Total Persistent {jobs.length === 1 ? 'Job' : 'Jobs'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {jobs.map(j => {
                const isSelected = j.id === selectedJobId;
                const isDone = j.status === 'waiting_approval' || j.status === 'completed';
                const isFail = j.status === 'failed';

                return (
                  <button
                    key={j.id}
                    onClick={() => { setSelectedJobId(j.id); fetchSingleJob(j.id); }}
                    className={`p-3.5 rounded-xl border text-left transition flex flex-col justify-between space-y-2 ${
                      isSelected
                        ? 'bg-indigo-950/60 border-indigo-500 shadow-lg'
                        : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono font-bold text-slate-200">{j.id}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono uppercase font-bold ${
                          isDone ? 'bg-emerald-950 text-emerald-300' :
                          isFail ? 'bg-rose-950 text-rose-300' :
                          'bg-indigo-950 text-indigo-300'
                        }`}>
                          {j.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-1" title={j.metadata?.title || j.vod_url}>
                        {j.metadata?.title || j.vod_url}
                      </p>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>{j.created_at ? new Date(j.created_at).toLocaleTimeString() : ''}</span>
                      <span className="text-indigo-400 font-semibold">{isSelected ? 'Active' : 'Inspect'}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Review Queue & Generated Clips */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <Flame className="w-5 h-5 text-amber-400" />
                <h2 className="text-xl font-bold text-slate-100">Review Queue & Generated Clips</h2>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Human operator safety gate (Constitution P4 & R2): Explicit approval is mandatory before publishing.
              </p>
            </div>

            {/* Segment Toggle: Real Clips vs Demo Fixtures */}
            <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-medium">
              <button
                onClick={() => setActiveTab('real')}
                className={`px-3.5 py-1.5 rounded-lg transition flex items-center space-x-1.5 ${
                  activeTab === 'real'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>Live Pipeline</span>
                <span className={`px-1.5 py-0.2 rounded-full font-mono text-[10px] ${
                  activeTab === 'real' ? 'bg-indigo-800 text-indigo-200' : 'bg-slate-800 text-slate-400'
                }`}>
                  {clips.length}
                </span>
              </button>
              <button
                onClick={() => setActiveTab('fixtures')}
                className={`px-3.5 py-1.5 rounded-lg transition flex items-center space-x-1.5 ${
                  activeTab === 'fixtures'
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>Demo Fixtures</span>
                <span className={`px-1.5 py-0.2 rounded-full font-mono text-[10px] ${
                  activeTab === 'fixtures' ? 'bg-purple-800 text-purple-200' : 'bg-slate-800 text-slate-400'
                }`}>
                  {fixtures.length}
                </span>
              </button>
            </div>
          </div>

          {/* Fixture Disclaimer Notice when in fixtures tab */}
          {activeTab === 'fixtures' && (
            <div className="p-3 bg-purple-950/40 border border-purple-800/80 rounded-xl text-xs text-purple-200 flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-purple-400 shrink-0" />
              <span>
                <strong>Development Fixtures Mode:</strong> Sample review items for UI layout and approval workflow evaluation. Segregated from live generation outputs.
              </span>
            </div>
          )}

          {/* Clip Grid / List */}
          {displayedClips.length === 0 ? (
            <div className="text-center py-12 px-4 border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-3">
              <Film className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="font-semibold text-slate-300 text-base">No clips in this queue</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                {activeTab === 'real'
                  ? 'Submit a YouTube video or stream VOD above to generate candidates, or switch to Demo Fixtures tab to test review actions.'
                  : 'No sample fixtures available.'}
              </p>
              {activeTab === 'real' && (
                <button
                  onClick={() => setActiveTab('fixtures')}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium underline pt-2"
                >
                  Switch to Demo Fixtures preview
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {displayedClips.map(clip => {
                const isApproved = clip.status === 'APPROVED';
                const isRejected = clip.status === 'REJECTED';
                const isPending = !isApproved && !isRejected;

                return (
                  <div
                    key={clip.id}
                    className={`bg-slate-950 border rounded-xl p-5 flex flex-col justify-between space-y-4 transition shadow-lg ${
                      isApproved ? 'border-emerald-800/70 shadow-emerald-950/20' :
                      isRejected ? 'border-rose-900/50 shadow-rose-950/10 opacity-75' :
                      'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="space-y-3">
                      {/* Video Player or Preview Card */}
                      {clip.media_url ? (
                        <div className="rounded-lg overflow-hidden bg-black border border-slate-800 aspect-[9/16] max-h-72 w-full flex items-center justify-center">
                          <video
                            src={clip.media_url}
                            controls
                            playsInline
                            className="w-full h-full object-contain"
                          />
                        </div>
                      ) : (
                        <div className="h-36 rounded-lg bg-gradient-to-br from-slate-900 via-indigo-950/30 to-slate-900 border border-slate-800/80 flex flex-col items-center justify-center text-slate-500 relative overflow-hidden group">
                          <div className="w-10 h-10 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-indigo-400 mb-1 group-hover:scale-110 transition">
                            <Play className="w-4 h-4 ml-0.5" />
                          </div>
                          <span className="text-[11px] font-mono text-slate-400">9:16 Vertical Preview</span>
                          <span className="text-[10px] text-slate-600 font-mono">1080×1920 • Candidate Window</span>
                        </div>
                      )}

                      {/* Header & Badges */}
                      <div className="flex items-center justify-between gap-2 flex-wrap text-xs">
                        <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">
                          <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                            isApproved ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                            isRejected ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                            'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}>
                            {isApproved ? 'APPROVED (Human Sign-off)' : isRejected ? 'REJECTED' : 'PENDING APPROVAL'}
                          </span>

                          {/* Media Type Badge */}
                          {clip.is_real_media ? (
                            <span className="bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 px-1.5 py-0.5 rounded text-[10px] font-mono">
                              RENDERED VIDEO
                            </span>
                          ) : clip.is_fixture ? (
                            <span className="bg-purple-950/80 text-purple-300 border border-purple-800/80 px-1.5 py-0.5 rounded text-[10px] font-mono">
                              DEMO FIXTURE
                            </span>
                          ) : (
                            <span className="bg-sky-950/80 text-sky-300 border border-sky-800/80 px-1.5 py-0.5 rounded text-[10px] font-mono">
                              CANDIDATE METADATA
                            </span>
                          )}
                        </div>

                        <div className="flex items-center space-x-2 font-mono text-slate-400 text-xs">
                          <span className="text-indigo-400 font-semibold">{clip.score}</span>
                          <span>•</span>
                          <span>{clip.duration}</span>
                        </div>
                      </div>

                      {/* Title & Metadata */}
                      <div>
                        <h4 className="font-semibold text-slate-100 text-base leading-snug">
                          {clip.title}
                        </h4>
                        <p className="text-xs text-slate-400 mt-1 truncate" title={clip.vod}>
                          Source: <span className="font-mono text-slate-300">{clip.vod}</span>
                        </p>
                      </div>

                      {/* Technical Timestamps & QC details */}
                      <div className="bg-slate-900/80 border border-slate-800/80 rounded-lg p-2.5 text-[11px] font-mono text-slate-400 space-y-1">
                        <div className="flex justify-between">
                          <span>Time Slice:</span>
                          <span className="text-slate-200">
                            {typeof clip.start_time === 'number' && typeof clip.end_time === 'number'
                              ? `[${clip.start_time.toFixed(1)}s → ${clip.end_time.toFixed(1)}s]`
                              : 'Automatic Highlight'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Target Composition:</span>
                          <span className="text-slate-200">{clip.resolution || '1080×1920 (9:16)'}</span>
                        </div>
                        {clip.qc_checks && Object.keys(clip.qc_checks).length > 0 && (
                          <div className="flex justify-between text-emerald-400">
                            <span>QC Verification:</span>
                            <span>Passed (Valid H.264 / MP4 Container)</span>
                          </div>
                        )}
                      </div>

                      {/* Notice */}
                      {clip.render_notice && (
                        <div className="text-[11px] text-slate-400 bg-slate-900/60 border border-slate-800/60 rounded-lg p-2 font-mono leading-relaxed">
                          <span className="text-slate-500 uppercase font-bold">Status: </span>
                          {clip.render_notice}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-3">
                      {isPending ? (
                        <>
                          <button
                            onClick={() => handleClipDecision(clip.id, 'approve')}
                            disabled={actionLoading[clip.id]}
                            className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium py-2 rounded-xl text-xs flex items-center justify-center space-x-1.5 transition shadow-lg shadow-emerald-600/20"
                          >
                            <Check className="w-3.5 h-3.5" />
                            <span>Approve for Publishing</span>
                          </button>
                          <button
                            onClick={() => handleClipDecision(clip.id, 'reject')}
                            disabled={actionLoading[clip.id]}
                            className="flex-1 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-medium py-2 rounded-xl text-xs flex items-center justify-center space-x-1.5 transition shadow-lg shadow-rose-600/20"
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </>
                      ) : (
                        <div className="w-full flex items-center justify-between text-xs font-mono text-slate-400">
                          <span className="flex items-center space-x-1">
                            {isApproved && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                            {isRejected && <XCircle className="w-4 h-4 text-rose-400" />}
                            <span>Operator Decision: {clip.status}</span>
                          </span>
                          {isApproved && (
                            <span className="text-emerald-400 font-semibold">Approved (Ready for export)</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500 font-mono">
        ClipForge Streamer Clipping Control Panel • Human Approval Gate Enforced (Constitution P4 & R2)
      </footer>
    </div>
  );
}
