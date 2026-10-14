'use client';

import { useState } from 'react';
import {
  Film,
  Video,
  Clock,
  CheckCircle2,
  XCircle,
  Eye,
  Sliders,
  Type,
  ArrowRight
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
  const [activeTab, setActiveTab] = useState('captions'); // 'captions', 'framing', 'virality'
  const [showClippo, setShowClippo] = useState(false);

  const activeJob =
    selectedJobData ||
    jobs.find((j) => j.id === selectedJobId && (j.status === 'processing' || j.status === 'created'));

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#222631] pb-4">
        <h1 className="text-xl font-semibold tracking-tight text-white">Clip Generator Studio</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Ingest video footage, configure 9:16 reframing, kinetic subtitles, and moment extraction rules.
        </p>
      </div>

      {/* Main Studio Card */}
      <div className="rounded-lg bg-[#14161c] border border-[#222631] p-5 sm:p-6 space-y-5">
        <form onSubmit={handleVodSubmit} className="space-y-5">
          {/* VOD URL Input */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-white uppercase tracking-wider">
                Source Media Path or URL
              </label>
              <button
                type="button"
                onClick={() => setShowClippo(!showClippo)}
                className="text-[11px] text-[#3b82f6] hover:underline font-mono"
              >
                {showClippo ? 'Hide Clippo.id task' : 'Use Clippo.id Task ID'}
              </button>
            </div>

            <input
              type="text"
              value={vodUrl}
              onChange={handleUrlChange}
              placeholder="https://www.youtube.com/watch?v=... or /local/stream.mp4"
              className={`w-full px-3.5 py-2.5 rounded-md bg-[#0c0d11] border text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#2563eb] ${
                inputError ? 'border-rose-800' : 'border-[#222631]'
              }`}
            />
            {inputError && <p className="text-[11px] text-rose-400 mt-1">{inputError}</p>}
          </div>

          {/* Section Tabs */}
          <div className="pt-2 border-t border-[#222631]">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold text-white uppercase tracking-wider">
                Processing Parameters
              </span>
              <div className="flex items-center bg-[#0c0d11] p-0.5 rounded-md border border-[#222631]">
                <button
                  type="button"
                  onClick={() => setActiveTab('captions')}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    activeTab === 'captions'
                      ? 'bg-[#222631] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Subtitles & Styler
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('framing')}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    activeTab === 'framing'
                      ? 'bg-[#222631] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  9:16 Reframing
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('virality')}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    activeTab === 'virality'
                      ? 'bg-[#222631] text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Detection Rules
                </button>
              </div>
            </div>

            {/* TAB 1: CAPTIONS & PREVIEW */}
            {activeTab === 'captions' && (
              <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
                {/* Controls (7 cols) */}
                <div className="md:col-span-7 space-y-3.5">
                  <div>
                    <label className="text-[11px] font-medium text-slate-300 block mb-1.5">
                      Subtitle Preset
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { id: 'clean', label: 'Clean Minimal', desc: 'Standard readable subtitle font' },
                        { id: 'bold_pop', label: 'Bold Pop', desc: 'Punchy text with yellow focus' },
                        { id: 'high_contrast', label: 'High Contrast', desc: 'Dark backing box for clarity' },
                        { id: 'neon_viral', label: 'Outline Glow', desc: 'Slight glow outline styling' }
                      ].map((preset) => {
                        const isSelected = captionPreset === preset.id;
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            onClick={() => setCaptionPreset(preset.id)}
                            className={`p-2.5 rounded-md border text-left transition-colors ${
                              isSelected
                                ? 'bg-[#1c2233] border-[#3b82f6] text-white'
                                : 'bg-[#0c0d11] border-[#1d212b] text-slate-300 hover:border-[#2b3140]'
                            }`}
                          >
                            <div className="text-xs font-medium">{preset.label}</div>
                            <div className="text-[10px] text-slate-500 mt-0.5">{preset.desc}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Settings Grid */}
                  <div className="grid grid-cols-2 gap-2.5 pt-1">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Font Size</label>
                      <select
                        value={captionSize}
                        onChange={(e) => setCaptionSize(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-[#0c0d11] border border-[#222631] text-xs text-white"
                      >
                        <option value="small">Small</option>
                        <option value="medium">Medium</option>
                        <option value="large">Large</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Screen Position</label>
                      <select
                        value={captionPosition}
                        onChange={(e) => setCaptionPosition(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-[#0c0d11] border border-[#222631] text-xs text-white"
                      >
                        <option value="bottom_safe">Bottom Safe Zone</option>
                        <option value="center">Center</option>
                        <option value="top">Top</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Audio Language</label>
                      <select
                        value={captionLanguage}
                        onChange={(e) => setCaptionLanguage(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-[#0c0d11] border border-[#222631] text-xs text-white"
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
                            : 'bg-[#0c0d11] border-[#222631] text-slate-400'
                        }`}
                      >
                        {captionWordHighlight ? 'Word Sync: ON' : 'Word Sync: OFF'}
                      </button>
                    </div>
                  </div>

                  {/* Colors */}
                  <div className="flex items-center gap-4 pt-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Primary:</span>
                      <input
                        type="color"
                        value={captionTextColor}
                        onChange={(e) => setCaptionTextColor(e.target.value)}
                        className="w-6 h-6 rounded border-0 bg-transparent cursor-pointer"
                      />
                      <span className="text-[10px] font-mono text-slate-400">{captionTextColor}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Highlight:</span>
                      <input
                        type="color"
                        value={captionHighlightColor}
                        onChange={(e) => setCaptionHighlightColor(e.target.value)}
                        className="w-6 h-6 rounded border-0 bg-transparent cursor-pointer"
                      />
                      <span className="text-[10px] font-mono text-slate-400">{captionHighlightColor}</span>
                    </div>
                  </div>
                </div>

                {/* Right: 9:16 Mockup (5 cols) */}
                <div className="md:col-span-5 flex flex-col items-center justify-center p-4 rounded-md bg-[#0c0d11] border border-[#1d212b]">
                  <span className="text-[11px] text-slate-400 font-mono mb-2">9:16 Monitor Preview</span>

                  {/* Simulated screen */}
                  <div className="w-[160px] h-[280px] rounded-lg bg-[#14161c] border border-[#2b3140] relative overflow-hidden flex flex-col justify-between p-3 select-none">
                    {/* Simulated subject */}
                    <div className="w-10 h-10 rounded-full bg-[#202533] border border-[#2b3140] mx-auto mt-6 flex items-center justify-center">
                      <Video className="w-4 h-4 text-slate-400" />
                    </div>

                    {/* Subtitle simulation */}
                    <div
                      className={`w-full text-center px-1 ${
                        captionPosition === 'top'
                          ? 'mt-3'
                          : captionPosition === 'center'
                          ? 'my-auto'
                          : 'mb-4'
                      }`}
                    >
                      <div
                        className={`inline-block px-1.5 py-0.5 rounded font-bold tracking-tight ${
                          captionSize === 'small'
                            ? 'text-[10px]'
                            : captionSize === 'large'
                            ? 'text-[13px]'
                            : 'text-[11px]'
                        } ${
                          captionPreset === 'high_contrast'
                            ? 'bg-black/90'
                            : captionPreset === 'neon_viral'
                            ? 'drop-shadow-[0_0_6px_rgba(255,255,0,0.8)]'
                            : 'drop-shadow-[0_1px_2px_rgba(0,0,0,0.9)]'
                        }`}
                        style={{ color: captionTextColor }}
                      >
                        <span>STREAM HIGHLIGHT </span>
                        <span
                          style={{
                            color: captionHighlightColor,
                            textDecoration: captionWordHighlight ? 'underline' : 'none'
                          }}
                        >
                          MOMENT
                        </span>
                      </div>
                    </div>

                    <div className="w-8 h-1 bg-[#2b3140] rounded-full mx-auto" />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: REFRAMING */}
            {activeTab === 'framing' && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  {
                    id: 'center_crop',
                    title: 'Center Smart Crop',
                    desc: 'Stable 9:16 center cutout with pan stabilization. Recommended for gaming streams.'
                  },
                  {
                    id: 'speaker_track',
                    title: 'YuNet Face Tracking',
                    desc: 'Dynamic AI facial detection follows the active speaker across camera pans.'
                  },
                  {
                    id: 'split_screen',
                    title: 'Dual Split Screen',
                    desc: 'Stacked layout showing facecam in top panel and gameplay in bottom panel.'
                  }
                ].map((mode) => {
                  const isSelected = framingMode === mode.id;
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => setFramingMode(mode.id)}
                      className={`p-3.5 rounded-md border text-left transition-colors ${
                        isSelected
                          ? 'bg-[#1c2233] border-[#3b82f6] text-white'
                          : 'bg-[#0c0d11] border-[#1d212b] text-slate-300 hover:border-[#2b3140]'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1">{mode.title}</div>
                      <div className="text-[11px] text-slate-400">{mode.desc}</div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* TAB 3: VIRALITY & DETECTION */}
            {activeTab === 'virality' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-md bg-[#0c0d11] border border-[#1d212b] space-y-2">
                  <div className="text-xs font-semibold text-white mb-2">Scoring Method</div>
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="radio"
                      name="detection_mode"
                      value="heuristic"
                      checked={momentDetectionMode === 'heuristic'}
                      onChange={() => setMomentDetectionMode('heuristic')}
                      className="text-[#2563eb]"
                    />
                    <span>Audio & Energy Peak Analysis (Heuristic)</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="radio"
                      name="detection_mode"
                      value="gemini"
                      checked={momentDetectionMode === 'gemini'}
                      onChange={() => setMomentDetectionMode('gemini')}
                      className="text-[#2563eb]"
                    />
                    <span>Gemini Multimodal Narrative Reasoning</span>
                  </label>
                </div>

                <div className="p-3.5 rounded-md bg-[#0c0d11] border border-[#1d212b] space-y-3 text-xs">
                  <label className="flex items-center justify-between text-slate-300 cursor-pointer">
                    <span>Snap cuts to detected scene boundaries</span>
                    <input
                      type="checkbox"
                      checked={enableSceneDetection}
                      onChange={(e) => setEnableSceneDetection(e.target.checked)}
                      className="rounded text-[#2563eb]"
                    />
                  </label>

                  <div>
                    <div className="flex items-center justify-between text-slate-400 mb-1">
                      <span>Max clips to cut:</span>
                      <span className="font-mono text-white tabular-nums">{maxClips} clips</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={maxClips}
                      onChange={(e) => setMaxClips(parseInt(e.target.value))}
                      className="w-full accent-[#2563eb]"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-slate-400 mb-1">
                      <span>Duration limits:</span>
                      <span className="font-mono text-white tabular-nums">
                        {minClipDuration}s – {maxClipDuration}s
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="range"
                        min="10"
                        max="30"
                        value={minClipDuration}
                        onChange={(e) => setMinClipDuration(parseFloat(e.target.value))}
                        className="w-1/2 accent-[#2563eb]"
                      />
                      <input
                        type="range"
                        min="30"
                        max="90"
                        value={maxClipDuration}
                        onChange={(e) => setMaxClipDuration(parseFloat(e.target.value))}
                        className="w-1/2 accent-[#2563eb]"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Submit Action */}
          <div className="pt-3 border-t border-[#222631] flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">
              Estimated duration: ~3-5 minutes
            </span>
            <button
              type="submit"
              disabled={submitting || !vodUrl.trim()}
              className="px-4 py-2 rounded-md bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-50 text-white text-xs font-semibold transition-colors"
            >
              {submitting ? 'Initializing Pipeline...' : 'Generate 9:16 Clips'}
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
                placeholder="Clippo Task ID (e.g. 70274198...)"
                value={clippoId}
                onChange={(e) => setClippoId(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded bg-[#14161c] border border-[#222631] text-xs text-white"
              />
              <button
                type="submit"
                disabled={clippoSubmitting || !clippoId.trim()}
                className="px-3 py-1.5 rounded bg-[#222631] hover:bg-[#2b3140] text-slate-200 text-xs font-medium disabled:opacity-50"
              >
                {clippoSubmitting ? 'Syncing...' : 'Sync Task'}
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
                Active Job: {activeJob.id}
              </div>
              <div className="text-[11px] text-slate-400">{activeJob.stage}</div>
            </div>
            <span className="text-xs text-blue-400 font-mono tabular-nums">
              {activeJob.progress || 0}%
            </span>
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
