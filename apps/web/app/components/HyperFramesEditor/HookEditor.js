'use client';

import React, { useState } from 'react';
import { Type, Sparkles, Sliders, Copy, Check, Loader2 } from 'lucide-react';

export default function HookEditor({
  hookLayer,
  onUpdateHook,
  onGenerateGeminiHook,
  isGeneratingGemini = false,
}) {
  const [copied, setCopied] = useState(false);
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
      {/* Gemini AI Hook Generator Button */}
      {onGenerateGeminiHook && (
        <div className="flex items-center justify-between p-2 rounded-lg bg-[#1a1e2b] border border-amber-400/30">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <div>
              <span className="text-[11px] font-bold text-amber-300 block leading-tight">Gemini AI Studio</span>
              <span className="text-[10px] text-slate-400 block leading-tight">Ekstrak hook viral & caption medsos</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onGenerateGeminiHook}
            disabled={isGeneratingGemini}
            className="px-2.5 py-1 rounded bg-amber-400 hover:bg-amber-300 disabled:opacity-50 text-slate-950 font-bold text-[11px] flex items-center gap-1 transition-colors shadow-sm"
          >
            {isGeneratingGemini ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <span>✨ Generate Hook with Gemini AI</span>
              </>
            )}
          </button>
        </div>
      )}

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
      {/* Social Media Post Caption & Hashtags (TikTok/Reels/Shorts) */}
      <div className="p-2.5 rounded-lg bg-[#141d26] border border-blue-500/30 space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-[11px] font-bold text-blue-300 flex items-center gap-1">
            <span>📱 Social Media Post Caption (TikTok / Reels)</span>
          </div>
          <button
            type="button"
            onClick={() => {
              const captionText = data.social_post_caption || '';
              const tags = Array.isArray(data.hashtags) ? data.hashtags.join(' ') : (data.hashtags || '');
              const fullPost = `${captionText}\n\n${tags}`.trim();
              if (navigator?.clipboard) {
                navigator.clipboard.writeText(fullPost);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }
            }}
            className="px-2 py-0.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium text-[10px] flex items-center gap-1 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-300" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy Post Caption</span>
              </>
            )}
          </button>
        </div>

        <div>
          <label className="text-[10px] text-slate-400 block mb-0.5">Caption Narasi</label>
          <textarea
            rows={3}
            value={data.social_post_caption || ''}
            onChange={(e) => handleChange('social_post_caption', e.target.value)}
            placeholder="Caption medsos yang engaging untuk TikTok/IG Reels/YouTube Shorts..."
            className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-white focus:outline-none focus:border-blue-400"
          />
        </div>

        <div>
          <label className="text-[10px] text-slate-400 block mb-0.5">Hashtags (#tag)</label>
          <input
            type="text"
            value={Array.isArray(data.hashtags) ? data.hashtags.join(' ') : (data.hashtags || '')}
            onChange={(e) => {
              const tags = e.target.value.split(/\s+/).filter(Boolean);
              handleChange('hashtags', tags);
            }}
            placeholder="#viral #podcast #trending #fyp #shorts"
            className="w-full px-2 py-1 rounded bg-[#10121a] border border-[#293245] text-xs text-blue-300 font-mono focus:outline-none focus:border-blue-400"
          />
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
