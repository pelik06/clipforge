'use client';

import React from 'react';
import { Type, Sparkles, Sliders } from 'lucide-react';

export default function HookEditor({
  hookLayer,
  onUpdateHook,
}) {
  if (!hookLayer) {
    return (
      <div className="p-4 text-center text-xs text-slate-400">
        No active Hook Cover layer in this composition.
      </div>
    );
  }

  const data = hookLayer.data || {};

  const handleChange = (field, value) => {
    onUpdateHook({
      ...hookLayer,
      data: {
        ...data,
        [field]: value,
      },
    });
  };

  const handleAnimationChange = (type) => {
    onUpdateHook({
      ...hookLayer,
      animation_in: {
        ...hookLayer.animation_in,
        type,
      },
    });
  };

  return (
    <div className="space-y-3.5 text-xs">
      {/* Indonesian Viral Hook Fields */}
      <div className="p-2.5 rounded-lg bg-[#161922] border border-[#293245] space-y-2">
        <div className="text-[11px] font-bold text-amber-300 flex items-center gap-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Format Hook Banner Viral (Bahasa Indonesia)</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] text-slate-400 block mb-0.5">Top Tag (Kotak Hitam)</label>
            <input
              type="text"
              value={data.top_tag || ''}
              onChange={(e) => handleChange('top_tag', e.target.value)}
              placeholder="e.g. TIMOTHY / BEVAN"
              className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-white font-bold uppercase focus:outline-none focus:border-amber-400"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-0.5">Badge Tag (Badge Merah)</label>
            <input
              type="text"
              value={data.badge_tag || ''}
              onChange={(e) => handleChange('badge_tag', e.target.value)}
              placeholder="e.g. DI RECALL RECALL"
              className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-red-400 font-bold uppercase focus:outline-none focus:border-red-400"
            />
          </div>
        </div>

        <div>
          <label className="text-[10px] text-slate-400 block mb-0.5">Highlight Headline (Kotak Kuning Besar)</label>
          <input
            type="text"
            value={data.highlight_text || ''}
            onChange={(e) => handleChange('highlight_text', e.target.value)}
            placeholder="e.g. DEPAN MUKA / CUAN 4 MILIAR"
            className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-amber-300 font-extrabold uppercase focus:outline-none focus:border-amber-400"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] text-slate-400 block mb-0.5">Sub Text (Kotak Putih)</label>
            <input
              type="text"
              value={data.sub_text || ''}
              onChange={(e) => handleChange('sub_text', e.target.value)}
              placeholder="e.g. SAMPE DIUSIR"
              className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-white font-bold uppercase focus:outline-none focus:border-white"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-0.5">Punchline (Teks Hijau Neon)</label>
            <input
              type="text"
              value={data.punchline || ''}
              onChange={(e) => handleChange('punchline', e.target.value)}
              placeholder="e.g. SECURITY / NEXT BULL RUN!"
              className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-emerald-400 font-extrabold uppercase focus:outline-none focus:border-emerald-400"
            />
          </div>
        </div>
      </div>

      <div>
        <label className="text-[11px] text-[#aab9c7] font-semibold block mb-1">
          Full Title (Fallback)
        </label>
        <textarea
          rows={2}
          value={data.title || ''}
          onChange={(e) => handleChange('title', e.target.value)}
          placeholder="e.g. FINANCIAL FREEDOM NEXT BULL MARKET"
          className="w-full px-2.5 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-[#e9ecee] uppercase font-bold focus:outline-none focus:border-[#aab9c7]"
        />
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <div>
          <label className="text-[11px] text-[#6e8799] block mb-1">Badge Text</label>
          <input
            type="text"
            value={data.badge || ''}
            onChange={(e) => handleChange('badge', e.target.value)}
            placeholder="★ VIRAL MOMENT"
            className="w-full px-2.5 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-[#e9ecee] font-semibold focus:outline-none focus:border-[#aab9c7]"
          />
        </div>

        <div>
          <label className="text-[11px] text-[#6e8799] block mb-1">Subtitle / Tagline</label>
          <input
            type="text"
            value={data.subtitle || ''}
            onChange={(e) => handleChange('subtitle', e.target.value)}
            placeholder="BEST VIRAL TAKE"
            className="w-full px-2.5 py-1.5 rounded bg-[#13151f] border border-[#293245] text-xs text-[#e9ecee] focus:outline-none focus:border-[#aab9c7]"
          />
        </div>
      </div>

      <div>
        <label className="text-[11px] text-[#6e8799] block mb-1.5">
          In-Animation Style (GSAP Keyframes)
        </label>
        <div className="grid grid-cols-4 gap-1.5">
          {[
            { id: 'spring', label: 'Spring' },
            { id: 'pop', label: 'Pop' },
            { id: 'slide_down', label: 'Slide' },
            { id: 'fade', label: 'Fade' },
          ].map((anim) => (
            <button
              key={anim.id}
              type="button"
              onClick={() => handleAnimationChange(anim.id)}
              className={`py-1.5 rounded text-[11px] font-medium border transition-colors ${
                hookLayer.animation_in?.type === anim.id
                  ? 'bg-[#252b3d] border-[#aab9c7] text-[#e9ecee]'
                  : 'bg-[#13151f] border-[#293245] text-[#6e8799] hover:text-[#e9ecee]'
              }`}
            >
              {anim.label}
            </button>
          ))}
        </div>
      </div>

      <div className="pt-2 border-t border-[#293245] space-y-2">
        <div className="flex justify-between items-center text-[11px] text-[#6e8799]">
          <span>Hook Duration:</span>
          <span className="font-mono text-[#e9ecee]">{hookLayer.duration.toFixed(1)}s</span>
        </div>
        <input
          type="range"
          min="3.0"
          max="20.0"
          step="0.5"
          value={hookLayer.duration}
          onChange={(e) => {
            const newDur = parseFloat(e.target.value);
            onUpdateHook({
              ...hookLayer,
              end: Math.round((hookLayer.start + newDur) * 10) / 10,
            });
          }}
          className="w-full accent-[#aab9c7]"
        />
      </div>
    </div>
  );
}
