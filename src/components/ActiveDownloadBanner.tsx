import { CheckCircle2, Download, Pause, Play, ShieldCheck, X } from 'lucide-react';
import { ActiveDownloadState } from '../core/types';
import { formatMegabytes } from '../core/updaterEngine';
import { AppIcon } from './AppIcon';

interface ActiveDownloadBannerProps {
  activeDownload: ActiveDownloadState | null;
  queueLength: number;
  lastCompletedName: string | null;
  onTogglePause: () => void;
  onCancel: () => void;
  onOpenQueue: () => void;
}

const PHASE_STEPS = [
  { id: 'downloading', label: '1. Download pacchetto' },
  { id: 'verifying', label: '2. Verifica SHA-256' },
  { id: 'installing', label: '3. Installazione silenziosa' },
] as const;

function getPhaseRank(phase: ActiveDownloadState['phase']): number {
  if (phase === 'downloading' || phase === 'paused') return 0;
  if (phase === 'verifying') return 1;
  if (phase === 'installing') return 2;
  if (phase === 'completed') return 3;
  return 0;
}

export function ActiveDownloadBanner({
  activeDownload,
  queueLength,
  lastCompletedName,
  onTogglePause,
  onCancel,
  onOpenQueue,
}: ActiveDownloadBannerProps) {
  if (!activeDownload) {
    return (
      <div
        data-testid="live-download-banner"
        className="mt-7 bg-surface-container-low rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-surface-container-lowest flex items-center justify-center text-secondary shadow-[0_1px_4px_rgba(0,0,0,0.03)] shrink-0">
            {lastCompletedName ? (
              <CheckCircle2 className="w-5 h-5 text-tertiary" aria-hidden="true" />
            ) : (
              <Download className="w-5 h-5 text-primary" aria-hidden="true" />
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-on-surface">
              {lastCompletedName
                ? `Ultimo aggiornamento completato: ${lastCompletedName}`
                : 'Nessun download attivo in questo momento'}
            </p>
            <p className="text-[11px] text-on-surface-variant">
              Gli aggiornamenti partono solo su tua conferma manuale. Seleziona un’app qui sotto per seguire il download in tempo reale.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[11px] font-mono text-on-surface-variant tabular-nums">
            0% · In attesa
          </span>
        </div>
      </div>
    );
  }

  const isPaused = activeDownload.phase === 'paused';
  const canPause =
    activeDownload.phase === 'downloading' || activeDownload.phase === 'paused';
  const phaseRank = getPhaseRank(activeDownload.phase);

  const phaseHeadline =
    activeDownload.phase === 'paused'
      ? `Download in pausa: ${activeDownload.appName}`
      : activeDownload.phase === 'verifying'
        ? `Verifica firma SHA-256: ${activeDownload.appName}`
        : activeDownload.phase === 'installing'
          ? `Installazione in corso: ${activeDownload.appName}`
          : `Download in corso: ${activeDownload.appName}`;

  return (
    <div
      data-testid="live-download-banner"
      aria-live="polite"
      className="mt-7 bg-surface-container-low rounded-xl p-4 lg:p-5 space-y-3.5 transition-all"
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="w-11 h-11 rounded-xl bg-surface-container-lowest flex items-center justify-center text-primary shadow-[0_1px_4px_rgba(0,0,0,0.04)] shrink-0">
            <AppIcon icon={activeDownload.icon} className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5">
              <span className="font-semibold text-sm text-on-surface truncate">
                {phaseHeadline}
              </span>
              <span className="font-mono text-xs font-semibold text-primary tabular-nums">
                {Math.round(activeDownload.percent)}%
              </span>
              <span className="text-[11px] font-mono text-on-surface-variant tabular-nums">
                v{activeDownload.fromVersion} → v{activeDownload.toVersion}
              </span>
            </div>
            <p className="text-xs text-on-surface-variant mt-0.5 tabular-nums">
              {activeDownload.message} ·{' '}
              {formatMegabytes(activeDownload.downloadedMb)} di{' '}
              {formatMegabytes(activeDownload.totalMb)}
              {activeDownload.phase === 'downloading' && (
                <>
                  {' '}
                  · {activeDownload.speedMbps.toFixed(1)} MB/s · circa{' '}
                  {Math.max(1, activeDownload.etaSeconds)} sec. rimasti
                </>
              )}
              {queueLength > 0 && (
                <>
                  {' '}
                  ·{' '}
                  <button
                    type="button"
                    onClick={onOpenQueue}
                    className="text-primary font-semibold hover:underline cursor-pointer"
                  >
                    +{queueLength} in coda
                  </button>
                </>
              )}
            </p>
          </div>
        </div>

        {/* Determinate progress bar + Pause / Cancel controls */}
        <div className="flex items-center gap-3 w-full lg:w-80 shrink-0">
          <div
            role="progressbar"
            aria-label={`Avanzamento aggiornamento ${activeDownload.appName}`}
            aria-valuenow={Math.round(activeDownload.percent)}
            aria-valuemin={0}
            aria-valuemax={100}
            className="flex-1 h-2.5 rounded-full bg-surface-container-highest overflow-hidden"
          >
            <div
              className={`h-full rounded-full transition-all duration-200 ${
                isPaused ? 'bg-tertiary-container' : 'bg-primary'
              }`}
              style={{ width: `${Math.min(100, Math.max(2, activeDownload.percent))}%` }}
            />
          </div>

          <button
            type="button"
            onClick={onTogglePause}
            disabled={!canPause}
            aria-label={isPaused ? 'Riprendi download' : 'Metti in pausa download'}
            title={isPaused ? 'Riprendi download' : 'Metti in pausa download'}
            className="w-8 h-8 rounded-lg bg-surface-container-lowest hover:bg-surface-container-high text-on-surface flex items-center justify-center transition-colors disabled:opacity-40 cursor-pointer shrink-0"
          >
            {isPaused ? (
              <Play className="w-4 h-4 text-primary" />
            ) : (
              <Pause className="w-4 h-4 text-on-surface-variant" />
            )}
          </button>

          <button
            type="button"
            onClick={onCancel}
            aria-label={`Annulla aggiornamento di ${activeDownload.appName}`}
            title="Annulla aggiornamento"
            className="w-8 h-8 rounded-lg bg-surface-container-lowest hover:bg-error-container text-on-surface-variant hover:text-error flex items-center justify-center transition-colors cursor-pointer shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Subtle 3-step pipeline bar */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px] pt-1">
        {PHASE_STEPS.map((step, idx) => {
          const isDone = phaseRank > idx;
          const isCurrent = phaseRank === idx;
          return (
            <span
              key={step.id}
              className={`inline-flex items-center gap-1.5 ${
                isCurrent
                  ? 'text-primary font-semibold'
                  : isDone
                    ? 'text-tertiary font-medium'
                    : 'text-on-surface-variant/70'
              }`}
            >
              {isDone ? (
                <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
              ) : (
                <span className="font-mono text-[10px]">
                  {isCurrent ? '▸' : '·'}
                </span>
              )}
              {step.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
