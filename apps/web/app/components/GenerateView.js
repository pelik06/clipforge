'use client';

import { useState } from 'react';
import {
  Film,
  Video,
  Type,
  CheckCircle2,
  XCircle,
  Eye,
  Zap,
  ArrowRight,
  Sliders,
  Layers,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function GenerateView({
  vodUrl,
  setVodUrl,
  inputError,
  handleUrlChange,
  handleVodSubmit,
  submitting,
  clippoId,
  setClippoId,
  handleClippoSync,
  clippoSubmitting,
  framingMode,
  setFramingMode,
  captionPreset,
  setCaptionPreset,
  captionLanguage,
  setCaptionLanguage,
  captionSize,
  setCaptionSize,
  captionPosition,
  setCaptionPosition,
  captionTextColor,
  setCaptionTextColor,
  captionHighlightColor,
  setCaptionHighlightColor,
  captionWordHighlight,
  setCaptionWordHighlight,
  showAdvancedCaptions,
  setShowAdvancedCaptions,
  momentDetectionMode,
  setMomentDetectionMode,
  momentDetectionProvider,
  setMomentDetectionProvider,
  maxClips,
  setMaxClips,
  minClipDuration,
  setMinClipDuration,
  maxClipDuration,
  setMaxClipDuration,
  targetDurationPreset,
  setTargetDurationPreset,
  enableSceneDetection,
  setEnableSceneDetection,
  selectedJobData,
  jobs = [],
  selectedJobId,
  setActiveView
}) {
  const [showClippo, setShowClippo] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const activeJob =
    selectedJobData ||
    jobs.find((j) => j.id === selectedJobId && (j.status === 'processing' || j.status === 'created'));

  const captionPresets = [
    {
      id: 'clean',
      label: 'Clean Minimal',
      desc: 'White crisp subtitles with drop shadow',
      previewText: 'CLEAN MINIMAL SUBTITLES',
      previewClass: 'text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]'
    },
    {
      id: 'bold_pop',
      label: 'Bold Pop',
      desc: 'High-energy text with yellow focus word',
      previewText: 'VIRAL HOOK MOMENT',
      previewClass: 'text-white font-extrabold drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]',
      highlightWord: 'VIRAL'
    },
    {
      id: 'high_contrast',
      label: 'High Contrast',
      desc: 'Dark backing box for maximum readability',
      previewText: 'HIGH CONTRAST BOX',
      previewClass: 'bg-black/90 text-white px-2 py-0.5 rounded shadow'
    },
    {
      id: 'neon_viral',
      label: 'Outline Glow',
      desc: 'Glowing outline text popular on TikTok',
      previewText: 'NEON VIRAL CAPTION',
      previewClass: 'text-amber-300 drop-shadow-[0_0_8px_rgba(245,158,11,0.8)] font-extrabold'
    }
  ];

  const handleDurationPresetSelect = (preset) => {
    if (setTargetDurationPreset) setTargetDurationPreset(preset);
    if (preset === 'fast') {
      if (setMinClipDuration) setMinClipDuration(15);
      if (setMaxClipDuration) setMaxClipDuration(45);
    } else if (preset === 'medium') {
      if (setMinClipDuration) setMinClipDuration(45);
      if (setMaxClipDuration) setMaxClipDuration(90);
    } else if (preset === 'extended') {
      if (setMinClipDuration) setMinClipDuration(90);
      if (setMaxClipDuration) setMaxClipDuration(180);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#222631] pb-4">
        <h1 className="text-xl font-semibold tracking-tight text-white">Generate Clips Studio</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Paste video link, tentukan durasi target dan caption, atau sinkronkan tugas dari Clippo.id.
        </p>
      </div>

      {/* Main Studio Card */}
      <div className="rounded-lg bg-[#14161c] border border-[#222631] p-5 sm:p-6 space-y-6">
        <form onSubmit={handleVodSubmit} className="space-y-6">
          {/* Section 1: Video Link & Clippo Toggle */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="vod_url" className="text-xs font-semibold text-white uppercase tracking-wider block">
                Link Video (Source Media)
              </label>
              <button
                type="button"
                onClick={() => setShowClippo(!showClippo)}
                className="text-[11px] text-[#3b82f6] hover:underline font-mono"
              >
                {showClippo ? 'Sembunyikan Clippo.id' : 'Gunakan Clippo.id Task'}
              </button>
            </div>

            <input
              id="vod_url"
              name="vod_url"
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={vodUrl}
              onChange={handleUrlChange}
              placeholder="https://www.youtube.com/watch?v=… atau path file /video.mp4"
              className={`w-full px-3.5 py-2.5 rounded-md bg-[#0c0d11] border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#2563eb] transition-colors ${
                inputError ? 'border-rose-800' : 'border-[#222631]'
              }`}
            />
            {inputError && <p className="text-[11px] text-rose-400 mt-1">{inputError}</p>}
            <p className="text-[11px] text-slate-500 mt-1 font-mono">
              YouTube, Shorts, atau local file (.mp4, .mkv, .mov)
            </p>
          </div>

          {/* Section 2: Target Duration Presets (from master) */}
          <div className="pt-2 border-t border-[#222631]">
            <label className="text-xs font-semibold text-white uppercase tracking-wider block mb-2">
              Target Clip Duration
            </label>
            <div className="grid grid-cols-3 gap-2.5">
              {[
                { id: 'fast', label: 'Fast (15–45s)', desc: 'TikTok / Shorts quick hooks' },
                { id: 'medium', label: 'Medium (45–90s)', desc: 'Balanced thought & payoff (Default)' },
                { id: 'extended', label: 'Extended (90–180s)', desc: 'Deep story & podcast context' }
              ].map((dp) => (
                <button
                  key={dp.id}
                  type="button"
                  onClick={() => handleDurationPresetSelect(dp.id)}
                  className={`p-2.5 rounded border text-left transition-colors ${
                    targetDurationPreset === dp.id
                      ? 'bg-[#1c2233] border-[#3b82f6] text-white'
                      : 'bg-[#0c0d11] border-[#1d212b] text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="text-xs font-semibold">{dp.label}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{dp.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Section 3: Caption Presets */}
          <div className="pt-2 border-t border-[#222631]">
            <label className="text-xs font-semibold text-white uppercase tracking-wider block mb-2.5">
              Pilihan Caption & Subtitle
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {captionPresets.map((preset) => {
                const isSelected = captionPreset === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => setCaptionPreset(preset.id)}
                    className={`p-3 rounded-md border text-left transition-colors flex flex-col justify-between gap-3 ${
                      isSelected
                        ? 'bg-[#1c2233] border-[#3b82f6] text-white shadow-sm'
                        : 'bg-[#0c0d11] border-[#1d212b] text-slate-300 hover:border-[#2b3140]'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold">{preset.label}</span>
                        {isSelected && <span className="w-2 h-2 rounded-full bg-blue-400" />}
                      </div>
                      <p className="text-[11px] text-slate-400">{preset.desc}</p>
                    </div>

                    <div className="w-full h-8 rounded bg-[#14161c] border border-[#222631] flex items-center justify-center text-center px-2 select-none">
                      <span className={`text-[10px] tracking-tight ${preset.previewClass}`}>
                        {preset.highlightWord ? (
                          <>
                            <span className="text-amber-400 underline">{preset.highlightWord}</span>{' '}
                            <span>HOOK MOMENT</span>
                          </>
                        ) : (
                          preset.previewText
                        )}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 4: Advanced Parameters (Framing, Detection, Style) */}
          <div className="pt-2 border-t border-[#222631]">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <Sliders className="w-3.5 h-3.5 text-blue-400" />
              <span>Pengaturan Lanjutan (Framing 9:16, Bahasa, Detection Engine)</span>
              {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showAdvanced && (
              <div className="mt-3 p-4 rounded-md bg-[#0c0d11] border border-[#1d212b] space-y-4 text-xs">
                {/* Framing Mode */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">
                    Framing Mode (9:16 Strategy)
                  </label>
                  <select
                    value={framingMode}
                    onChange={(e) => setFramingMode(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
                  >
                    <option value="auto_follow_speaker">Auto Follow Speaker (Face Tracking YuNet)</option>
                    <option value="center_crop">Center Crop (Fixed Safe Zone)</option>
                    <option value="split_screen">Split Screen (Podcast / Dual Speaker)</option>
                    <option value="speaker_track">Speaker Track Only</option>
                  </select>
                </div>

                {/* Language & Word Highlight */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Bahasa Transkripsi</label>
                    <select
                      value={captionLanguage}
                      onChange={(e) => setCaptionLanguage(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
                    >
                      <option value="auto">Auto-Detect</option>
                      <option value="en">English</option>
                      <option value="id">Indonesian (Bahasa)</option>
                      <option value="es">Spanish</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Word Highlight</label>
                    <button
                      type="button"
                      onClick={() => setCaptionWordHighlight(!captionWordHighlight)}
                      className={`w-full px-2.5 py-1.5 rounded border text-xs font-medium transition-colors ${
                        captionWordHighlight
                          ? 'bg-[#1c2233] border-[#3b82f6] text-blue-300'
                          : 'bg-[#14161c] border-[#222631] text-slate-400'
                      }`}
                    >
                      {captionWordHighlight ? 'Word Highlight: ON' : 'Word Highlight: OFF'}
                    </button>
                  </div>
                </div>

                {/* AI Detection & Limits */}
                <div className="grid grid-cols-2 gap-3 pt-1 border-t border-[#1d212b]">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Moment Detection Mode</label>
                    <select
                      value={momentDetectionMode}
                      onChange={(e) => setMomentDetectionMode(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
                    >
                      <option value="heuristic">Heuristic (Energy & Audio Density)</option>
                      <option value="gemini">Gemini LLM Reasoner</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between pt-4">
                    <span className="text-[11px] text-slate-400">Scene Cut Snapping:</span>
                    <input
                      type="checkbox"
                      checked={enableSceneDetection}
                      onChange={(e) => setEnableSceneDetection(e.target.checked)}
                      className="rounded accent-[#2563eb]"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Submit Action */}
          <div className="pt-3 border-t border-[#222631] flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">
              Durasi: {minClipDuration}s–{maxClipDuration}s • 13-stage pipeline
            </span>
            <button
              type="submit"
              disabled={submitting || !vodUrl.trim()}
              className="px-5 py-2 rounded-md bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#2563eb]"
            >
              <span>{submitting ? 'Memproses 13 Stages…' : 'Generate 9:16 Clips'}</span>
            </button>
          </div>
        </form>

        {/* Clippo Sync Panel (from master) */}
        {showClippo && (
          <div className="mt-4 pt-4 border-t border-[#222631] bg-[#0c0d11] p-3.5 rounded-md border border-[#1d212b]">
            <div className="text-xs font-semibold text-white mb-2">Sync Task from Clippo.id</div>
            <form onSubmit={handleClippoSync} className="flex gap-2">
              <input
                type="text"
                placeholder="Clippo Task ID (e.g. 70274198…)"
                value={clippoId}
                onChange={(e) => setClippoId(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
              />
              <button
                type="submit"
                disabled={clippoSubmitting || !clippoId.trim()}
                className="px-3 py-1.5 rounded bg-[#222631] hover:bg-[#2b3140] text-slate-200 text-xs font-medium disabled:opacity-50"
              >
                {clippoSubmitting ? 'Syncing…' : 'Sync Task'}
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Active Pipeline Status (Processing Workspace from master) */}
      {activeJob && (
        <div className="rounded-lg bg-[#14161c] border border-[#222631] p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-white">
                Job Aktif: {activeJob.id}
              </div>
              <div className="text-[11px] text-slate-400">{activeJob.stage}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-blue-400 font-mono tabular-nums">
                {activeJob.progress || 0}%
              </span>
              <button
                onClick={() => setActiveView('clips')}
                className="text-xs text-[#3b82f6] hover:underline flex items-center gap-1"
              >
                <span>Lihat Clips</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="w-full bg-[#0c0d11] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-[#2563eb] h-full transition-all duration-300"
              style={{ width: `${Math.max(5, activeJob.progress || 0)}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-xs">
            {(activeJob.stages || []).map((st) => (
              <div
                key={st.id}
                className={`p-1.5 rounded border text-[11px] flex items-center justify-between ${
                  st.status === 'completed'
                    ? 'bg-[#101217] border-[#1d212b] text-slate-400'
                    : st.status === 'running'
                    ? 'bg-[#1c2233] border-blue-500/40 text-blue-200'
                    : 'bg-[#0c0d11] border-[#161820] text-slate-600'
                }`}
              >
                <span className="truncate">{st.name}</span>
                <span className="font-mono uppercase text-[9px] ml-1">
                  {st.status === 'completed' ? 'OK' : st.status === 'running' ? 'RUN' : 'WAIT'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
