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
  ArrowRight
} from 'lucide-react';

export default function GenerateView({
  vodUrl,
  setVodUrl,
  inputError,
  handleUrlChange,
  handleVodSubmit,
  submitting,
  captionPreset,
  setCaptionPreset,
  selectedJobData,
  jobs = [],
  selectedJobId,
  setActiveView
}) {
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

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b border-[#222631] pb-4">
        <h1 className="text-xl font-semibold tracking-tight text-white">Generate Clips</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Paste video link, pilih gaya caption, dan generate klip vertikal 9:16 otomatis.
        </p>
      </div>

      {/* Main Studio Card */}
      <div className="rounded-lg bg-[#14161c] border border-[#222631] p-5 sm:p-6 space-y-6">
        <form onSubmit={handleVodSubmit} className="space-y-6">
          {/* Field 1: Video Link */}
          <div>
            <label htmlFor="vod_url" className="text-xs font-semibold text-white uppercase tracking-wider block mb-2">
              Link Video
            </label>
            <div className="relative">
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
            </div>
            {inputError && <p className="text-[11px] text-rose-400 mt-1">{inputError}</p>}
            <p className="text-[11px] text-slate-500 mt-1 font-mono">
              Mendukung link YouTube, YouTube Shorts, atau file lokal (.mp4, .mkv, .mov)
            </p>
          </div>

          {/* Field 2: Pilihan Caption */}
          <div className="pt-2 border-t border-[#222631]">
            <label className="text-xs font-semibold text-white uppercase tracking-wider block mb-2.5">
              Pilihan Caption
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {captionPresets.map((preset) => {
                const isSelected = captionPreset === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => setCaptionPreset(preset.id)}
                    className={`p-3.5 rounded-md border text-left transition-colors flex flex-col justify-between gap-3 ${
                      isSelected
                        ? 'bg-[#1c2233] border-[#3b82f6] text-white shadow-sm'
                        : 'bg-[#0c0d11] border-[#1d212b] text-slate-300 hover:border-[#2b3140]'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold">{preset.label}</span>
                        {isSelected && (
                          <span className="w-2 h-2 rounded-full bg-blue-400" />
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400">{preset.desc}</p>
                    </div>

                    {/* Miniature caption style preview */}
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

          {/* Submit Action */}
          <div className="pt-3 border-t border-[#222631] flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">
              Otomatis 9:16 reframe + transkrip Whisper
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
      </div>

      {/* Active Pipeline Status (jika ada job aktif) */}
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
