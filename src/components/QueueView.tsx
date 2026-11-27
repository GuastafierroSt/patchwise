import { CheckCircle2, Clock, Trash2, X } from 'lucide-react';
import {
  ActiveDownloadState,
  DesktopApp,
  SessionUpdateRecord,
} from '../core/types';
import { formatMegabytes } from '../core/updaterEngine';
import { ActiveDownloadBanner } from './ActiveDownloadBanner';
import { AppIcon } from './AppIcon';

interface QueueViewProps {
  activeDownload: ActiveDownloadState | null;
  queuedApps: DesktopApp[];
  completedInSession: SessionUpdateRecord[];
  onTogglePause: () => void;
  onCancelDownload: () => void;
  onRemoveFromQueue: (appId: string) => void;
  onClearQueue: () => void;
}

export function QueueView({
  activeDownload,
  queuedApps,
  completedInSession,
  onTogglePause,
  onCancelDownload,
  onRemoveFromQueue,
  onClearQueue,
}: QueueViewProps) {
  return (
    <div className="flex flex-col w-full pb-16 space-y-8">
      <div>
        <h1 className="font-headline text-3xl font-bold text-on-surface">
          Download &amp; Coda Manuale
        </h1>
        <p className="text-xs text-on-surface-variant mt-1">
          Monitora l’applicazione attualmente in download/installazione e gestisci i pacchetti in attesa.
        </p>
      </div>

      {/* Active Download Monitor */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)]">
        <h2 className="font-headline text-lg font-bold text-on-surface">
          Trasferimento Attivo
        </h2>
        <div className="-mt-3">
          <ActiveDownloadBanner
            activeDownload={activeDownload}
            queueLength={queuedApps.length}
            lastCompletedName={completedInSession[0]?.appName ?? null}
            onTogglePause={onTogglePause}
            onCancel={onCancelDownload}
            onOpenQueue={() => {}}
          />
        </div>
      </section>

      {/* Queued Items */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Clock className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 className="font-headline text-lg font-bold text-on-surface">
              In Coda ({queuedApps.length})
            </h2>
          </div>

          {queuedApps.length > 0 && (
            <button
              type="button"
              onClick={onClearQueue}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-low hover:bg-error-container hover:text-error text-xs font-medium text-on-surface-variant transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
              Svuota coda
            </button>
          )}
        </div>

        {queuedApps.length === 0 ? (
          <div className="bg-surface-container-low/70 rounded-xl p-8 text-center">
            <p className="text-xs text-on-surface-variant">
              La coda è vuota. Seleziona più app nella Dashboard e premi “Aggiorna Selezionate” per accodarle.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5" data-testid="queued-items-list">
            {queuedApps.map((app, index) => (
              <div
                key={app.id}
                className="bg-surface-container-low/70 rounded-xl px-4 py-3 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="font-mono text-xs text-on-surface-variant w-5 tabular-nums">
                    #{index + 1}
                  </span>
                  <div className="w-9 h-9 rounded-lg bg-surface-container-lowest flex items-center justify-center text-primary shrink-0">
                    <AppIcon icon={app.icon} className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-on-surface truncate">{app.name}</p>
                    <p className="text-[11px] font-mono text-on-surface-variant tabular-nums">
                      v{app.installedVersion} → v{app.latestVersion} · {formatMegabytes(app.sizeMb)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveFromQueue(app.id)}
                  aria-label={`Rimuovi ${app.name} dalla coda`}
                  className="p-1.5 rounded-lg text-on-surface-variant hover:bg-error-container hover:text-error transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Completed this session */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex items-center gap-2.5">
          <CheckCircle2 className="w-5 h-5 text-tertiary" aria-hidden="true" />
          <h2 className="font-headline text-lg font-bold text-on-surface">
            Completati in Questa Sessione ({completedInSession.length})
          </h2>
        </div>

        {completedInSession.length === 0 ? (
          <p className="text-xs text-on-surface-variant">
            Nessun pacchetto completato finora durante questa sessione.
          </p>
        ) : (
          <div className="space-y-2">
            {completedInSession.map((rec) => (
              <div
                key={rec.id}
                className="bg-surface-container-low/60 rounded-xl px-4 py-3 flex items-center justify-between gap-4 text-xs"
              >
                <div>
                  <span className="font-semibold text-on-surface">{rec.appName}</span>
                  <span className="text-on-surface-variant ml-2 font-mono tabular-nums">
                    v{rec.fromVersion} → v{rec.toVersion}
                  </span>
                </div>
                <span className="font-mono text-[11px] text-tertiary font-semibold tabular-nums">
                  {rec.status === 'success' ? '100% · Installato' : 'Annullato'}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
