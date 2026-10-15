'use client';

import { useState, useRef, useEffect } from 'react';
import {
  X,
  Play,
  Pause,
  Scissors,
  Plus,
  Trash2,
  Check,
  ShieldCheck,
  Download,
  Film,
  Type,
  Sliders,
  Sparkles,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  RotateCw,
  Volume2,
  VolumeX,
  Crop,
  Video,
  Save,
  AlertTriangle
} from 'lucide-react';
import HyperFramesCanvasOverlay from './HyperFramesEditor/HyperFramesCanvasOverlay';
import HookEditor from './HyperFramesEditor/HookEditor';
import HyperFramesLayers from './HyperFramesEditor/HyperFramesLayers';

export default function ClipModal({
  clip,
  onClose,
  onClipDecision,
  actionLoading
}) {
  if (!clip) return null;

  const videoRef = useRef(null);
  const timelineRef = useRef(null);

  // Video playback & timeline state
  const totalDuration = parseFloat(clip.duration || 18.4) || 18.4;
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1); // 1x to 2x

  // In/Out Trimming bounds
  const [trimStart, setTrimStart] = useState(clip.start_time !== undefined ? clip.start_time : 0.0);
  const [trimEnd, setTrimEnd] = useState(clip.end_time !== undefined ? clip.end_time : totalDuration);

  // P5 Editor State & Versioning
  const [editorVersion, setEditorVersion] = useState(1);
  const [editorStatus, setEditorStatus] = useState('DRAFT');
  const [autosaveStatus, setAutosaveStatus] = useState('Saved v1');
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);

  // P5 Audio State
  const [volume, setVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);

  // P5 Manual Crop & Layout Override
  const [cropMode, setCropMode] = useState('auto'); // 'auto' | 'manual'
  const [cropX, setCropX] = useState(0.0);
  const [cropY, setCropY] = useState(0.0);
  const [cropScale, setCropScale] = useState(1.0);
  const [layoutMode, setLayoutMode] = useState(clip.layout_mode || 'AUTO');

  // P5 Preview & Render Status
  const [isRenderingPreview, setIsRenderingPreview] = useState(false);
  const [isRenderingFinal, setIsRenderingFinal] = useState(false);
  const [activeRenderJobId, setActiveRenderJobId] = useState(null);
  const [videoSrc, setVideoSrc] = useState(clip.media_url);

  // CapCut-style Subtitle Layer Chunks
  const [captions, setCaptions] = useState([
    {
      id: 1,
      start: 0.0,
      end: Math.min(3.8, totalDuration * 0.25),
      text: 'Turn long stream moments',
      highlightWord: 'moments'
    },
    {
      id: 2,
      start: Math.min(3.8, totalDuration * 0.25),
      end: Math.min(8.5, totalDuration * 0.5),
      text: 'Audio energy peaked right here',
      highlightWord: 'peaked'
    },
    {
      id: 3,
      start: Math.min(8.5, totalDuration * 0.5),
      end: Math.min(13.5, totalDuration * 0.75),
      text: 'Unbelievable clutch in final zone',
      highlightWord: 'clutch'
    },
    {
      id: 4,
      start: Math.min(13.5, totalDuration * 0.75),
      end: totalDuration,
      text: 'Ready for TikTok and Reels',
      highlightWord: 'TikTok'
    }
  ]);

  const [selectedCaptionId, setSelectedCaptionId] = useState(1);
  const [activeInspectorTab, setActiveInspectorTab] = useState('caption'); // 'caption', 'style', 'export'

  // Subtitle styling options
  const [captionSize, setCaptionSize] = useState('medium');
  const [captionPosition, setCaptionPosition] = useState('bottom_safe');
  const [captionColor, setCaptionColor] = useState('#FFFFFF');
  const [highlightColor, setHighlightColor] = useState('#FBBF24');
  // HyperFrames Composition State (P6)
  const [composition, setComposition] = useState(clip.composition || null);
  const [selectedLayerId, setSelectedLayerId] = useState('layer_hook_title');
  const [showHyperframesPreview, setShowHyperframesPreview] = useState(true);

  // Export settings
  const [exportRes, setExportRes] = useState('1080p');
  const [exportPlatform, setExportPlatform] = useState('hyperframes');
  const [exporting, setExporting] = useState(false);
  const [exportDone, setExportDone] = useState(false);
  const isApproved = clip.status === 'APPROVED';
  const isRejected = clip.status === 'REJECTED';
  const isWaiting = !isApproved && !isRejected;
  const isLoading = actionLoading[clip.id];

  // Snapshot generator for undo/redo
  const getSnapshot = () => ({
    trimStart,
    trimEnd,
    captions: JSON.parse(JSON.stringify(captions)),
    cropMode,
    cropX,
    cropY,
    cropScale,
    layoutMode,
    volume,
    isMuted,
    composition: composition ? JSON.parse(JSON.stringify(composition)) : null,
  });

  const pushUndo = () => {
    setUndoStack((prev) => [...prev.slice(-30), getSnapshot()]);
    setRedoStack([]);
  };

  const handleUndo = () => {
    if (undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    setUndoStack((s) => s.slice(0, -1));
    setRedoStack((s) => [...s, getSnapshot()]);

    setTrimStart(prev.trimStart);
    setTrimEnd(prev.trimEnd);
    setCaptions(prev.captions);
    setCropMode(prev.cropMode);
    setCropX(prev.cropX);
    setCropY(prev.cropY);
    setCropScale(prev.cropScale);
    setLayoutMode(prev.layoutMode);
    setVolume(prev.volume);
    setIsMuted(prev.isMuted);
    if (prev.composition) setComposition(prev.composition);
  };

  const handleRedo = () => {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setRedoStack((s) => s.slice(0, -1));
    setUndoStack((s) => [...s, getSnapshot()]);

    setTrimStart(next.trimStart);
    setTrimEnd(next.trimEnd);
    setCaptions(next.captions);
    setCropMode(next.cropMode);
    setCropX(next.cropX);
    setCropY(next.cropY);
    setCropScale(next.cropScale);
    setLayoutMode(next.layoutMode);
    setVolume(next.volume);
    setIsMuted(next.isMuted);
    if (next.composition) setComposition(next.composition);
  };

  // Load editor state from backend on mount
  useEffect(() => {
    if (!clip?.id) return;
    const fetchState = async () => {
      try {
        const res = await fetch(`/api/v4/editor/${clip.id}`);
        if (res.ok) {
          const data = await res.json();
          if (data.state) {
            const st = data.state;
            setEditorVersion(st.editor_version || 1);
            setEditorStatus(st.status || 'DRAFT');
            setAutosaveStatus(`Saved v${st.editor_version || 1}`);
            if (st.source_start !== undefined) setTrimStart(st.source_start);
            if (st.source_end !== undefined) setTrimEnd(st.source_end);
            if (st.captions && st.captions.length > 0) setCaptions(st.captions);
            if (st.crop) {
              setCropMode(st.crop.mode || 'auto');
              setCropX(st.crop.x || 0.0);
              setCropY(st.crop.y || 0.0);
              setCropScale(st.crop.scale || 1.0);
            }
            if (st.layout) setLayoutMode(st.layout);
            if (st.audio) {
              setVolume(st.audio.volume !== undefined ? st.audio.volume : 1.0);
              setIsMuted(Boolean(st.audio.mute));
              if (st.user_overrides?.composition) {
                setComposition(st.user_overrides.composition);
              } else if (clip.composition) {
                setComposition(clip.composition);
              }
            }
          }
        }
      } catch (e) {}
    };
    fetchState();
  }, [clip.id]);

  // Debounced Autosave to backend
  const triggerAutosave = async () => {
    setAutosaveStatus('Saving...');
    try {
      const payload = {
        clip_id: clip.id,
        source_id: clip.media_url || clip.vod || 'data/input/real_talk_35s.mp4',
        source_start: trimStart,
        source_end: trimEnd,
        crop: { x: cropX, y: cropY, width: 1.0, height: 1.0, scale: cropScale, mode: cropMode },
        layout: layoutMode,
        captions: captions,
        audio: { volume: isMuted ? 0.0 : volume, mute: isMuted },
        editor_version: editorVersion + 1,
        status: editorStatus,
        user_overrides: {
          composition: composition,
        },
      };
      const res = await fetch(`/api/v4/editor/${clip.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        setEditorVersion(data.state?.editor_version || editorVersion + 1);
        setAutosaveStatus(`Saved v${data.state?.editor_version || editorVersion + 1}`);
      }
    } catch (e) {
      setAutosaveStatus('Save failed');
    }
  };

  const handleRenderPreview = async () => {
    setIsRenderingPreview(true);
    await triggerAutosave();
    try {
      const res = await fetch(`/api/v4/editor/${clip.id}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: 'preview' }),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveRenderJobId(data.job?.id);
      }
    } catch (e) {} finally {
      setIsRenderingPreview(false);
    }
  };

  const handleRenderFinal = async () => {
    setIsRenderingFinal(true);
    await triggerAutosave();
    try {
      const res = await fetch(`/api/v4/editor/${clip.id}/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: exportPlatform || 'tiktok' }),
      });
      if (res.ok) {
        setExportDone(true);
      }
    } catch (e) {} finally {
      setIsRenderingFinal(false);
    }
  };

  // Selected caption chunk
  const activeCaption = captions.find((c) => c.id === selectedCaptionId) || captions[0];

  // Find currently active caption at playhead time for monitor overlay
  const visibleCaption = captions.find(
    (c) => currentTime >= c.start && currentTime <= c.end
  );

  // Sync video time to state
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  // Seek video and playhead
  const seekTo = (time) => {
    const clamped = Math.max(0, Math.min(totalDuration, time));
    setCurrentTime(clamped);
    if (videoRef.current) {
      videoRef.current.currentTime = clamped;
    }
  };

  // Keyboard shortcuts (Space = Play/Pause, Left/Right = Seek, Esc = Close)
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in a textarea or input
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        seekTo(currentTime - 1);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        seekTo(currentTime + 1);
      } else if (e.code === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentTime, isPlaying]);

  // Click on timeline to scrub
  const handleTimelineClick = (e) => {
    if (!timelineRef.current) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percent = Math.max(0, Math.min(1, clickX / rect.width));
    seekTo(percent * totalDuration);
  };

  // Split selected caption at current playhead
  const handleSplitCaption = () => {
    if (!activeCaption) return;
    if (currentTime <= activeCaption.start || currentTime >= activeCaption.end) return;

    const firstHalf = {
      ...activeCaption,
      end: currentTime
    };
    const secondHalf = {
      id: Date.now(),
      start: currentTime,
      end: activeCaption.end,
      text: activeCaption.text,
      highlightWord: ''
    };

    setCaptions((prev) =>
      prev
        .map((c) => (c.id === activeCaption.id ? firstHalf : c))
        .concat(secondHalf)
        .sort((a, b) => a.start - b.start)
    );
    setSelectedCaptionId(secondHalf.id);
  };

  // Add new caption chunk
  const handleAddCaption = () => {
    const newChunk = {
      id: Date.now(),
      start: currentTime,
      end: Math.min(totalDuration, currentTime + 3.0),
      text: 'New subtitle block…',
      highlightWord: ''
    };
    setCaptions((prev) => [...prev, newChunk].sort((a, b) => a.start - b.start));
    setSelectedCaptionId(newChunk.id);
  };

  // Delete caption chunk
  const handleDeleteCaption = (id) => {
    if (captions.length <= 1) return;
    const remaining = captions.filter((c) => c.id !== id);
    setCaptions(remaining);
    setSelectedCaptionId(remaining[0].id);
  };

  // Update active caption text
  const updateActiveText = (text) => {
    setCaptions((prev) =>
      prev.map((c) => (c.id === selectedCaptionId ? { ...c, text } : c))
    );
  };

  const updateActiveTiming = (field, val) => {
    const num = parseFloat(val) || 0;
    setCaptions((prev) =>
      prev.map((c) => (c.id === selectedCaptionId ? { ...c, [field]: num } : c))
    );
  };

  const handleExport = () => {
    setExporting(true);
    setTimeout(() => {
      setExporting(false);
      setExportDone(true);
      setTimeout(() => setExportDone(false), 3000);
    }, 1500);
  };

  // Format seconds to mm:ss.s
  const formatTimecode = (sec) => {
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(1);
    return `${m.toString().padStart(2, '0')}:${s.padStart(4, '0')}`;
  };

  // Percentage position of playhead
  const playheadPercent = (currentTime / totalDuration) * 100;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="CapCut Multi-Track Video & Caption Studio"
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/85 backdrop-blur-md overscroll-contain select-none"
    >
      <div className="relative w-full max-w-5xl h-[92vh] max-h-[900px] rounded-xl bg-[#0e1017] border border-[#293245] shadow-2xl flex flex-col overflow-hidden text-slate-100">
        {/* Top Studio Bar */}
        <div className="h-11 px-4 border-b border-[#293245] bg-[#12141d] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 font-semibold text-xs text-white">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span>CapCut Editor</span>
              <span className="text-slate-500 font-mono text-[10px] font-normal">
                Multi-Track Timeline
              </span>
            </div>

            <div className="h-3.5 w-px bg-[#293245]" />

            <div className="text-[11px] text-slate-400 font-mono tabular-nums">
              {clip.title || `Clip #${clip.id}`}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* P5 Undo / Redo & Autosave */}
            <div className="flex items-center gap-1 bg-[#141722] p-0.5 rounded border border-[#4c5e6b]">
              <button
                type="button"
                onClick={handleUndo}
                disabled={undoStack.length === 0}
                title="Undo (Ctrl+Z)"
                className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleRedo}
                disabled={redoStack.length === 0}
                title="Redo (Ctrl+Y)"
                className="p-1 rounded text-slate-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-2 py-0.5 rounded">
              {autosaveStatus}
            </span>

            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#1a1e2a] text-slate-300 border border-[#4c5e6b] tabular-nums">
              Score: {clip.score || '90/100'}
            </span>

            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                isApproved
                  ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/40'
                  : isRejected
                  ? 'bg-rose-950/40 text-rose-400 border border-rose-800/40'
                  : 'bg-amber-950/40 text-amber-300 border border-amber-800/40'
              }`}
            >
              {clip.status || 'WAITING_APPROVAL'}
            </span>

            <button
              onClick={onClose}
              aria-label="Close clip editor"
              className="p-1 rounded bg-[#1a1e2a] hover:bg-[#252b3c] text-slate-400 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#aab9c7]"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Middle Stage: 9:16 Video Monitor (Left) & Layer Inspector (Right) */}
        <div className="flex-1 min-h-0 flex flex-col sm:flex-row overflow-hidden border-b border-[#293245]">
          {/* Left: 9:16 Video Monitor Preview */}
          <div className="w-full sm:w-[320px] lg:w-[360px] bg-[#08090d] p-3 flex flex-col items-center justify-center shrink-0 border-r border-[#293245] relative">
            <div className="w-[185px] h-[330px] rounded-lg bg-black border border-[#293245] overflow-hidden relative shadow-2xl flex flex-col justify-between">
              {clip.media_url ? (
                <video
                  ref={videoRef}
                  src={clip.media_url}
                  onTimeUpdate={handleTimeUpdate}
                  onEnded={() => setIsPlaying(false)}
                  className="w-full h-full object-cover cursor-pointer"
                  onClick={togglePlay}
                />
              ) : (
                <div
                  onClick={togglePlay}
                  className="w-full h-full bg-gradient-to-b from-[#141824] via-[#0f1118] to-black flex items-center justify-center cursor-pointer relative"
                >
                  <div className="w-12 h-12 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center text-white shadow-xl hover:scale-105 transition-transform">
                    {isPlaying ? (
                      <Pause className="w-5 h-5" aria-hidden="true" />
                    ) : (
                      <Play className="w-5 h-5 ml-0.5" aria-hidden="true" />
                    )}
                  </div>
                </div>
              )}

              {/* TAB: REFRAME & CROP (P5.7 & P5.8) */}
              {activeInspectorTab === 'reframe' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Framing Override Mode</label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('auto'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'auto' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Auto (AI Smart Face)
                      </button>
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('manual'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'manual' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Manual Position
                      </button>
                    </div>
                  </div>

                  {cropMode === 'manual' && (
                    <div className="space-y-2.5 p-2.5 bg-[#13151f] rounded-lg border border-[#293245]">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Horizontal Crop X:</span>
                          <span className="font-mono text-white">{Math.round(cropX * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min="0.0"
                          max="1.0"
                          step="0.02"
                          value={cropX}
                          onChange={(e) => setCropX(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Crop Scale:</span>
                          <span className="font-mono text-white">{cropScale.toFixed(2)}x</span>
                        </div>
                        <input
                          type="range"
                          min="0.8"
                          max="1.8"
                          step="0.05"
                          value={cropScale}
                          onChange={(e) => setCropScale(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Multi-Speaker Layout</label>
                    <div className="grid grid-cols-3 gap-1.5 font-mono text-[11px]">
                      {['AUTO', 'TRACK', 'SPLIT'].map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => { pushUndo(); setLayoutMode(m); triggerAutosave(); }}
                          className={`py-1.5 rounded border transition ${layoutMode === m ? 'bg-purple-950/80 border-purple-600 text-purple-200 font-bold' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB: AUDIO CONTROLS (P5.9) */}
              {activeInspectorTab === 'audio' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>Volume Gain:</span>
                      <span className="font-mono text-white">{Math.round(volume * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="2.0"
                      step="0.05"
                      value={volume}
                      disabled={isMuted}
                      onChange={(e) => setVolume(parseFloat(e.target.value))}
                      onMouseUp={triggerAutosave}
                      className="w-full accent-emerald-400"
                    />
                  </div>
                  <label className="flex items-center space-x-2 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={isMuted}
                      onChange={(e) => { setIsMuted(e.target.checked); triggerAutosave(); }}
                      className="rounded bg-slate-900 border-slate-700 text-rose-500"
                    />
                    <span className="text-slate-300 font-medium">Mute Clip Audio</span>
                  </label>
                </div>
              )}

              {/* HyperFrames Interactive Canvas Overlay (P6) */}
              {showHyperframesPreview ? (
                <HyperFramesCanvasOverlay
                  composition={composition}
                  currentTime={currentTime}
                  selectedLayerId={selectedLayerId}
                  setSelectedLayerId={setSelectedLayerId}
                  onUpdateLayer={(updated) => {
                    pushUndo();
                    setComposition((prev) => ({
                      ...prev,
                      layers: (prev?.layers || []).map((l) => (l.id === updated.id ? updated : l)),
                    }));
                    triggerAutosave();
                  }}
                  activeCaptionText={visibleCaption ? visibleCaption.text : ''}
                />
              ) : (
                <div
                  className={`absolute left-0 right-0 px-2 text-center pointer-events-none transition-all ${
                    captionPosition === 'top'
                      ? 'top-4'
                      : captionPosition === 'center'
                      ? 'top-1/2 -translate-y-1/2'
                      : 'bottom-6'
                  }`}
                >
                  {visibleCaption && (
                    <div
                      className="inline-block px-2 py-1 rounded font-extrabold tracking-tight drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)] text-[13px]"
                      style={{ color: captionColor }}
                    >
                      <span>{visibleCaption.text}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Timecode badge on monitor */}
              <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/70 backdrop-blur-sm font-mono text-[10px] text-slate-300 tabular-nums">
                {formatTimecode(currentTime)} / {formatTimecode(totalDuration)}
              </div>
            </div>

            {/* HyperFrames Live Toggle */}
            <div className="mt-2.5 flex items-center justify-between w-[185px]">
              <button
                type="button"
                onClick={() => setShowHyperframesPreview(!showHyperframesPreview)}
                className={`w-full py-1 rounded text-[10px] font-mono border transition-colors text-center ${
                  showHyperframesPreview
                    ? 'bg-[#252b3d] text-amber-300 border-amber-400'
                    : 'bg-[#13151f] text-slate-500 border-[#293245]'
                }`}
              >
                ★ HyperFrames DOM: {showHyperframesPreview ? 'ON' : 'OFF'}
              </button>
            </div>
          </div>

          {/* Right: Inspector Panel */}
          <div className="flex-1 bg-[#12141d] p-4 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-4">
              {/* Inspector Navigation Tabs */}
              <div className="flex items-center gap-1 bg-[#13151f] p-1 rounded-md border border-[#293245]">
                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('caption')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'caption'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Type className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
                  <span>Subtitle Chunk</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('hook')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'hook'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
                  <span>Hook Cover</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('layers')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'layers'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 text-blue-400" aria-hidden="true" />
                  <span>Layers</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('style')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'style'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sliders className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
                  <span>Caption Style</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('reframe')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'reframe'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Crop className="w-3.5 h-3.5 text-purple-400" aria-hidden="true" />
                  <span>Crop/Layout</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('audio')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'audio'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Volume2 className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                  <span>Audio</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveInspectorTab('export')}
                  className={`flex-1 py-1 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    activeInspectorTab === 'export'
                      ? 'bg-[#293245] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Download className="w-3.5 h-3.5 text-blue-400" aria-hidden="true" />
                  <span>Export Package</span>
                </button>
              </div>

              {/* TAB 1: SUBTITLE CHUNK EDITOR */}
              {activeInspectorTab === 'caption' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-cyan-400" />
                      Active Chunk #{activeCaption?.id}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono tabular-nums">
                      {formatTimecode(activeCaption?.start || 0)} → {formatTimecode(activeCaption?.end || 0)} (
                      {((activeCaption?.end || 0) - (activeCaption?.start || 0)).toFixed(1)}s)
                    </span>
                  </div>

                  <div>
                    <label htmlFor="inspector-caption-text" className="text-[11px] text-slate-400 block mb-1">
                      Spoken Subtitle Text:
                    </label>
                    <textarea
                      id="inspector-caption-text"
                      rows={3}
                      value={activeCaption?.text || ''}
                      onChange={(e) => updateActiveText(e.target.value)}
                      placeholder="Type subtitle words here…"
                      className="w-full p-2.5 rounded bg-[#13151f] border border-[#293245] text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans leading-relaxed"
                    />
                  </div>

                  {/* Timing Adjusters */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="caption-start-time" className="text-[11px] text-slate-400 block mb-1">
                        Start Time (s):
                      </label>
                      <input
                        id="caption-start-time"
                        type="number"
                        step="0.1"
                        value={activeCaption?.start || 0}
                        onChange={(e) => updateActiveTiming('start', e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-white font-mono"
                      />
                    </div>
                    <div>
                      <label htmlFor="caption-end-time" className="text-[11px] text-slate-400 block mb-1">
                        End Time (s):
                      </label>
                      <input
                        id="caption-end-time"
                        type="number"
                        step="0.1"
                        value={activeCaption?.end || 0}
                        onChange={(e) => updateActiveTiming('end', e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-white font-mono"
                      />
                    </div>
                  </div>

                  {/* Chunk Actions */}
                  <div className="pt-2 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => handleDeleteCaption(activeCaption.id)}
                      disabled={captions.length <= 1}
                      className="px-2.5 py-1 rounded bg-[#221517] text-rose-300 hover:bg-rose-950/60 border border-rose-900/40 text-xs font-medium flex items-center gap-1 disabled:opacity-40 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" aria-hidden="true" />
                      <span>Delete Chunk</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => seekTo(activeCaption.start)}
                      className="px-2.5 py-1 rounded bg-[#1e2333] text-slate-300 hover:text-white border border-[#4c5e6b] text-xs font-medium transition-colors"
                    >
                      Jump to Start
                    </button>
                  </div>
                </div>
              )}

              {/* TAB: HOOK COVER EDITOR (P6) */}
              {activeInspectorTab === 'hook' && (
                <HookEditor
                  hookLayer={composition?.layers?.find((l) => l.type === 'hook')}
                  onUpdateHook={(updated) => {
                    pushUndo();
                    setComposition((prev) => ({
                      ...prev,
                      layers: (prev?.layers || []).map((l) => (l.id === updated.id ? updated : l)),
                    }));
                    triggerAutosave();
                  }}
                />
              )}

              {/* TAB: LAYERS & MOTION (P6) */}
              {activeInspectorTab === 'layers' && (
                <HyperFramesLayers
                  layers={composition?.layers || []}
                  selectedLayerId={selectedLayerId}
                  setSelectedLayerId={setSelectedLayerId}
                  onUpdateLayer={(updated) => {
                    pushUndo();
                    setComposition((prev) => ({
                      ...prev,
                      layers: (prev?.layers || []).map((l) => (l.id === updated.id ? updated : l)),
                    }));
                    triggerAutosave();
                  }}
                  onReorderLayers={(newLayers) => {
                    pushUndo();
                    setComposition((prev) => ({ ...prev, layers: newLayers }));
                    triggerAutosave();
                  }}
                />
              )}

              {/* TAB: REFRAME & CROP (P5.7 & P5.8) */}
              {activeInspectorTab === 'reframe' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Framing Override Mode</label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('auto'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'auto' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Auto (AI Smart Face)
                      </button>
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('manual'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'manual' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Manual Position
                      </button>
                    </div>
                  </div>

                  {cropMode === 'manual' && (
                    <div className="space-y-2.5 p-2.5 bg-[#13151f] rounded-lg border border-[#293245]">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Horizontal Crop X:</span>
                          <span className="font-mono text-white">{Math.round(cropX * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min="0.0"
                          max="1.0"
                          step="0.02"
                          value={cropX}
                          onChange={(e) => setCropX(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Crop Scale:</span>
                          <span className="font-mono text-white">{cropScale.toFixed(2)}x</span>
                        </div>
                        <input
                          type="range"
                          min="0.8"
                          max="1.8"
                          step="0.05"
                          value={cropScale}
                          onChange={(e) => setCropScale(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Multi-Speaker Layout</label>
                    <div className="grid grid-cols-3 gap-1.5 font-mono text-[11px]">
                      {['AUTO', 'TRACK', 'SPLIT'].map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => { pushUndo(); setLayoutMode(m); triggerAutosave(); }}
                          className={`py-1.5 rounded border transition ${layoutMode === m ? 'bg-purple-950/80 border-purple-600 text-purple-200 font-bold' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB: AUDIO CONTROLS (P5.9) */}
              {activeInspectorTab === 'audio' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>Volume Gain:</span>
                      <span className="font-mono text-white">{Math.round(volume * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="2.0"
                      step="0.05"
                      value={volume}
                      disabled={isMuted}
                      onChange={(e) => setVolume(parseFloat(e.target.value))}
                      onMouseUp={triggerAutosave}
                      className="w-full accent-emerald-400"
                    />
                  </div>
                  <label className="flex items-center space-x-2 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={isMuted}
                      onChange={(e) => { setIsMuted(e.target.checked); triggerAutosave(); }}
                      className="rounded bg-slate-900 border-slate-700 text-rose-500"
                    />
                    <span className="text-slate-300 font-medium">Mute Clip Audio</span>
                  </label>
                </div>
              )}

              {/* TAB 2: CAPTION STYLE */}
              {activeInspectorTab === 'style' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Font Size</label>
                      <select
                        value={captionSize}
                        onChange={(e) => setCaptionSize(e.target.value)}
                        className="w-full px-2 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-white"
                      >
                        <option value="small">Small</option>
                        <option value="medium">Medium (Standard)</option>
                        <option value="large">Large (High Impact)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Screen Position</label>
                      <select
                        value={captionPosition}
                        onChange={(e) => setCaptionPosition(e.target.value)}
                        className="w-full px-2 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-white"
                      >
                        <option value="bottom_safe">Bottom Safe Zone</option>
                        <option value="center">Center</option>
                        <option value="top">Top Header</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 pt-1">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400">Font:</span>
                      <input
                        type="color"
                        value={captionColor}
                        onChange={(e) => setCaptionColor(e.target.value)}
                        className="w-6 h-6 rounded border-0 bg-transparent cursor-pointer"
                      />
                      <span className="font-mono text-[10px] text-slate-400">{captionColor}</span>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400">Highlight:</span>
                      <input
                        type="color"
                        value={highlightColor}
                        onChange={(e) => setHighlightColor(e.target.value)}
                        className="w-6 h-6 rounded border-0 bg-transparent cursor-pointer"
                      />
                      <span className="font-mono text-[10px] text-slate-400">{highlightColor}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB: REFRAME & CROP (P5.7 & P5.8) */}
              {activeInspectorTab === 'reframe' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Framing Override Mode</label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('auto'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'auto' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Auto (AI Smart Face)
                      </button>
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('manual'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'manual' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Manual Position
                      </button>
                    </div>
                  </div>

                  {cropMode === 'manual' && (
                    <div className="space-y-2.5 p-2.5 bg-[#13151f] rounded-lg border border-[#293245]">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Horizontal Crop X:</span>
                          <span className="font-mono text-white">{Math.round(cropX * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min="0.0"
                          max="1.0"
                          step="0.02"
                          value={cropX}
                          onChange={(e) => setCropX(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Crop Scale:</span>
                          <span className="font-mono text-white">{cropScale.toFixed(2)}x</span>
                        </div>
                        <input
                          type="range"
                          min="0.8"
                          max="1.8"
                          step="0.05"
                          value={cropScale}
                          onChange={(e) => setCropScale(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Multi-Speaker Layout</label>
                    <div className="grid grid-cols-3 gap-1.5 font-mono text-[11px]">
                      {['AUTO', 'TRACK', 'SPLIT'].map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => { pushUndo(); setLayoutMode(m); triggerAutosave(); }}
                          className={`py-1.5 rounded border transition ${layoutMode === m ? 'bg-purple-950/80 border-purple-600 text-purple-200 font-bold' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB: AUDIO CONTROLS (P5.9) */}
              {activeInspectorTab === 'audio' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>Volume Gain:</span>
                      <span className="font-mono text-white">{Math.round(volume * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="2.0"
                      step="0.05"
                      value={volume}
                      disabled={isMuted}
                      onChange={(e) => setVolume(parseFloat(e.target.value))}
                      onMouseUp={triggerAutosave}
                      className="w-full accent-emerald-400"
                    />
                  </div>
                  <label className="flex items-center space-x-2 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={isMuted}
                      onChange={(e) => { setIsMuted(e.target.checked); triggerAutosave(); }}
                      className="rounded bg-slate-900 border-slate-700 text-rose-500"
                    />
                    <span className="text-slate-300 font-medium">Mute Clip Audio</span>
                  </label>
                </div>
              )}

              {/* TAB 3: EXPORT */}
              {activeInspectorTab === 'export' && (
                <div className="space-y-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Export Resolution</label>
                    <div className="grid grid-cols-3 gap-2">
                      {['720p', '1080p', '4K'].map((res) => (
                        <button
                          key={res}
                          type="button"
                          onClick={() => setExportRes(res)}
                          className={`p-2 rounded border text-xs font-medium transition-colors ${
                            exportRes === res
                              ? 'bg-[#252b3d] border-blue-500 text-white'
                              : 'bg-[#13151f] border-[#293245] text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {res} {res === '1080p' ? '(Standard)' : ''}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Platform Preset</label>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      {[
                        { id: 'tiktok', name: 'TikTok 9:16' },
                        { id: 'hyperframes', name: '★ HyperFrames HTML' },
                        { id: 'reels', name: 'Instagram Reels' },
                        { id: 'shorts', name: 'YouTube Shorts' }
                      ].map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => setExportPlatform(p.id)}
                          className={`p-2 rounded border text-xs font-medium transition-colors ${
                            exportPlatform === p.id
                              ? 'bg-[#252b3d] border-blue-500 text-white'
                              : 'bg-[#13151f] border-[#293245] text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {p.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={handleExport}
                      disabled={exporting}
                      className="w-full py-2 rounded bg-[#aab9c7] hover:bg-[#e9ecee] text-white text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                      {exporting ? 'Rendering Package…' : exportDone ? 'Package Ready ✓' : 'Render Export Package'}
                    </button>
                  </div>
                </div>
              )}

              {/* TAB: REFRAME & CROP (P5.7 & P5.8) */}
              {activeInspectorTab === 'reframe' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Framing Override Mode</label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('auto'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'auto' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Auto (AI Smart Face)
                      </button>
                      <button
                        type="button"
                        onClick={() => { pushUndo(); setCropMode('manual'); triggerAutosave(); }}
                        className={`p-2 rounded border font-medium ${cropMode === 'manual' ? 'bg-[#252b3d] border-cyan-400 text-white' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                      >
                        Manual Position
                      </button>
                    </div>
                  </div>

                  {cropMode === 'manual' && (
                    <div className="space-y-2.5 p-2.5 bg-[#13151f] rounded-lg border border-[#293245]">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Horizontal Crop X:</span>
                          <span className="font-mono text-white">{Math.round(cropX * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min="0.0"
                          max="1.0"
                          step="0.02"
                          value={cropX}
                          onChange={(e) => setCropX(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                          <span>Crop Scale:</span>
                          <span className="font-mono text-white">{cropScale.toFixed(2)}x</span>
                        </div>
                        <input
                          type="range"
                          min="0.8"
                          max="1.8"
                          step="0.05"
                          value={cropScale}
                          onChange={(e) => setCropScale(parseFloat(e.target.value))}
                          onMouseUp={triggerAutosave}
                          className="w-full accent-cyan-400"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Multi-Speaker Layout</label>
                    <div className="grid grid-cols-3 gap-1.5 font-mono text-[11px]">
                      {['AUTO', 'TRACK', 'SPLIT'].map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => { pushUndo(); setLayoutMode(m); triggerAutosave(); }}
                          className={`py-1.5 rounded border transition ${layoutMode === m ? 'bg-purple-950/80 border-purple-600 text-purple-200 font-bold' : 'bg-[#13151f] border-[#293245] text-slate-400'}`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB: AUDIO CONTROLS (P5.9) */}
              {activeInspectorTab === 'audio' && (
                <div className="space-y-3.5 text-xs">
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>Volume Gain:</span>
                      <span className="font-mono text-white">{Math.round(volume * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="2.0"
                      step="0.05"
                      value={volume}
                      disabled={isMuted}
                      onChange={(e) => setVolume(parseFloat(e.target.value))}
                      onMouseUp={triggerAutosave}
                      className="w-full accent-emerald-400"
                    />
                  </div>
                  <label className="flex items-center space-x-2 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={isMuted}
                      onChange={(e) => { setIsMuted(e.target.checked); triggerAutosave(); }}
                      className="rounded bg-slate-900 border-slate-700 text-rose-500"
                    />
                    <span className="text-slate-300 font-medium">Mute Clip Audio</span>
                  </label>
                </div>
              )}
            </div>

            {/* Bottom Status / Short Rationale */}
            <div className="pt-3 border-t border-[#293245] flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1.5 text-emerald-400 font-mono">
                <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
                QC Integrity: 1080x1920 H.264
              </span>
              <span className="font-mono tabular-nums">
                Trim window: {trimStart.toFixed(1)}s – {trimEnd.toFixed(1)}s
              </span>
            </div>
          </div>
        </div>

        {/* BOTTOM STAGE: CapCut Multi-Track Timeline */}
        <div className="h-[210px] bg-[#13151f] flex flex-col shrink-0 select-none">
          {/* Timeline Toolbar */}
          <div className="h-9 px-3 border-b border-[#293245] bg-[#12141d] flex items-center justify-between">
            {/* Playback Controls */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={togglePlay}
                aria-label={isPlaying ? 'Pause' : 'Play'}
                className="w-6 h-6 rounded bg-[#1e2333] hover:bg-[#252b3c] flex items-center justify-center text-slate-200 hover:text-white transition-colors"
              >
                {isPlaying ? (
                  <Pause className="w-3 h-3" aria-hidden="true" />
                ) : (
                  <Play className="w-3 h-3 ml-0.5" aria-hidden="true" />
                )}
              </button>

              <div className="font-mono text-xs text-slate-200 tabular-nums">
                <span className="text-cyan-400">{formatTimecode(currentTime)}</span>
                <span className="text-slate-500"> / </span>
                <span className="text-slate-400">{formatTimecode(totalDuration)}</span>
              </div>
            </div>

            {/* Edit Tools */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleSplitCaption}
                title="Split subtitle at playhead (Scissors)"
                className="px-2 py-1 rounded bg-[#1e2333] hover:bg-[#252b3c] text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1 border border-[#4c5e6b] transition-colors"
              >
                <Scissors className="w-3 h-3 text-cyan-400" aria-hidden="true" />
                <span>Split Text</span>
              </button>

              <button
                type="button"
                onClick={handleAddCaption}
                title="Add subtitle chunk at playhead"
                className="px-2 py-1 rounded bg-[#1e2333] hover:bg-[#252b3c] text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1 border border-[#4c5e6b] transition-colors"
              >
                <Plus className="w-3 h-3 text-emerald-400" aria-hidden="true" />
                <span>+ Chunk</span>
              </button>
            </div>

            {/* Zoom / Info */}
            <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
              <span>Timeline: 100%</span>
            </div>
          </div>

          {/* Timeline Multi-Track Body */}
          <div className="flex-1 flex overflow-hidden">
            {/* Track Headers (Left Column) */}
            <div className="w-24 bg-[#1a1e2b] border-r border-[#293245] flex flex-col shrink-0 text-[10px] font-mono">
              {/* Ruler header gap */}
              <div className="h-5 border-b border-[#293245] px-2 flex items-center text-slate-500">
                TIME
              </div>

              {/* T1 Track Header */}
              <div className="h-14 border-b border-[#293245] px-2 flex flex-col justify-center gap-0.5">
                <div className="flex items-center gap-1 text-cyan-300 font-bold">
                  <Type className="w-3 h-3" aria-hidden="true" />
                  <span>T1 TEXT</span>
                </div>
                <span className="text-slate-500 text-[9px]">Captions</span>
              </div>

              {/* V1 Track Header */}
              <div className="h-16 px-2 flex flex-col justify-center gap-0.5">
                <div className="flex items-center gap-1 text-blue-300 font-bold">
                  <Film className="w-3 h-3" aria-hidden="true" />
                  <span>V1 VIDEO</span>
                </div>
                <span className="text-slate-500 text-[9px]">9:16 Master</span>
              </div>
            </div>

            {/* Tracks Canvas with Playhead */}
            <div
              ref={timelineRef}
              onClick={handleTimelineClick}
              className="flex-1 relative overflow-hidden bg-[#13151f] cursor-pointer flex flex-col"
            >
              {/* Time Ruler (Seconds markers) */}
              <div className="h-5 border-b border-[#293245] bg-[#101217] relative select-none flex items-center">
                {Array.from({ length: Math.ceil(totalDuration) + 1 }).map((_, i) => {
                  const percent = (i / totalDuration) * 100;
                  if (percent > 100) return null;
                  return (
                    <div
                      key={i}
                      className="absolute top-0 bottom-0 flex flex-col items-start"
                      style={{ left: `${percent}%` }}
                    >
                      <div className="h-2 w-px bg-[#4c5e6b]" />
                      {i % 2 === 0 && (
                        <span className="text-[9px] font-mono text-slate-500 -ml-2 -mt-0.5">
                          {i}s
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Track T1: Subtitle Chunks Layer */}
              <div className="h-14 border-b border-[#293245] bg-[#13151f] relative p-1.5 flex items-center">
                {captions.map((chunk) => {
                  const left = (chunk.start / totalDuration) * 100;
                  const width = ((chunk.end - chunk.start) / totalDuration) * 100;
                  const isSelected = chunk.id === selectedCaptionId;

                  return (
                    <div
                      key={chunk.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCaptionId(chunk.id);
                        seekTo(chunk.start);
                      }}
                      className={`absolute top-1.5 bottom-1.5 rounded px-2 flex items-center overflow-hidden transition-all text-[11px] font-medium border ${
                        isSelected
                          ? 'bg-[#183354] border-cyan-400 text-white shadow-md shadow-cyan-950/40 z-10'
                          : 'bg-[#142338] border-[#223d63] text-cyan-200 hover:border-cyan-500/50'
                      }`}
                      style={{
                        left: `${left}%`,
                        width: `${Math.max(3, width)}%`
                      }}
                    >
                      <span className="truncate">{chunk.text}</span>
                    </div>
                  );
                })}
              </div>

              {/* Track V1: Video Layer Strip with In/Out Bounds */}
              <div className="h-16 bg-[#13151f] relative p-1.5 flex items-center">
                {/* Active Video Region */}
                <div
                  className="absolute top-1.5 bottom-1.5 rounded bg-gradient-to-r from-[#172033] via-[#1c2840] to-[#172033] border border-[#2b3e63] flex items-center justify-between px-2 overflow-hidden shadow-inner"
                  style={{
                    left: `${(trimStart / totalDuration) * 100}%`,
                    width: `${((trimEnd - trimStart) / totalDuration) * 100}%`
                  }}
                >
                  {/* Waveform / Frames visualizer simulation */}
                  <div className="w-full h-full flex items-center gap-1 opacity-60">
                    {Array.from({ length: 28 }).map((_, i) => (
                      <div
                        key={i}
                        className="flex-1 bg-[#324b78] rounded-sm"
                        style={{ height: `${20 + (i % 5) * 18}%` }}
                      />
                    ))}
                  </div>

                  <span className="absolute right-2 text-[10px] font-mono text-slate-400">
                    1080x1920 (9:16)
                  </span>
                </div>
              </div>

              {/* CapCut Vertical Playhead Needle */}
              <div
                className="absolute top-0 bottom-0 pointer-events-none z-20 flex flex-col items-center"
                style={{ left: `${playheadPercent}%` }}
              >
                {/* Playhead Needle Head */}
                <div className="w-2.5 h-3 bg-red-500 rounded-b -mt-0.5 shadow-md flex items-center justify-center">
                  <div className="w-0.5 h-1.5 bg-white rounded-full" />
                </div>
                {/* Needle Line */}
                <div className="w-[1.5px] flex-1 bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.8)]" />
              </div>
            </div>
          </div>
        </div>

        {/* Action Decision Footer Bar */}
        <div className="h-12 px-4 border-t border-[#293245] bg-[#12141d] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            {clip.media_url && (
              <a
                href={clip.media_url}
                download
                className="px-3 py-1.5 rounded bg-[#1e2333] hover:bg-[#252b3c] text-slate-200 text-xs font-medium border border-[#4c5e6b] transition-colors inline-flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Download MP4</span>
              </a>
            )}
            <span className="text-[11px] text-slate-500 font-mono hidden sm:inline">
              Shortcuts: [Space] Play/Pause • [← / →] Seek ±1s • [Esc] Close
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onClipDecision(clip.id, 'reject')}
              disabled={isLoading}
              className={`px-3.5 py-1.5 rounded text-xs font-medium border transition-colors ${
                isRejected
                  ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                  : 'bg-[#22171a] hover:bg-rose-950/40 text-rose-300 border-rose-900/40'
              }`}
            >
              {isLoading === 'reject' ? 'Rejecting…' : 'Reject'}
            </button>

            <button
              type="button"
              onClick={handleRenderPreview}
              disabled={isRenderingPreview}
              className="px-3 py-1.5 rounded bg-indigo-950/70 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-800 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <Video className="w-3.5 h-3.5" />
              <span>{isRenderingPreview ? 'Rendering 720p...' : 'Render Preview (720p)'}</span>
            </button>

            <button
              type="button"
              onClick={handleRenderFinal}
              disabled={isRenderingFinal}
              className="px-3.5 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-blue-600/25 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{isRenderingFinal ? 'Exporting...' : exportDone ? 'Export Ready ✓' : 'Export Final 1080p'}</span>
            </button>

            <button
              type="button"
              onClick={() => onClipDecision(clip.id, 'approve')}
              disabled={isLoading}
              className={`px-4 py-1.5 rounded text-xs font-semibold border transition-colors ${
                isApproved
                  ? 'bg-emerald-600 text-white border-emerald-500'
                  : 'bg-[#14261d] hover:bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
              }`}
            >
              {isLoading === 'approve' ? 'Approving…' : isApproved ? 'Approved ✓' : 'Approve for Publish'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
