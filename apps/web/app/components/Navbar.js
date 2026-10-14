'use client';

import { Video, Sliders, Film, ArrowUpRight } from 'lucide-react';

export default function Navbar({
  activeView,
  setActiveView,
  backendOnline,
  systemDeps,
  clipsCount,
  jobsCount
}) {
  const depsOk = systemDeps ? Object.values(systemDeps).filter(Boolean).length : 0;
  const totalDeps = systemDeps ? Object.keys(systemDeps).length : 5;

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
              <Film className="w-3.5 h-3.5" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-semibold text-sm tracking-tight text-white">ClipForge</span>
              <span className="text-[11px] text-slate-400 hidden sm:inline">Studio</span>
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
              onClick={() => setActiveView('clips')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeView === 'clips'
                  ? 'bg-[#222631] text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>All Clips</span>
              {clipsCount > 0 && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#2b3140] text-slate-300 font-mono tabular-nums">
                  {clipsCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Right side status & action */}
        <div className="flex items-center gap-3">
          {/* Engine Status */}
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#14161c] border border-[#222631] text-xs">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${
              backendOnline ? 'bg-emerald-500' : 'bg-rose-500'
            }`} />
            <span className="text-slate-300 text-[11px] font-mono tabular-nums">
              {backendOnline === null ? 'Checking...' : backendOnline ? `Engine ${depsOk}/${totalDeps} OK` : 'Offline'}
            </span>
          </div>

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
          onClick={() => setActiveView('clips')}
          className={`flex-1 py-1 rounded text-xs font-medium text-center ${
            activeView === 'clips' ? 'bg-[#222631] text-white' : 'text-slate-400'
          }`}
        >
          All Clips ({clipsCount})
        </button>
      </div>
    </header>
  );
}
