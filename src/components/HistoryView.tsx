import {
  ArrowRight,
  CheckCircle2,
  Download,
  History,
  Info,
  RotateCcw,
  Trash2,
  XCircle,
} from 'lucide-react';
import { SessionHistoryState, SessionUpdateRecord } from '../core/types';
import { formatMegabytes } from '../core/updaterEngine';

interface HistoryViewProps {
  history: SessionHistoryState;
  onSimulateAppRestart: () => void;
  onClearHistory: () => void;
}

function HistoryRecordList({
  records,
  emptyTitle,
  emptyDescription,
  testId,
}: {
  records: SessionUpdateRecord[];
  emptyTitle: string;
  emptyDescription: string;
  testId: string;
}) {
  if (records.length === 0) {
    return (
      <div
        data-testid={testId}
        className="bg-surface-container-low/70 rounded-xl p-8 text-center space-y-1.5"
      >
        <p className="text-sm font-semibold text-on-surface">{emptyTitle}</p>
        <p className="text-xs text-on-surface-variant max-w-md mx-auto">{emptyDescription}</p>
      </div>
    );
  }

  return (
    <div data-testid={testId} className="space-y-2.5">
      {records.map((rec) => (
        <div
          key={rec.id}
          className="bg-surface-container-low/65 hover:bg-surface-container-low rounded-xl px-4 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors"
        >
          <div className="space-y-1 min-w-0">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="font-headline font-bold text-sm text-on-surface">
                {rec.appName}
              </span>
              <span className="text-xs text-on-surface-variant">{rec.publisher}</span>
              <span aria-hidden="true" className="text-outline-variant">·</span>
              <span className="text-[11px] font-mono text-on-surface-variant">
                {rec.sourceProvider}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-on-surface-variant">
              <span className="font-mono tabular-nums">v{rec.fromVersion}</span>
              <ArrowRight className="w-3.5 h-3.5 text-outline" aria-hidden="true" />
              <span className="font-mono font-semibold text-primary tabular-nums">
                v{rec.toVersion}
              </span>
              <span aria-hidden="true">·</span>
              <span className="font-mono tabular-nums">{formatMegabytes(rec.sizeMb)}</span>
              <span aria-hidden="true">·</span>
              <span className="tabular-nums">{rec.durationSeconds.toFixed(1)}s</span>
              <span aria-hidden="true">·</span>
              <span>{rec.completedAt}</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {rec.status === 'success' ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-tertiary">
                <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                Installato
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-error">
                <XCircle className="w-4 h-4" aria-hidden="true" />
                {rec.status === 'cancelled' ? 'Annullato' : 'Errore'}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export function HistoryView({
  history,
  onSimulateAppRestart,
  onClearHistory,
}: HistoryViewProps) {
  const handleExportJson = () => {
    const payload = JSON.stringify(history, null, 2);
    const blob = new Blob([payload], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'patchwise_session_history.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col w-full pb-16 space-y-8">
      {/* Header & Stateless Controls */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h1 className="font-headline text-3xl font-bold text-on-surface">
            Cronologia Aggiornamenti
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Architettura stateless: tiene traccia in RAM della sessione corrente e conserva alla chiusura solo l’ultima sessione, senza database storici permanenti.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={onSimulateAppRestart}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:bg-primary-container transition-colors whitespace-nowrap cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
            Simula Chiusura e Riapertura
          </button>

          <button
            type="button"
            onClick={handleExportJson}
            disabled={history.currentSession.length === 0 && history.lastSession.length === 0}
            className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium transition-colors disabled:opacity-50 whitespace-nowrap cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            Esporta JSON
          </button>

          <button
            type="button"
            onClick={onClearHistory}
            disabled={history.currentSession.length === 0 && history.lastSession.length === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-surface-container-low hover:bg-error-container hover:text-error text-on-surface-variant text-xs font-medium transition-colors disabled:opacity-50 whitespace-nowrap cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
            Svuota
          </button>
        </div>
      </div>

      {/* Stateless policy callout */}
      <div className="bg-surface-container-lowest rounded-2xl p-5 shadow-[0_1px_8px_rgba(0,0,0,0.03)] flex items-start gap-3.5">
        <div className="w-9 h-9 rounded-xl bg-primary-fixed text-on-primary-fixed-variant flex items-center justify-center shrink-0">
          <Info className="w-4 h-4" aria-hidden="true" />
        </div>
        <div className="space-y-1 text-xs">
          <p className="font-semibold text-on-surface">
            Come funziona la memoria stateless di PatchWise Portable
          </p>
          <p className="text-on-surface-variant leading-relaxed">
            Gli aggiornamenti eseguiti ora risiedono esclusivamente nella memoria RAM (<code className="font-mono text-[11px] text-primary">StatelessSessionHistoryManager</code>). Quando chiudi l’eseguibile portable, viene sovrascritto un unico file volatile (<code className="font-mono text-[11px]">%TEMP%\patchwise_last_session.json</code>) contenente solo questa sessione: tutte le sessioni più vecchie vengono eliminate automaticamente.
          </p>
        </div>
      </div>

      {/* CURRENT SESSION SECTION */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <History className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 className="font-headline text-xl font-bold text-on-surface">
              Sessione Corrente ({history.currentSession.length})
            </h2>
          </div>
          <span className="text-xs font-mono text-on-surface-variant tabular-nums">
            Avviata: {history.currentSessionStartedAt} · Solo RAM
          </span>
        </div>

        <HistoryRecordList
          records={history.currentSession}
          emptyTitle="Nessun aggiornamento eseguito in questa sessione"
          emptyDescription="Torna nella Dashboard e avvia manualmente l’aggiornamento di una o più applicazioni: ogni completamento comparirà qui istantaneamente."
          testId="current-session-history"
        />
      </section>

      {/* LAST CLOSED SESSION SECTION */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-headline text-xl font-bold text-on-surface">
              Ultima Sessione Chiusa ({history.lastSession.length})
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Unico riepilogo conservato dall’ultimo avvio precedente; verrà sostituito alla prossima chiusura.
            </p>
          </div>
          {history.lastSessionStartedAt && (
            <span className="text-xs font-mono text-on-surface-variant tabular-nums">
              {history.lastSessionStartedAt}
            </span>
          )}
        </div>

        <HistoryRecordList
          records={history.lastSession}
          emptyTitle="Nessun aggiornamento registrato nell’ultima sessione"
          emptyDescription="Quando chiudi PatchWise senza eseguire nuovi aggiornamenti, anche lo snapshot precedente viene rimosso automaticamente."
          testId="last-session-history"
        />
      </section>
    </div>
  );
}
