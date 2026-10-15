'use client';

import { Film, Database, RefreshCw, Sparkles, Video, Cpu } from 'lucide-react';

export default function Navbar({
  activeView,
  setActiveView,
  backendOnline,
  systemDeps,
  clipsCount,
  onRefresh
}) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#293245] bg-[#13151f]/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand & Workspace */}
        <div className="flex items-center gap-6">
          <button 
            onClick={() => setActiveView('dashboard')}
            className="flex items-center gap-2.5 group text-left"
          >
            <div className="w-7 h-7 rounded bg-[#1a1e2b] border border-[#293245] flex items-center justify-center text-[#e9ecee] group-hover:border-[#aab9c7] group-hover:text-white transition-colors">
              <Film className="w-3.5 h-3.5 text-[#aab9c7]" aria-hidden="true" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-semibold text-sm tracking-tight text-[#e9ecee]">ClipForge</span>
              <span className="text-[11px] text-[#6e8799] hidden sm:inline">Studio</span>
              <span className="text-[10px] uppercase font-mono px-1 py-0.2 rounded bg-[#1e2333] border border-[#293245] text-[#aab9c7] font-semibold">
                v0.4.0
              </span>
            </div>
          </button>

          {/* Navigation Segmented Switcher */}
          <nav className="hidden md:flex items-center bg-[#1a1e2b] p-0.5 rounded-lg border border-[#293245]">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                activeView === 'dashboard'
                  ? 'bg-[#252b3d] text-[#e9ecee] border border-[#4c5e6b] shadow-sm'
                  : 'text-[#6e8799] hover:text-[#e9ecee]'
              }`}
            >
              Dashboard
            </button>

            <button
              onClick={() => setActiveView('generate')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                activeView === 'generate'
                  ? 'bg-[#252b3d] text-[#e9ecee] border border-[#4c5e6b] shadow-sm'
                  : 'text-[#6e8799] hover:text-[#e9ecee]'
              }`}
            >
              Generate Studio
            </button>

            <button
              onClick={() => setActiveView('clips')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeView === 'clips'
                  ? 'bg-[#252b3d] text-[#e9ecee] border border-[#4c5e6b] shadow-sm'
                  : 'text-[#6e8799] hover:text-[#e9ecee]'
              }`}
            >
              <span>Review Queue</span>
              {clipsCount > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#1e2333] text-[#aab9c7] font-mono tabular-nums border border-[#293245]">
                  {clipsCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Right side status indicators */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono">
            <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
              systemDeps?.ytdlp_available
                ? 'bg-[#14261d] text-[#6ee7b7] border-[#1f4a3d]'
                : 'bg-[#1a1e2b] text-[#6e8799] border-[#293245]'
            }`}>
              <span>yt-dlp:</span>
              <span className="font-bold">{systemDeps?.ytdlp_available ? 'Ready' : 'Checking'}</span>
            </span>

            <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
              systemDeps?.ffmpeg_available
                ? 'bg-[#14261d] text-[#6ee7b7] border-[#1f4a3d]'
                : 'bg-[#2a2318] text-[#fcd34d] border-[#4d3e23]'
            }`}>
              <span>FFmpeg:</span>
              <span className="font-bold">{systemDeps?.ffmpeg_available ? 'Detected' : 'Pending'}</span>
            </span>

            <span className="px-2 py-0.5 rounded border hidden sm:flex items-center gap-1 bg-[#1a1e2b] text-[#aab9c7] border-[#293245]">
              <Database className="w-3 h-3 text-[#6e8799]" aria-hidden="true" />
              <span>SQLite:</span>
              <span className="font-bold text-[#e9ecee]">Persistent</span>
            </span>

            <div className="flex items-center gap-1.5 pl-1">
              <span className={`inline-block w-2 h-2 rounded-full ${
                backendOnline ? 'bg-[#6ee7b7]' : 'bg-[#f87171]'
              }`} />
              <span className="text-[11px] text-[#6e8799]">
                {backendOnline ? 'Online' : 'Offline'}
              </span>
            </div>
          </div>

          <button
            onClick={onRefresh}
            title="Refresh workspace status"
            className="p-1.5 rounded-md text-[#6e8799] hover:text-[#e9ecee] hover:bg-[#1a1e2b] border border-transparent hover:border-[#293245] transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Mobile Segmented Navigation */}
      <div className="md:hidden border-t border-[#293245] bg-[#1a1e2b] px-3 py-1.5 flex items-center justify-between gap-1">
        <button
          onClick={() => setActiveView('dashboard')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'dashboard' ? 'bg-[#252b3d] text-[#e9ecee] border border-[#4c5e6b]' : 'text-[#6e8799]'
          }`}
        >
          Dashboard
        </button>
        <button
          onClick={() => setActiveView('generate')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'generate' ? 'bg-[#252b3d] text-[#e9ecee] border border-[#4c5e6b]' : 'text-[#6e8799]'
          }`}
        >
          Generate
        </button>
        <button
          onClick={() => setActiveView('clips')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'clips' ? 'bg-[#252b3d] text-[#e9ecee] border border-[#4c5e6b]' : 'text-[#6e8799]'
          }`}
        >
          Queue {clipsCount > 0 ? `(${clipsCount})` : ''}
        </button>
      </div>
    </header>
  );
}
