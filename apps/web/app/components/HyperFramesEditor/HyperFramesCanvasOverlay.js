'use client';

import React from 'react';

export default function HyperFramesCanvasOverlay({
  composition,
  currentTime,
  selectedLayerId,
  setSelectedLayerId,
  onUpdateLayer,
  activeCaptionText,
}) {
  if (!composition || !composition.layers) return null;

  const layers = composition.layers || [];
  const hookLayer = layers.find((l) => l.type === 'hook' && l.visible);
  const personLayers = layers.filter((l) => l.type === 'person' && l.visible);
  const captionLayer = layers.find((l) => l.type === 'caption' && l.visible);
  const progressBarLayer = layers.find((l) => l.type === 'progress_bar' && l.visible);

  const duration = composition.duration || 60;
  const progressPercent = Math.min(100, Math.max(0, (currentTime / duration) * 100));

  const isHookActive = hookLayer && currentTime >= hookLayer.start && currentTime <= hookLayer.end;

  return (
    <div className="absolute inset-0 pointer-events-none select-none overflow-hidden z-20">
      {/* 1. Hook Title Banner (Top) */}
      {isHookActive && hookLayer && (
        <div
          onClick={(e) => {
            e.stopPropagation();
            setSelectedLayerId(hookLayer.id);
          }}
          className={`absolute left-2 right-2 p-2 rounded-lg border shadow-lg flex flex-col items-center text-center pointer-events-auto cursor-pointer transition-all ${
            selectedLayerId === hookLayer.id
              ? 'ring-2 ring-amber-400 border-amber-400'
              : 'border-[#293245]'
          }`}
          style={{
            top: `${(hookLayer.y / 1920) * 100}%`,
            background: hookLayer.data?.bg_color || 'rgba(26, 30, 43, 0.94)',
            transform: `scale(${hookLayer.scale || 1})`,
            opacity: hookLayer.opacity !== undefined ? hookLayer.opacity : 1,
          }}
        >
          <div className="flex items-center gap-1 mb-0.5">
            <span className="text-[8px] font-extrabold px-1.5 py-0.2 rounded bg-amber-400 text-black">
              {hookLayer.data?.badge || '★ VIRAL'}
            </span>
            {hookLayer.data?.subtitle && (
              <span className="text-[8px] text-[#aab9c7] font-mono">
                {hookLayer.data.subtitle}
              </span>
            )}
          </div>
          <div
            className="text-[11px] font-extrabold leading-tight tracking-tight uppercase line-clamp-2"
            style={{ color: hookLayer.data?.text_color || '#E9ECEE' }}
          >
            {hookLayer.data?.title || 'VIRAL HOOK TITLE'}
          </div>
        </div>
      )}

      {/* 2. Person Speaker Badges */}
      {personLayers.map((p) => (
        <div
          key={p.id}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedLayerId(p.id);
          }}
          className={`absolute pointer-events-auto cursor-pointer px-1.5 py-0.5 rounded text-[8px] font-mono font-bold uppercase transition-all shadow ${
            selectedLayerId === p.id
              ? 'ring-2 ring-cyan-400 bg-cyan-950/80 text-cyan-300 border border-cyan-500'
              : 'bg-[#1a1e2b]/80 text-[#aab9c7] border border-[#293245]'
          }`}
          style={{
            left: `${(p.x / 1080) * 100}%`,
            top: `${(p.y / 1920) * 100}%`,
            transform: 'translate(-50%, -50%)',
            opacity: p.opacity !== undefined ? p.opacity : 1,
          }}
        >
          {p.data?.badge || 'SPEAKER'}: {p.data?.person_label || 'Speaker'}
        </div>
      ))}

      {/* 3. Live Kinetic Caption Chunk */}
      {captionLayer && activeCaptionText && (
        <div
          onClick={(e) => {
            e.stopPropagation();
            setSelectedLayerId(captionLayer.id);
          }}
          className={`absolute left-2 right-2 text-center pointer-events-auto cursor-pointer transition-all p-1.5 rounded ${
            selectedLayerId === captionLayer.id ? 'ring-1 ring-emerald-400 bg-black/40' : ''
          }`}
          style={{
            bottom: '18%',
          }}
        >
          <span
            className="text-xs font-black uppercase tracking-tight drop-shadow-[0_2px_4px_rgba(0,0,0,0.95)]"
            style={{
              color: captionLayer.data?.text_color || '#FFFFFF',
              fontFamily: captionLayer.data?.font_family === 'Anton' ? 'Impact, sans-serif' : 'Arial Black, sans-serif',
            }}
          >
            {activeCaptionText}
          </span>
        </div>
      )}

      {/* 4. Bottom Progress Bar */}
      {progressBarLayer && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#293245]/60 z-30">
          <div
            className="h-full transition-all duration-75"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: progressBarLayer.data?.color || '#00FF66',
              boxShadow: `0 0 6px ${progressBarLayer.data?.color || '#00FF66'}`,
            }}
          />
        </div>
      )}
    </div>
  );
}
