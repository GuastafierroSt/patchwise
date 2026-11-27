import { useState } from 'react';
import { CheckCheck, Download, Eye, EyeOff, FolderOpen } from 'lucide-react';
import { ActiveDownloadState, DesktopApp } from '../core/types';
import { filterAllApps, formatMegabytes, hasPendingUpdate } from '../core/updaterEngine';
import { AppIcon } from './AppIcon';

interface AllAppsViewProps {
  apps: DesktopApp[];
  searchQuery: string;
  activeDownload: ActiveDownloadState | null;
  queuedIds: string[];
  onStartSingleUpdate: (appId: string) => void;
  onToggleExclude: (appId: string) => void;
}

export function AllAppsView({
  apps,
  searchQuery,
  activeDownload,
  queuedIds,
  onStartSingleUpdate,
  onToggleExclude,
}: AllAppsViewProps) {
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'up-to-date' | 'excluded'>(
    'all'
  );

  const filtered = filterAllApps(apps, statusFilter, searchQuery);
  const pendingCount = apps.filter(hasPendingUpdate).length;
  const upToDateCount = apps.filter((a) => !hasPendingUpdate(a) && !a.excluded).length;
  const excludedCount = apps.filter((a) => a.excluded).length;

  return (
    <div className="flex flex-col w-full pb-16 space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="font-headline text-3xl font-bold text-on-surface">
            Tutte le Applicazioni ({apps.length})
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Inventario completo rilevato da Registro Windows e Winget. Gestisci esclusioni o avvia aggiornamenti manuali.
          </p>
        </div>

        <div
          role="group"
          aria-label="Filtra elenco applicazioni"
          className="bg-surface-container-low p-1 rounded-xl flex flex-wrap items-center gap-1"
        >
          {(
            [
              { id: 'all', label: `Tutte (${apps.length})` },
              { id: 'pending', label: `Da aggiornare (${pendingCount})` },
              { id: 'up-to-date', label: `Aggiornate (${upToDateCount})` },
              { id: 'excluded', label: `Escluse (${excludedCount})` },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                statusFilter === tab.id
                  ? 'bg-surface-container-lowest text-on-surface font-semibold shadow-xs'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <section className="bg-surface-container-lowest rounded-2xl p-4 sm:p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)] overflow-x-auto">
        {filtered.length === 0 ? (
          <div className="py-12 text-center space-y-2">
            <p className="font-headline text-base font-bold text-on-surface">
              Nessuna applicazione trovata
            </p>
            <p className="text-xs text-on-surface-variant">
              Modifica il filtro di stato o cancella la ricerca per vedere tutti i programmi censiti.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse min-w-[720px]">
            <thead>
              <tr className="text-[11px] font-semibold text-on-surface-variant bg-surface-container-low">
                <th className="py-2.5 px-4 rounded-l-lg">Applicazione</th>
                <th className="py-2.5 px-3">Sorgente</th>
                <th className="py-2.5 px-3">Installata</th>
                <th className="py-2.5 px-3">Online</th>
                <th className="py-2.5 px-3">Dimensione</th>
                <th className="py-2.5 px-4 rounded-r-lg text-right">Azioni Manuali</th>
              </tr>
            </thead>
            <tbody className="text-xs">
              {filtered.map((app) => {
                const pending = hasPendingUpdate(app);
                const isUpdating = activeDownload?.appId === app.id;
                const isQueued = queuedIds.includes(app.id);

                return (
                  <tr
                    key={app.id}
                    className="hover:bg-surface-container-low/60 transition-colors"
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center text-primary shrink-0">
                          <AppIcon icon={app.icon} className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-on-surface truncate">{app.name}</div>
                          <div className="text-[11px] text-on-surface-variant flex items-center gap-1.5 truncate">
                            <span>{app.publisher}</span>
                            <span aria-hidden="true">·</span>
                            <span className="font-mono text-[10px]">{app.wingetId}</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-3 text-on-surface-variant">
                      <span className="inline-flex items-center gap-1.5">
                        <FolderOpen className="w-3.5 h-3.5 text-outline" aria-hidden="true" />
                        {app.source}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[11px] text-on-surface tabular-nums">
                      v{app.installedVersion}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[11px] tabular-nums">
                      <span className={pending ? 'text-primary font-semibold' : 'text-on-surface-variant'}>
                        v{app.latestVersion}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[11px] text-on-surface-variant tabular-nums">
                      {formatMegabytes(app.sizeMb)}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center justify-end gap-2">
                        {pending ? (
                          <button
                            type="button"
                            onClick={() => onStartSingleUpdate(app.id)}
                            disabled={isUpdating || isQueued}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-on-primary text-[11px] font-semibold hover:bg-primary-container disabled:opacity-50 whitespace-nowrap cursor-pointer"
                          >
                            <Download className="w-3.5 h-3.5" aria-hidden="true" />
                            {isUpdating ? 'In corso' : isQueued ? 'In coda' : 'Aggiorna'}
                          </button>
                        ) : app.excluded ? (
                          <span className="text-[11px] font-medium text-on-surface-variant">
                            Esclusa
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-tertiary">
                            <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
                            Aggiornata
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={() => onToggleExclude(app.id)}
                          aria-label={
                            app.excluded
                              ? `Includi ${app.name} nelle scansioni`
                              : `Escludi ${app.name} dalle scansioni`
                          }
                          title={app.excluded ? 'Ripristina in scansione' : 'Escludi da scansione'}
                          className="p-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer"
                        >
                          {app.excluded ? (
                            <Eye className="w-3.5 h-3.5 text-primary" />
                          ) : (
                            <EyeOff className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
