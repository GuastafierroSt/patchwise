import { Menu, RefreshCw, Search, ShieldCheck, X } from 'lucide-react';
import { PatchWiseLogo } from './AppIcon';

interface TopHeaderProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  isScanning: boolean;
  onTriggerScan: () => void;
  onToggleMobileMenu: () => void;
  mobileMenuOpen: boolean;
}

export function TopHeader({
  searchQuery,
  onSearchChange,
  isScanning,
  onTriggerScan,
  onToggleMobileMenu,
  mobileMenuOpen,
}: TopHeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 z-50 bg-surface/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] flex items-center justify-between gap-4 px-4 lg:px-6">
      {/* Left: Desktop window accents + Brand */}
      <div className="flex items-center gap-3 lg:min-w-[256px] shrink-0">
        <button
          type="button"
          onClick={onToggleMobileMenu}
          aria-label={mobileMenuOpen ? 'Chiudi menu di navigazione' : 'Apri menu di navigazione'}
          className="lg:hidden w-9 h-9 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high transition-colors"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <div className="hidden sm:flex items-center gap-1.5 pr-1.5" aria-hidden="true">
          <span className="w-2.5 h-2.5 rounded-full bg-error/70" />
          <span className="w-2.5 h-2.5 rounded-full bg-tertiary-container/85" />
          <span className="w-2.5 h-2.5 rounded-full bg-primary/65" />
        </div>

        <div className="flex items-center gap-2.5 whitespace-nowrap shrink-0">
          <PatchWiseLogo className="w-8 h-8 shrink-0" />
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-tight text-on-surface leading-tight">
              PatchWise
            </span>
            <span className="text-[11px] text-on-surface-variant leading-none">
              Software Updater
            </span>
          </div>
        </div>
      </div>

      {/* Center: Live Search */}
      <div className="flex-1 max-w-xl">
        <div className="relative flex items-center">
          <Search
            className="w-4 h-4 absolute left-3.5 text-on-surface-variant pointer-events-none"
            aria-hidden="true"
          />
          <label htmlFor="global-app-search" className="sr-only">
            Cerca programmi installati o aggiornamenti
          </label>
          <input
            id="global-app-search"
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Cerca programmi installati, editore o ID Winget..."
            className="w-full h-9 pl-10 pr-8 rounded-xl bg-surface-container-lowest text-xs text-on-surface placeholder:text-on-surface-variant/70 focus:outline-none focus:ring-2 focus:ring-primary/35 shadow-[0_1px_4px_rgba(0,0,0,0.03)] transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              aria-label="Cancella ricerca"
              className="absolute right-2.5 p-0.5 rounded text-on-surface-variant hover:text-on-surface"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Right: Manual-only indicator & Quick Scan Action */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="hidden md:flex items-center gap-1.5 text-xs text-on-surface-variant whitespace-nowrap">
          <ShieldCheck className="w-4 h-4 text-primary" aria-hidden="true" />
          <span>Solo manuale · Stateless</span>
        </div>

        <button
          type="button"
          onClick={onTriggerScan}
          disabled={isScanning}
          aria-label="Avvia scansione rapida delle applicazioni"
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-container-low hover:bg-surface-container-high text-xs font-semibold text-on-surface transition-colors disabled:opacity-60 whitespace-nowrap shrink-0 cursor-pointer"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 text-primary ${isScanning ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          <span className="hidden sm:inline">{isScanning ? 'Scansione...' : 'Scansiona'}</span>
        </button>
      </div>
    </header>
  );
}
