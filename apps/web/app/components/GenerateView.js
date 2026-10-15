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
  ChevronUp,
  Clock,
  Sparkles
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
      label: 'Clean',
      desc: 'Simple & readable font',
      preview: () => (
        <span className="text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)] font-sans font-semibold">
          This is a clean subtitle
        </span>
      )
    },
    {
      id: 'creator_bold',
      label: 'Creator Bold',
      desc: 'Viral bold Impact typography',
      preview: () => (
        <span className="text-white uppercase tracking-wider drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]" style={{ fontFamily: 'Impact, sans-serif' }}>
          VIRAL CREATOR BOLD
        </span>
      )
    },
    {
      id: 'karaoke',
      label: 'Karaoke',
      desc: 'Word-by-word active highlight',
      preview: () => (
        <span className="text-white drop-shadow-[0_2px_3px_rgba(0,0,0,0.95)]" style={{ fontFamily: 'Impact, sans-serif' }}>
          <span>Word </span>
          <span className="text-yellow-400 underline decoration-yellow-400 underline-offset-2">Active</span>
          <span> Karaoke</span>
        </span>
      )
    },
    {
      id: 'viral_beast',
      label: 'Viral Beast',
      desc: 'MrBeast yellow & green pop',
      preview: () => (
        <span className="uppercase tracking-wide drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]" style={{ fontFamily: 'Impact, sans-serif' }}>
          <span className="text-[#FFDE00]">THIS IS </span>
          <span className="text-[#00FF66] underline decoration-[#00FF66]">VIRAL</span>
        </span>
      )
    },
    {
      id: 'neon_cyan',
      label: 'Neon Cyan',
      desc: 'Cyberpunk bright glow',
      preview: () => (
        <span className="text-[#00FFFF] drop-shadow-[0_0_8px_rgba(0,255,255,0.8)] font-black">
          <span>CYBER </span>
          <span className="text-white underline">GLOW</span>
        </span>
      )
    },
    {
      id: 'minimal',
      label: 'Minimal',
      desc: 'Clean subtle subtitle',
      preview: () => (
        <span className="text-slate-300 font-sans text-[10px] opacity-90">
          subtle clean subtitle
        </span>
      )
    },
    {
      id: 'no_captions',
      label: 'No Captions',
      desc: 'Subtitles disabled',
      preview: () => (
        <span className="text-slate-500 font-mono italic text-[10px]">
          [ No subtitles ]
        </span>
      )
    }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#222631] pb-4">
        <h1 className="text-xl font-semibold tracking-tight text-white">Generate Clips Studio</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Paste link video, tentukan lokasi caption dan preset, lalu generate hingga 5 klip video vertikal 9:16.
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

          {/* Active Config Strategy Badges */}
          <div className="flex flex-wrap items-center gap-2 pt-1 pb-1">
            <span className="px-2.5 py-1 rounded-md bg-[#1c202a] border border-[#2b3140] text-[11px] font-mono text-blue-300 flex items-center gap-1.5">
              <Video className="w-3.5 h-3.5 text-blue-400" />
              <span>Framing:</span>
              <span className="font-semibold text-white">Follow Speaker (9:16)</span>
            </span>
            <span className="px-2.5 py-1 rounded-md bg-[#261f14] border border-amber-800/40 text-[11px] font-mono text-amber-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Detection:</span>
              <span className="font-semibold text-white">Automatic Heuristic</span>
            </span>
            <span className="px-2.5 py-1 rounded-md bg-[#14261d] border border-emerald-800/40 text-[11px] font-mono text-emerald-300 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              <span>Clips:</span>
              <span className="font-semibold text-white">Max 5 (45s – 120s)</span>
            </span>
          </div>

          {/* Section 2: Caption Position Selector */}
          <div className="pt-2 border-t border-[#222631]">
            <label className="text-xs font-semibold text-white uppercase tracking-wider block mb-2">
              Lokasi Penempatan Caption
            </label>
            <div className="grid grid-cols-3 gap-2.5">
              {[
                { id: 'top_safe', label: '↑ Atas (Top)', desc: 'Area atas bebas kepala/wajah' },
                { id: 'center', label: '↔ Tengah (Center)', desc: 'Tepat di tengah vertikal' },
                { id: 'bottom_safe', label: '↓ Bawah (Bottom)', desc: 'Bawah safe-area (Default)' }
              ].map((pos) => (
                <button
                  key={pos.id}
                  type="button"
                  onClick={() => setCaptionPosition(pos.id)}
                  className={`p-2.5 rounded-md border text-left transition-colors ${
                    captionPosition === pos.id
                      ? 'bg-[#1c2233] border-[#3b82f6] text-white shadow-sm'
                      : 'bg-[#0c0d11] border-[#1d212b] text-slate-400 hover:text-slate-200 hover:border-[#2b3140]'
                  }`}
                >
                  <div className="text-xs font-semibold">{pos.label}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{pos.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Section 3: Caption Presets */}
          <div className="pt-2 border-t border-[#222631]">
            <div className="flex items-center justify-between mb-2.5">
              <label className="text-xs font-semibold text-white uppercase tracking-wider block">
                Pilihan Preset Subtitle & Caption
              </label>
              <button
                type="button"
                onClick={() => setShowAdvancedCaptions(!showAdvancedCaptions)}
                className="text-[11px] text-[#3b82f6] hover:underline font-mono"
              >
                {showAdvancedCaptions ? 'Sembunyikan Opsi Lanjutan' : 'Opsi Custom & Ukuran'}
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
              {captionPresets.map((preset) => {
                const isSelected = captionPreset === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => {
                      setCaptionPreset(preset.id);
                      if (preset.id === 'karaoke' || preset.id === 'viral_beast' || preset.id === 'neon_cyan') {
                        setCaptionWordHighlight(true);
                      }
                    }}
                    className={`p-2.5 rounded-md border text-left transition-colors flex flex-col justify-between gap-2 ${
                      isSelected
                        ? 'bg-[#1c2233] border-[#3b82f6] text-white shadow-sm'
                        : 'bg-[#0c0d11] border-[#1d212b] text-slate-300 hover:border-[#2b3140]'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs font-semibold truncate">{preset.label}</span>
                        {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />}
                      </div>
                      <p className="text-[10px] text-slate-400 line-clamp-1">{preset.desc}</p>
                    </div>

                    <div className="w-full h-7 rounded bg-[#14161c] border border-[#222631] flex items-center justify-center text-center px-1.5 select-none text-[10px]">
                      {preset.preview()}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 4: Advanced Parameters */}
          <div className="pt-2 border-t border-[#222631]">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <Sliders className="w-3.5 h-3.5 text-blue-400" />
              <span>Pengaturan Lanjutan (Ukuran Font, Framing 9:16, Bahasa)</span>
              {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showAdvanced && (
              <div className="mt-3 p-4 rounded-md bg-[#0c0d11] border border-[#1d212b] space-y-4 text-xs">
                {/* Caption Size & Language */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Ukuran Font Caption</label>
                    <select
                      value={captionSize}
                      onChange={(e) => setCaptionSize(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
                    >
                      <option value="small">Small (56pt)</option>
                      <option value="medium">Medium (74pt)</option>
                      <option value="large">Large (92pt - Recommended)</option>
                      <option value="extra_large">Extra Large (110pt)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Bahasa Transkripsi</label>
                    <select
                      value={captionLanguage}
                      onChange={(e) => setCaptionLanguage(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
                    >
                      <option value="auto">Auto-Detect</option>
                      <option value="id">Indonesian (Bahasa)</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                </div>

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
                    <option value="split">Split Screen (Stacked 1080x960 Multi-Speaker)</option>
                  </select>
                </div>

                {/* Word Highlight & Scene Snapping */}
                <div className="grid grid-cols-2 gap-3 pt-1 border-t border-[#1d212b]">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="wordHighlightToggle"
                      checked={captionWordHighlight || captionPreset === 'karaoke' || captionPreset === 'viral_beast' || captionPreset === 'neon_cyan'}
                      onChange={(e) => setCaptionWordHighlight(e.target.checked)}
                      className="rounded accent-[#2563eb]"
                    />
                    <label htmlFor="wordHighlightToggle" className="text-[11px] text-slate-300 cursor-pointer">
                      Word-by-Word Highlight
                    </label>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="sceneSnapToggle"
                      checked={enableSceneDetection}
                      onChange={(e) => setEnableSceneDetection(e.target.checked)}
                      className="rounded accent-[#2563eb]"
                    />
                    <label htmlFor="sceneSnapToggle" className="text-[11px] text-slate-300 cursor-pointer">
                      Visual Scene Cut Snapping
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Submit Action */}
          <div className="pt-3 border-t border-[#222631] flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">
              Target: 5 Clips • Durasi: 45s–120s • 13-stage pipeline
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

        {/* Clippo Sync Panel */}
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

      {/* Active Pipeline Status */}
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
                onClick={() => setActiveView('dashboard')}
                className="text-[11px] text-blue-400 hover:underline flex items-center gap-1"
              >
                <span>Lihat Detail Pipeline</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="w-full bg-[#0c0d11] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full transition-all duration-300"
              style={{ width: `${Math.max(5, activeJob.progress || 0)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
