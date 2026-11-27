import {
  Clock,
  Download,
  FileCode2,
  History,
  LayoutGrid,
  RefreshCw,
} from 'lucide-react';
import { NavSection } from '../core/types';

interface SidebarProps {
  activeSection: NavSection;
  onSelectSection: (section: NavSection) => void;
  pendingCount: number;
  queueCount: number;
  sessionHistoryCount: number;
  lastScanTime: string;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({
  activeSection,
  onSelectSection,
  pendingCount,
  queueCount,
  sessionHistoryCount,
  lastScanTime,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const navItems: Array<{
    id: NavSection;
    label: string;
    icon: typeof RefreshCw;
    count?: number;
    accentCount?: boolean;
  }> = [
    {
      id: 'dashboard',
      label: 'Dashboard & Aggiornamenti',
      icon: RefreshCw,
      count: pendingCount,
      accentCount: pendingCount > 0,
    },
    {
      id: 'all-apps',
      label: 'Tutte le Applicazioni',
      icon: LayoutGrid,
    },
    {
      id: 'history',
      label: 'Cronologia Aggiornamenti',
      icon: History,
      count: sessionHistoryCount,
    },
    {
      id: 'queue',
      label: 'Download & Coda',
      icon: Download,
      count: queueCount,
      accentCount: queueCount > 0,
    },
    {
      id: 'python-export',
      label: 'Python OOP & Build .EXE',
      icon: FileCode2,
    },
  ];

  const handleNav = (id: NavSection) => {
    onSelectSection(id);
    onCloseMobile();
  };

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 top-16 bg-on-surface/25 backdrop-blur-xs z-30 lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        aria-label="Navigazione principale"
        className={`fixed left-0 top-16 bottom-0 w-72 bg-surface-container-low z-40 flex flex-col justify-between p-4 shadow-[1px_0_12px_rgba(0,0,0,0.03)] transition-transform duration-200 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col gap-5">
          <div className="px-3 pt-2">
            <span className="text-[11px] font-semibold tracking-wider text-on-surface-variant">
              Libreria Software
            </span>
          </div>

          <nav className="flex flex-col gap-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleNav(item.id)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`w-full flex items-center justify-between gap-2 px-3.5 py-2.5 rounded-xl text-left text-xs transition-all cursor-pointer ${
                    isActive
                      ? 'bg-primary-container text-on-primary font-semibold shadow-sm'
                      : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface font-medium'
                  }`}
                >
                  <span className="flex items-center gap-3 min-w-0">
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{item.label}</span>
                  </span>
                  {typeof item.count === 'number' && item.count > 0 && (
                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold tabular-nums shrink-0 ${
                        isActive
                          ? 'bg-tertiary text-on-tertiary'
                          : item.accentCount
                            ? 'bg-primary-fixed text-on-primary-fixed-variant'
                            : 'bg-surface-container-high text-on-surface-variant'
                      }`}
                    >
                      {item.count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom system & portable metadata panel */}
        <div className="flex flex-col gap-3 p-3.5 rounded-xl bg-surface-container-lowest shadow-[0_1px_6px_rgba(0,0,0,0.03)]">
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-on-surface-variant">Spazio disco (C:)</span>
              <span className="font-mono font-medium text-on-surface tabular-nums">
                382 / 512 GB
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-surface-container overflow-hidden">
              <div className="h-full bg-primary rounded-full" style={{ width: '74%' }} />
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-on-surface-variant pt-0.5">
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" aria-hidden="true" />
              Ultima scansione
            </span>
            <span className="font-mono font-medium text-on-surface tabular-nums">
              {lastScanTime}
            </span>
          </div>

          <div className="flex items-center justify-between text-[10px] text-on-surface-variant/85 pt-2 bg-surface-container-low/60 -mx-3.5 -mb-3.5 px-3.5 py-2 rounded-b-xl">
            <span className="font-semibold text-on-surface">PatchWise Portable</span>
            <span className="font-mono tabular-nums">v2.5.0</span>
          </div>
        </div>
      </aside>
    </>
  );
}
