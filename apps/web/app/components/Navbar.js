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
    <header className="sticky top-0 z-50 w-full border-b border-[#222631] bg-[#0c0d11]/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand & Workspace */}
        <div className="flex items-center gap-6">
          <button 
            onClick={() => setActiveView('dashboard')}
            className="flex items-center gap-2.5 group text-left"
          >
            <div className="w-7 h-7 rounded bg-[#1c202a] border border-[#2b3140] flex items-center justify-center text-slate-200 group-hover:border-[#3b82f6] group-hover:text-white transition-colors">
              <Film className="w-3.5 h-3.5" aria-hidden="true" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-semibold text-sm tracking-tight text-white">ClipForge</span>
              <span className="text-[11px] text-slate-400 hidden sm:inline">Studio</span>
              <span className="text-[10px] uppercase font-mono px-1 py-0.2 rounded bg-[#1c202a] border border-[#2b3140] text-blue-300 font-semibold">
                v0.4.0
              </span>
            </div>
          </button>

          {/* Navigation Segmented Switcher */}
          <nav className="hidden md:flex items-center bg-[#14161c] p-0.5 rounded-lg border border-[#222631]">
            <button
              onClick={() => setActiveView('dashboard')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                activeView === 'dashboard'
                  ? 'bg-[#222631] text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Dashboard
            </button>

            <button
              onClick={() => setActiveView('generate')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                activeView === 'generate'
                  ? 'bg-[#222631] text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Generate Studio
            </button>

            <button
              onClick={() => setActiveView('clips')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeView === 'clips'
                  ? 'bg-[#222631] text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>Review Queue</span>
              {clipsCount > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#2b3140] text-slate-300 font-mono tabular-nums">
                  {clipsCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Right side status indicators (from master) */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono">
            <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
              systemDeps?.ytdlp_available
                ? 'bg-[#14261d] text-emerald-300 border-emerald-800/40'
                : 'bg-[#14161c] text-slate-400 border-[#222631]'
            }`}>
              <span>yt-dlp:</span>
              <span className="font-bold">{systemDeps?.ytdlp_available ? 'Ready' : 'Checking'}</span>
            </span>

            <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
              systemDeps?.ffmpeg_available
                ? 'bg-[#14261d] text-emerald-300 border-emerald-800/40'
                : 'bg-[#261f14] text-amber-300 border-amber-800/40'
            }`}>
              <span>FFmpeg:</span>
              <span className="font-bold">{systemDeps?.ffmpeg_available ? 'Detected' : 'Pending'}</span>
            </span>

            <span className="px-2 py-0.5 rounded border hidden sm:flex items-center gap-1 bg-[#14161c] text-slate-300 border-[#222631]">
              <Database className="w-3 h-3 text-slate-400" aria-hidden="true" />
              <span>SQLite:</span>
              <span className="font-bold text-slate-200">Persistent</span>
            </span>

            <div className="flex items-center gap-1.5 pl-1">
              <span className={`w-2 h-2 rounded-full ${backendOnline ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              <span className={backendOnline ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                {backendOnline ? 'API Active' : 'Offline'}
              </span>
            </div>
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              title="Refresh queue"
              aria-label="Refresh queue"
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-[#1c202a] rounded-md transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          )}

          {/* New Clip Action */}
          <button
            onClick={() => setActiveView('generate')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#2563eb] hover:bg-[#1d4ed8] text-white text-xs font-medium transition-colors active:scale-98"
          >
            <span>+ New Clip</span>
          </button>
        </div>
      </div>

      {/* Mobile nav bar */}
      <div className="md:hidden flex items-center justify-around border-t border-[#222631] bg-[#0c0d11] px-2 py-1.5">
        <button
          onClick={() => setActiveView('dashboard')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'dashboard' ? 'bg-[#222631] text-white' : 'text-slate-400'
          }`}
        >
          Dashboard
        </button>
        <button
          onClick={() => setActiveView('generate')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'generate' ? 'bg-[#222631] text-white' : 'text-slate-400'
          }`}
        >
          Generate
        </button>
        <button
          onClick={() => setActiveView('clips')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'clips' ? 'bg-[#222631] text-white' : 'text-slate-400'
          }`}
        >
          Clips ({clipsCount})
        </button>
      </div>
    </header>
  );
}
