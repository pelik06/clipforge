'use client';

import React from 'react';
import { Eye, EyeOff, Layers, Sliders, Move, ArrowUp, ArrowDown } from 'lucide-react';

export default function HyperFramesLayers({
  layers = [],
  selectedLayerId,
  setSelectedLayerId,
  onUpdateLayer,
  onReorderLayers,
}) {
  const selectedLayer = layers.find((l) => l.id === selectedLayerId) || layers[0];

  const handleToggleVisibility = (layerId) => {
    const l = layers.find((x) => x.id === layerId);
    if (l) {
      onUpdateLayer({ ...l, visible: !l.visible });
    }
  };

  const handleMoveLayerZ = (layerId, delta) => {
    const idx = layers.findIndex((x) => x.id === layerId);
    if (idx < 0) return;
    const targetIdx = idx + delta;
    if (targetIdx < 0 || targetIdx >= layers.length) return;

    const newLayers = [...layers];
    const temp = newLayers[idx];
    newLayers[idx] = newLayers[targetIdx];
    newLayers[targetIdx] = temp;

    // Re-index z_index
    newLayers.forEach((l, i) => {
      l.z_index = i;
    });

    onReorderLayers(newLayers);
  };

  return (
    <div className="space-y-4 text-xs">
      {/* Layers List */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-[11px] text-[#aab9c7] font-semibold uppercase tracking-wider block">
            Composition Layers (Z-Stack)
          </label>
          <span className="text-[10px] text-[#6e8799] font-mono">{layers.length} layers</span>
        </div>

        <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
          {layers.map((l, idx) => {
            const isSelected = selectedLayerId === l.id;
            return (
              <div
                key={l.id}
                onClick={() => setSelectedLayerId(l.id)}
                className={`p-2 rounded-md border flex items-center justify-between gap-2 cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-[#252b3d] border-[#aab9c7] text-[#e9ecee]'
                    : 'bg-[#13151f] border-[#293245] text-[#6e8799] hover:border-[#4c5e6b] hover:text-[#e9ecee]'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="w-4 text-[10px] font-mono text-[#6e8799]">{idx + 1}</span>
                  <span className="font-semibold text-xs truncate">
                    {l.data?.title || l.data?.person_label || l.type.toUpperCase()}
                  </span>
                  <span className="text-[9px] px-1 rounded bg-[#1e2333] border border-[#293245] font-mono uppercase text-[#aab9c7]">
                    {l.type}
                  </span>
                </div>

                <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => handleToggleVisibility(l.id)}
                    className="p-1 rounded text-[#6e8799] hover:text-[#e9ecee]"
                    title="Toggle Visibility"
                  >
                    {l.visible ? <Eye className="w-3.5 h-3.5 text-[#6ee7b7]" /> : <EyeOff className="w-3.5 h-3.5 text-[#6e8799]" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMoveLayerZ(l.id, -1)}
                    disabled={idx === 0}
                    className="p-1 rounded text-[#6e8799] hover:text-[#e9ecee] disabled:opacity-20"
                    title="Move Down"
                  >
                    <ArrowDown className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMoveLayerZ(l.id, 1)}
                    disabled={idx === layers.length - 1}
                    className="p-1 rounded text-[#6e8799] hover:text-[#e9ecee] disabled:opacity-20"
                    title="Move Up"
                  >
                    <ArrowUp className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Layer Properties */}
      {selectedLayer && (
        <div className="p-3 rounded-lg bg-[#13151f] border border-[#293245] space-y-3">
          <div className="flex items-center justify-between border-b border-[#293245] pb-2">
            <span className="font-semibold text-xs text-[#e9ecee] uppercase">
              Transform: {selectedLayer.id}
            </span>
            <span className="text-[10px] text-[#aab9c7] font-mono">
              {selectedLayer.start}s – {selectedLayer.end}s
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <div className="flex justify-between text-[#6e8799] mb-1">
                <span>Scale:</span>
                <span className="font-mono text-[#e9ecee]">{selectedLayer.scale.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                min="0.4"
                max="2.0"
                step="0.05"
                value={selectedLayer.scale}
                onChange={(e) => onUpdateLayer({ ...selectedLayer, scale: parseFloat(e.target.value) })}
                className="w-full accent-[#aab9c7]"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#6e8799] mb-1">
                <span>Opacity:</span>
                <span className="font-mono text-[#e9ecee]">{Math.round(selectedLayer.opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={selectedLayer.opacity}
                onChange={(e) => onUpdateLayer({ ...selectedLayer, opacity: parseFloat(e.target.value) })}
                className="w-full accent-[#aab9c7]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <div className="flex justify-between text-[#6e8799] mb-1">
                <span>Position X:</span>
                <span className="font-mono text-[#e9ecee]">{Math.round(selectedLayer.x)}px</span>
              </div>
              <input
                type="range"
                min="0"
                max="1080"
                step="10"
                value={selectedLayer.x}
                onChange={(e) => onUpdateLayer({ ...selectedLayer, x: parseFloat(e.target.value) })}
                className="w-full accent-[#aab9c7]"
              />
            </div>

            <div>
              <div className="flex justify-between text-[#6e8799] mb-1">
                <span>Position Y:</span>
                <span className="font-mono text-[#e9ecee]">{Math.round(selectedLayer.y)}px</span>
              </div>
              <input
                type="range"
                min="0"
                max="1920"
                step="10"
                value={selectedLayer.y}
                onChange={(e) => onUpdateLayer({ ...selectedLayer, y: parseFloat(e.target.value) })}
                className="w-full accent-[#aab9c7]"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
