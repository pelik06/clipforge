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
      desc: 'Crisp readable white text',
      preview: () => (
        <span className="text-[#e9ecee] drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)] font-sans font-semibold">
          Clean Subtitle
        </span>
      )
    },
    {
      id: 'creator_bold',
      label: 'Creator Bold',
      desc: 'Viral bold Impact style',
      preview: () => (
        <span className="text-[#e9ecee] uppercase tracking-wider drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]" style={{ fontFamily: 'Impact, sans-serif' }}>
          CREATOR BOLD
        </span>
      )
    },
    {
      id: 'karaoke',
      label: 'Karaoke',
      desc: 'Word-by-word active highlight',
      preview: () => (
        <span className="text-[#e9ecee] drop-shadow-[0_2px_3px_rgba(0,0,0,0.95)]" style={{ fontFamily: 'Impact, sans-serif' }}>
          <span>Word </span>
          <span className="text-[#fcd34d] underline decoration-[#fcd34d] underline-offset-2">Active</span>
          <span> Karaoke</span>
        </span>
      )
    },
    {
      id: 'viral_beast',
      label: 'Viral Beast',
      desc: 'MrBeast yellow + green pop',
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
      desc: 'Subtle clean subtitle',
      preview: () => (
        <span className="text-[#aab9c7] font-sans text-[10px] opacity-90">
          subtle subtitle
        </span>
      )
    },
    {
      id: 'no_captions',
      label: 'No Captions',
      desc: 'Subtitles disabled',
      preview: () => (
        <span className="text-[#6e8799] font-mono italic text-[10px]">
          [ No subtitles ]
        </span>
      )
    }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#293245] pb-4">
        <h1 className="text-xl font-semibold tracking-tight text-[#e9ecee]">Generate Clips Studio</h1>
        <p className="text-xs text-[#6e8799] mt-0.5">
          Paste link video, tentukan lokasi caption dan preset, lalu generate hingga 5 klip video vertikal 9:16.
        </p>
      </div>

      {/* Main Studio Card */}
      <div className="rounded-lg bg-[#1a1e2b] border border-[#293245] p-5 sm:p-6 space-y-6 shadow-sm">
        <form onSubmit={handleVodSubmit} className="space-y-6">
          {/* Section 1: Video Link & Clippo Toggle */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="vod_url" className="text-xs font-semibold text-[#e9ecee] uppercase tracking-wider block">
                Link Video (Source Media)
              </label>
              <button
                type="button"
                onClick={() => setShowClippo(!showClippo)}
                className="text-[11px] text-[#aab9c7] hover:underline font-mono"
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
              className={`w-full px-3.5 py-2.5 rounded-md bg-[#13151f] border text-xs text-[#e9ecee] placeholder-[#6e8799] focus:outline-none focus:border-[#aab9c7] transition-colors ${
                inputError ? 'border-[#f87171]' : 'border-[#293245]'
              }`}
            />
            {inputError && <p className="text-[11px] text-[#f87171] mt-1">{inputError}</p>}
            <p className="text-[11px] text-[#6e8799] mt-1 font-mono">
              YouTube, Shorts, atau local file (.mp4, .mkv, .mov)
            </p>
          </div>

          {/* Active Config Strategy Badges */}
          <div className="flex flex-wrap items-center gap-2 pt-1 pb-1">
            <span className="px-2.5 py-1 rounded-md bg-[#1e2333] border border-[#293245] text-[11px] font-mono text-[#aab9c7] flex items-center gap-1.5">
              <Video className="w-3.5 h-3.5 text-[#aab9c7]" />
              <span>Framing:</span>
              <span className="font-semibold text-[#e9ecee]">Follow Speaker (9:16)</span>
            </span>
            <span className="px-2.5 py-1 rounded-md bg-[#2a2318] border border-[#4d3e23] text-[11px] font-mono text-[#fcd34d] flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#fcd34d]" />
              <span>Detection:</span>
              <span className="font-semibold text-[#e9ecee]">Automatic Heuristic</span>
            </span>
            <span className="px-2.5 py-1 rounded-md bg-[#14261d] border border-[#1f4a3d] text-[11px] font-mono text-[#6ee7b7] flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#6ee7b7]" />
              <span>Clips:</span>
              <span className="font-semibold text-[#e9ecee]">Max 5 (45s – 120s)</span>
            </span>
          </div>

          {/* Section 2: Caption Position Selector */}
          <div className="pt-2 border-t border-[#293245]">
            <label className="text-xs font-semibold text-[#e9ecee] uppercase tracking-wider block mb-2">
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
                      ? 'bg-[#252b3d] border-[#aab9c7] text-[#e9ecee] shadow-sm'
                      : 'bg-[#13151f] border-[#293245] text-[#6e8799] hover:text-[#e9ecee] hover:border-[#4c5e6b]'
                  }`}
                >
                  <div className="text-xs font-semibold">{pos.label}</div>
                  <div className="text-[10px] text-[#6e8799] mt-0.5">{pos.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Section 3: Caption Presets */}
          <div className="pt-2 border-t border-[#293245]">
            <div className="flex items-center justify-between mb-2.5">
              <label className="text-xs font-semibold text-[#e9ecee] uppercase tracking-wider block">
                Pilihan Preset Subtitle & Caption
              </label>
              <button
                type="button"
                onClick={() => setShowAdvancedCaptions(!showAdvancedCaptions)}
                className="text-[11px] text-[#aab9c7] hover:underline font-mono"
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
                        ? 'bg-[#252b3d] border-[#aab9c7] text-[#e9ecee] shadow-sm'
                        : 'bg-[#13151f] border-[#293245] text-[#6e8799] hover:text-[#e9ecee] hover:border-[#4c5e6b]'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs font-semibold truncate">{preset.label}</span>
                        {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-[#aab9c7] shrink-0" />}
                      </div>
                      <p className="text-[10px] text-[#6e8799] line-clamp-1">{preset.desc}</p>
                    </div>

                    <div className="w-full h-7 rounded bg-[#1a1e2b] border border-[#293245] flex items-center justify-center text-center px-1.5 select-none text-[10px]">
                      {preset.preview()}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 4: Advanced Parameters */}
          <div className="pt-2 border-t border-[#293245]">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs font-semibold text-[#aab9c7] hover:text-[#e9ecee] flex items-center gap-1.5 transition-colors"
            >
              <Sliders className="w-3.5 h-3.5 text-[#aab9c7]" />
              <span>Pengaturan Lanjutan (Ukuran Font, Framing 9:16, Bahasa)</span>
              {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showAdvanced && (
              <div className="mt-3 p-4 rounded-md bg-[#13151f] border border-[#293245] space-y-4 text-xs">
                {/* Caption Size & Language */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] text-[#6e8799] block mb-1">Ukuran Font Caption</label>
                    <select
                      value={captionSize}
                      onChange={(e) => setCaptionSize(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-[#1a1e2b] border border-[#293245] text-xs text-[#e9ecee] focus:outline-none focus:border-[#aab9c7]"
                    >
                      <option value="small">Small (56pt)</option>
                      <option value="medium">Medium (74pt)</option>
                      <option value="large">Large (92pt - Recommended)</option>
                      <option value="extra_large">Extra Large (110pt)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] text-[#6e8799] block mb-1">Bahasa Transkripsi</label>
                    <select
                      value={captionLanguage}
                      onChange={(e) => setCaptionLanguage(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded bg-[#1a1e2b] border border-[#293245] text-xs text-[#e9ecee] focus:outline-none focus:border-[#aab9c7]"
                    >
                      <option value="auto">Auto-Detect</option>
                      <option value="id">Indonesian (Bahasa)</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                </div>

                {/* Framing Mode */}
                <div>
                  <label className="text-[11px] text-[#6e8799] block mb-1">
                    Framing Mode (9:16 Strategy)
                  </label>
                  <select
                    value={framingMode}
                    onChange={(e) => setFramingMode(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded bg-[#1a1e2b] border border-[#293245] text-xs text-[#e9ecee] focus:outline-none focus:border-[#aab9c7]"
                  >
                    <option value="auto_follow_speaker">Auto Follow Speaker (Face Tracking YuNet)</option>
                    <option value="center_crop">Center Crop (Fixed Safe Zone)</option>
                    <option value="split">Split Screen (Stacked 1080x960 Multi-Speaker)</option>
                  </select>
                </div>

                {/* Word Highlight & Scene Snapping */}
                <div className="grid grid-cols-2 gap-3 pt-1 border-t border-[#293245]">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="wordHighlightToggle"
                      checked={captionWordHighlight || captionPreset === 'karaoke' || captionPreset === 'viral_beast' || captionPreset === 'neon_cyan'}
                      onChange={(e) => setCaptionWordHighlight(e.target.checked)}
                      className="rounded accent-[#aab9c7]"
                    />
                    <label htmlFor="wordHighlightToggle" className="text-[11px] text-[#aab9c7] cursor-pointer">
                      Word-by-Word Highlight
                    </label>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="sceneSnapToggle"
                      checked={enableSceneDetection}
                      onChange={(e) => setEnableSceneDetection(e.target.checked)}
                      className="rounded accent-[#aab9c7]"
                    />
                    <label htmlFor="sceneSnapToggle" className="text-[11px] text-[#aab9c7] cursor-pointer">
                      Visual Scene Cut Snapping
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Submit Action */}
          <div className="pt-3 border-t border-[#293245] flex items-center justify-between">
            <span className="text-[11px] text-[#6e8799] font-mono">
              Target: 5 Clips • Durasi: 45s–120s • 13-stage pipeline
            </span>
            <button
              type="submit"
              disabled={submitting || !vodUrl.trim()}
              className="px-6 py-2.5 rounded-md bg-[#e9ecee] hover:bg-white text-[#13151f] text-xs font-semibold transition-all shadow-sm flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none"
            >
              <span>{submitting ? 'Memproses 13 Stages…' : 'Generate 9:16 Clips'}</span>
            </button>
          </div>
        </form>

        {/* Clippo Sync Panel */}
        {showClippo && (
          <div className="mt-4 pt-4 border-t border-[#293245] bg-[#13151f] p-3.5 rounded-md border border-[#293245]">
            <div className="text-xs font-semibold text-[#e9ecee] mb-2">Sync Task from Clippo.id</div>
            <form onSubmit={handleClippoSync} className="flex gap-2">
              <input
                type="text"
                placeholder="Clippo Task ID (e.g. 70274198…)"
                value={clippoId}
                onChange={(e) => setClippoId(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded bg-[#1a1e2b] border border-[#293245] text-xs text-[#e9ecee]"
              />
              <button
                type="submit"
                disabled={clippoSubmitting || !clippoId.trim()}
                className="px-3 py-1.5 rounded bg-[#252b3d] hover:bg-[#293245] text-[#e9ecee] text-xs font-medium disabled:opacity-50"
              >
                {clippoSubmitting ? 'Syncing…' : 'Sync Task'}
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Active Pipeline Status */}
      {activeJob && (
        <div className="rounded-lg bg-[#1a1e2b] border border-[#293245] p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-[#e9ecee]">
                Job Aktif: {activeJob.id}
              </div>
              <div className="text-[11px] text-[#6e8799]">{activeJob.stage}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[#aab9c7] font-mono tabular-nums">
                {activeJob.progress || 0}%
              </span>
              <button
                onClick={() => setActiveView('dashboard')}
                className="text-[11px] text-[#aab9c7] hover:underline flex items-center gap-1"
              >
                <span>Lihat Detail Pipeline</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="w-full bg-[#13151f] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-[#aab9c7] h-full transition-all duration-300"
              style={{ width: `${Math.max(5, activeJob.progress || 0)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
