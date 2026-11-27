import { useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCheck,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  Database,
  Download,
  FileText,
  History,
  MoreVertical,
  Radar,
  ShieldCheck,
  Sparkles,
  Square,
  X,
} from 'lucide-react';
import {
  ActiveDownloadState,
  DashboardMetrics,
  DesktopApp,
  UpdateCategory,
} from '../core/types';
import {
  filterPendingApps,
  formatMegabytes,
  hasPendingUpdate,
} from '../core/updaterEngine';
import { ActiveDownloadBanner } from './ActiveDownloadBanner';
import { AppIcon } from './AppIcon';

interface DashboardViewProps {
  apps: DesktopApp[];
  metrics: DashboardMetrics;
  searchQuery: string;
  lastScanAt: string;
  isScanning: boolean;
  scanStageMessage: string;
  compatibilityChecked: boolean;
  activeDownload: ActiveDownloadState | null;
  queuedIds: string[];
  lastCompletedName: string | null;
  onTriggerScan: () => void;
  onVerifyCompatibility: () => void;
  onToggleSelect: (appId: string) => void;
  onToggleSelectAll: () => void;
  onStartSingleUpdate: (appId: string) => void;
  onStartSelectedUpdates: () => void;
  onTogglePause: () => void;
  onCancelDownload: () => void;
  onSkipVersion: (appId: string) => void;
  onExcludeApp: (appId: string) => void;
  onOpenQueue: () => void;
}

export function DashboardView({
  apps,
  metrics,
  searchQuery,
  lastScanAt,
  isScanning,
  scanStageMessage,
  compatibilityChecked,
  activeDownload,
  queuedIds,
  lastCompletedName,
  onTriggerScan,
  onVerifyCompatibility,
  onToggleSelect,
  onToggleSelectAll,
  onStartSingleUpdate,
  onStartSelectedUpdates,
  onTogglePause,
  onCancelDownload,
  onSkipVersion,
  onExcludeApp,
  onOpenQueue,
}: DashboardViewProps) {
  const [categoryFilter, setCategoryFilter] = useState<'all' | UpdateCategory>('all');
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [releaseNotesApp, setReleaseNotesApp] = useState<DesktopApp | null>(null);
  const [updatedAccordionOpen, setUpdatedAccordionOpen] = useState(false);

  const allPending = apps.filter(hasPendingUpdate);
  const visiblePending = filterPendingApps(apps, categoryFilter, searchQuery);
  const upToDateApps = apps.filter((a) => !hasPendingUpdate(a) && !a.excluded);
  const selectedPending = allPending.filter((a) => a.selected);
  const selectedSizeMb = selectedPending.reduce((acc, item) => acc + item.sizeMb, 0);
  const allSelected = allPending.length > 0 && selectedPending.length === allPending.length;

  const securityCount = allPending.filter((a) => a.category === 'security').length;
  const featuresCount = allPending.filter((a) => a.category === 'features').length;
  const patchCount = allPending.filter((a) => a.category === 'patch').length;

  const categoryLabel = (cat: UpdateCategory) => {
    if (cat === 'security') return 'Critico · Sicurezza';
    if (cat === 'features') return 'Nuove Funzionalità';
    return 'Bugfix & Stabilità';
  };

  return (
    <div className="flex flex-col w-full pb-16 space-y-9">
      {/* HERO SUMMARY & SCAN ACTION */}
      <section className="relative overflow-hidden rounded-2xl bg-surface-container-lowest p-7 lg:p-9 shadow-[0_2px_16px_rgba(27,28,29,0.04)]">
        <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-2.5">
            <p className="text-xs font-semibold text-tertiary tracking-wide">
              {isScanning
                ? scanStageMessage
                : compatibilityChecked
                  ? 'Controllo integrità e compatibilità firme SHA-256 completato'
                  : 'Controllo integrità completato · Aggiornamento esclusivamente manuale'}
            </p>
            <h1 className="font-headline text-3xl lg:text-4xl font-bold tracking-tight text-on-surface leading-tight">
              {isScanning
                ? 'Scansione applicazioni in corso...'
                : metrics.pendingCount > 0
                  ? `${metrics.pendingCount} aggiornamenti disponibili trovati`
                  : 'Tutte le applicazioni sono aggiornate'}
            </h1>
            <p className="text-xs sm:text-sm text-on-surface-variant flex flex-wrap items-center gap-x-2 gap-y-1">
              <History className="w-4 h-4 text-outline shrink-0" aria-hidden="true" />
              <span>
                Ultima scansione: <strong className="font-medium text-on-surface">{lastScanAt}</strong>
              </span>
              <span aria-hidden="true" className="hidden sm:inline">·</span>
              <span className="tabular-nums">
                {metrics.totalInstalled} app censite (Registro Windows &amp; Winget)
              </span>
            </p>
          </div>

          <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 self-start xl:self-center shrink-0">
            <button
              type="button"
              onClick={onTriggerScan}
              disabled={isScanning}
              className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold text-xs transition-colors disabled:opacity-60 whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Radar
                className={`w-4 h-4 text-primary ${isScanning ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
              <span>{isScanning ? 'Analisi in corso...' : 'Nuova Scansione'}</span>
            </button>

            <button
              type="button"
              onClick={onStartSelectedUpdates}
              disabled={selectedPending.length === 0 || isScanning}
              className="inline-flex items-center gap-3 px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-container text-on-primary font-semibold text-xs shadow-sm hover:brightness-105 active:scale-[0.99] transition-all disabled:opacity-45 disabled:cursor-not-allowed whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Download className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span className="flex flex-col text-left leading-tight">
                <span>Aggiorna Selezionate ({selectedPending.length})</span>
                <span className="text-[10px] text-on-primary-container font-normal tabular-nums">
                  {formatMegabytes(selectedSizeMb)} totali stimati
                </span>
              </span>
            </button>

            <button
              type="button"
              onClick={onVerifyCompatibility}
              disabled={isScanning || allPending.length === 0}
              className="px-4 py-3 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface font-medium text-xs transition-colors disabled:opacity-50 whitespace-nowrap shrink-0 cursor-pointer"
            >
              {compatibilityChecked ? 'Firme Verificate' : 'Compatibilità'}
            </button>
          </div>
        </div>

        {/* LIVE DOWNLOAD / INSTALL PROGRESS BAR */}
        <ActiveDownloadBanner
          activeDownload={activeDownload}
          queueLength={queuedIds.length}
          lastCompletedName={lastCompletedName}
          onTogglePause={onTogglePause}
          onCancel={onCancelDownload}
          onOpenQueue={onOpenQueue}
        />
      </section>

      {/* KPI METRIC CARDS */}
      <section aria-label="Indicatori di stato" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="bg-surface-container-lowest p-5 rounded-xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] flex items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-on-surface-variant">App Censite</span>
            <div className="font-headline text-2xl font-bold text-on-surface tabular-nums">
              {metrics.totalInstalled}
            </div>
            <p className="text-[11px] text-on-surface-variant">Registro Windows e Winget</p>
          </div>
          <div className="w-11 h-11 rounded-xl bg-surface-container flex items-center justify-center text-secondary shrink-0">
            <Database className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>

        <div className="bg-surface-container-lowest p-5 rounded-xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] flex items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-error">Aggiornamenti Critici</span>
            <div className="font-headline text-2xl font-bold text-error tabular-nums">
              {metrics.criticalCount}
            </div>
            <p className="text-[11px] text-on-surface-variant">Patch urgenti di sicurezza</p>
          </div>
          <div className="w-11 h-11 rounded-xl bg-error-container text-on-error-container flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>

        <div className="bg-surface-container-lowest p-5 rounded-xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] flex items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-tertiary">Recupero Spazio</span>
            <div className="font-headline text-2xl font-bold text-on-surface tabular-nums">
              {formatMegabytes(metrics.estimatedCleanupMb)}
            </div>
            <p className="text-[11px] text-on-surface-variant">Cache installer temporanei</p>
          </div>
          <div className="w-11 h-11 rounded-xl bg-surface-container-high text-tertiary flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>

        <div className="bg-surface-container-lowest p-5 rounded-xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] flex items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-on-surface-variant">Patch CVE Rilevate</span>
            <div className="font-headline text-2xl font-bold text-primary tabular-nums">
              {metrics.zeroDayCount > 0 ? `${metrics.zeroDayCount} Attive` : 'Nessuna'}
            </div>
            <p className="text-[11px] text-on-surface-variant">Protezione vulnerabilità note</p>
          </div>
          <div className="w-11 h-11 rounded-xl bg-primary-fixed text-on-primary-fixed-variant flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>
      </section>

      {/* PENDING UPDATES DIRECTORY */}
      <section className="space-y-5">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h2 className="font-headline text-2xl font-bold text-on-surface">
              Aggiornamenti in Sospeso
            </h2>
            <p className="text-xs text-on-surface-variant mt-1">
              Avvia ogni aggiornamento manualmente: l’auto-update automatico è disabilitato per tua sicurezza.
            </p>
          </div>

          {/* Interactive category segmented filter + Select all */}
          <div className="flex flex-wrap items-center gap-2">
            <div
              role="group"
              aria-label="Filtra aggiornamenti per categoria"
              className="bg-surface-container-low p-1 rounded-xl flex items-center gap-1"
            >
              {(
                [
                  { id: 'all', label: `Tutti (${allPending.length})` },
                  { id: 'security', label: `Sicurezza (${securityCount})` },
                  { id: 'features', label: `Novità (${featuresCount})` },
                  { id: 'patch', label: `Bugfix (${patchCount})` },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setCategoryFilter(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    categoryFilter === tab.id
                      ? 'bg-surface-container-lowest text-on-surface shadow-[0_1px_4px_rgba(0,0,0,0.05)] font-semibold'
                      : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {allPending.length > 0 && (
              <button
                type="button"
                onClick={onToggleSelectAll}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container-low hover:bg-surface-container text-xs text-on-surface font-medium transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                {allSelected ? (
                  <CheckSquare className="w-4 h-4 text-primary" aria-hidden="true" />
                ) : (
                  <Square className="w-4 h-4 text-outline" aria-hidden="true" />
                )}
                <span>{allSelected ? 'Deseleziona tutti' : 'Seleziona tutti'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Pending software cards — STRICTLY NO AUTO-UPDATE TOGGLE */}
        {visiblePending.length === 0 ? (
          <div className="bg-surface-container-lowest rounded-2xl p-10 text-center space-y-3 shadow-[0_1px_8px_rgba(0,0,0,0.03)]">
            <CheckCircle2 className="w-10 h-10 text-tertiary mx-auto" aria-hidden="true" />
            <h3 className="font-headline text-lg font-bold text-on-surface">
              {allPending.length === 0
                ? 'Nessun aggiornamento in sospeso'
                : 'Nessun risultato per i filtri attivi'}
            </h3>
            <p className="text-xs text-on-surface-variant max-w-md mx-auto">
              {allPending.length === 0
                ? 'Tutte le applicazioni installate risultano allineate alle versioni più recenti verificate online.'
                : 'Prova a cambiare categoria o a rimuovere il testo dalla barra di ricerca in alto.'}
            </p>
            {allPending.length === 0 && (
              <button
                type="button"
                onClick={onTriggerScan}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-container-high hover:bg-surface-container-highest text-xs font-semibold text-on-surface transition-colors cursor-pointer"
              >
                <Radar className="w-4 h-4 text-primary" aria-hidden="true" />
                Esegui una nuova scansione
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col space-y-3" data-testid="pending-updates-list">
            {visiblePending.map((app) => {
              const isUpdatingThis = activeDownload?.appId === app.id;
              const isQueuedThis = queuedIds.includes(app.id);
              const menuOpen = openMenuId === app.id;

              return (
                <article
                  key={app.id}
                  data-testid={`update-card-${app.id}`}
                  className="bg-surface-container-lowest rounded-xl p-5 shadow-[0_1px_8px_rgba(0,0,0,0.03)] hover:shadow-[0_4px_16px_rgba(27,28,29,0.06)] transition-shadow"
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0">
                      <input
                        type="checkbox"
                        checked={app.selected}
                        onChange={() => onToggleSelect(app.id)}
                        disabled={isUpdatingThis || isQueuedThis}
                        aria-label={`Seleziona ${app.name} per aggiornamento multiplo`}
                        className="mt-2 w-4 h-4 rounded accent-primary cursor-pointer shrink-0"
                      />

                      <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center text-primary shrink-0">
                        <AppIcon icon={app.icon} className="w-6 h-6" />
                      </div>

                      <div className="space-y-1.5 min-w-0">
                        <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-0.5">
                          <h3 className="font-headline font-bold text-base text-on-surface">
                            {app.name}
                          </h3>
                          <span className="text-xs text-on-surface-variant">{app.publisher}</span>
                          <span aria-hidden="true" className="text-outline-variant">·</span>
                          <span
                            className={`text-xs font-semibold ${
                              app.category === 'security'
                                ? 'text-error'
                                : app.category === 'features'
                                  ? 'text-primary'
                                  : 'text-on-surface-variant'
                            }`}
                          >
                            {categoryLabel(app.category)}
                          </span>
                          {app.compatibilityVerified && (
                            <>
                              <span aria-hidden="true" className="text-outline-variant">·</span>
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-tertiary">
                                <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
                                Firma SHA-256 OK
                              </span>
                            </>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-on-surface-variant">
                          <span>
                            Attuale:{' '}
                            <strong className="font-mono text-on-surface tabular-nums">
                              {app.installedVersion}
                            </strong>
                          </span>
                          <ArrowRight className="w-3.5 h-3.5 text-outline" aria-hidden="true" />
                          <span>
                            Disponibile:{' '}
                            <strong className="font-mono text-primary tabular-nums">
                              {app.latestVersion}
                            </strong>
                          </span>
                          <span aria-hidden="true" className="text-outline">·</span>
                          <span className="font-mono font-medium text-on-surface tabular-nums">
                            {formatMegabytes(app.sizeMb)}
                          </span>
                          <span aria-hidden="true" className="text-outline">·</span>
                          <span className="text-[11px]">{app.source}</span>
                        </div>

                        <p className="text-xs text-on-surface-variant max-w-2xl leading-relaxed">
                          {app.releaseNotes}
                        </p>

                        {/* Inline mini progress bar on the actively updating card */}
                        {isUpdatingThis && activeDownload && (
                          <div className="pt-2 max-w-md space-y-1">
                            <div className="flex items-center justify-between text-[11px] font-mono tabular-nums">
                              <span className="text-primary font-semibold">
                                {activeDownload.phase === 'paused'
                                  ? 'In pausa'
                                  : activeDownload.phase === 'verifying'
                                    ? 'Verifica SHA-256...'
                                    : activeDownload.phase === 'installing'
                                      ? 'Installazione...'
                                      : 'Download in corso...'}
                              </span>
                              <span className="text-on-surface font-semibold">
                                {Math.round(activeDownload.percent)}%
                              </span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-surface-container-highest overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full transition-all duration-200"
                                style={{ width: `${activeDownload.percent}%` }}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right actions: strictly manual trigger + overflow menu (NO Auto-Update toggle!) */}
                    <div className="flex items-center justify-end gap-2.5 shrink-0 pt-2 lg:pt-0">
                      <button
                        type="button"
                        onClick={() => onStartSingleUpdate(app.id)}
                        disabled={isUpdatingThis || isQueuedThis}
                        aria-label={`Aggiorna ora ${app.name}`}
                        className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                          isUpdatingThis
                            ? 'bg-primary-fixed text-on-primary-fixed-variant cursor-default'
                            : isQueuedThis
                              ? 'bg-surface-container text-on-surface-variant cursor-default'
                              : 'bg-primary text-on-primary hover:bg-primary-container shadow-sm active:scale-[0.98]'
                        }`}
                      >
                        {isUpdatingThis
                          ? `In corso (${Math.round(activeDownload?.percent ?? 0)}%)`
                          : isQueuedThis
                            ? 'In coda...'
                            : 'Aggiorna Ora'}
                      </button>

                      <div className="relative">
                        <button
                          type="button"
                          onClick={() => setOpenMenuId(menuOpen ? null : app.id)}
                          aria-label={`Altre opzioni per ${app.name}`}
                          aria-expanded={menuOpen}
                          className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors cursor-pointer"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>

                        {menuOpen && (
                          <div className="absolute right-0 top-full mt-1 w-52 bg-surface-container-lowest/95 backdrop-blur-xl rounded-xl shadow-[0_12px_32px_rgba(27,28,29,0.12)] py-1.5 z-30 flex flex-col">
                            <button
                              type="button"
                              onClick={() => {
                                setReleaseNotesApp(app);
                                setOpenMenuId(null);
                              }}
                              className="px-3.5 py-2 text-left text-xs text-on-surface hover:bg-surface-container-low flex items-center gap-2 cursor-pointer"
                            >
                              <FileText className="w-3.5 h-3.5 text-primary" />
                              Note di rilascio complete
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                onSkipVersion(app.id);
                                setOpenMenuId(null);
                              }}
                              className="px-3.5 py-2 text-left text-xs text-on-surface hover:bg-surface-container-low cursor-pointer"
                            >
                              Salta versione {app.latestVersion}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                onExcludeApp(app.id);
                                setOpenMenuId(null);
                              }}
                              className="px-3.5 py-2 text-left text-xs text-error hover:bg-error-container/40 cursor-pointer"
                            >
                              Escludi dalla scansione
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* COLLAPSIBLE SECTION: ALREADY UPDATED APPS */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)]">
        <button
          type="button"
          onClick={() => setUpdatedAccordionOpen((prev) => !prev)}
          aria-expanded={updatedAccordionOpen}
          className="w-full flex items-center justify-between text-left group cursor-pointer"
        >
          <div className="flex items-center gap-3.5">
            <div className="w-9 h-9 rounded-lg bg-surface-container flex items-center justify-center text-tertiary shrink-0">
              <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="font-headline text-lg font-bold text-on-surface group-hover:text-primary transition-colors">
                Applicazioni Già Aggiornate ({upToDateApps.length})
              </h2>
              <p className="text-xs text-on-surface-variant">
                Tutti i pacchetti verificati corrispondono alle release ufficiali correnti
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-on-surface-variant font-medium hidden sm:inline">
              {updatedAccordionOpen ? 'Nascondi elenco' : 'Visualizza elenco'}
            </span>
            <ChevronDown
              className={`w-5 h-5 text-on-surface-variant transition-transform duration-200 ${
                updatedAccordionOpen ? 'rotate-180' : ''
              }`}
              aria-hidden="true"
            />
          </div>
        </button>

        {updatedAccordionOpen && (
          <div className="mt-5 pt-2 space-y-1.5">
            <div className="grid grid-cols-12 text-[11px] font-semibold text-on-surface-variant px-4 py-2 bg-surface-container-low rounded-lg">
              <div className="col-span-6 sm:col-span-5">Software</div>
              <div className="col-span-3 sm:col-span-3">Versione Corrente</div>
              <div className="hidden sm:block sm:col-span-2">Verificato</div>
              <div className="col-span-3 sm:col-span-2 text-right">Stato</div>
            </div>

            {upToDateApps.map((app) => (
              <div
                key={app.id}
                className="grid grid-cols-12 items-center text-xs px-4 py-3 hover:bg-surface-container-low/70 rounded-xl transition-colors"
              >
                <div className="col-span-6 sm:col-span-5 flex items-center gap-3 min-w-0">
                  <AppIcon icon={app.icon} className="w-4 h-4 text-secondary shrink-0" />
                  <span className="font-medium text-on-surface truncate">{app.name}</span>
                </div>
                <div className="col-span-3 sm:col-span-3 font-mono text-[11px] text-on-surface-variant tabular-nums">
                  v{app.installedVersion}
                </div>
                <div className="hidden sm:block sm:col-span-2 text-[11px] text-on-surface-variant">
                  {app.lastCheckedAt}
                </div>
                <div className="col-span-3 sm:col-span-2 text-right">
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-tertiary">
                    <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
                    Aggiornata
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* RELEASE NOTES DIALOG */}
      {releaseNotesApp && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="release-notes-title"
          className="fixed inset-0 z-50 bg-on-surface/30 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={() => setReleaseNotesApp(null)}
        >
          <div
            className="bg-surface-container-lowest rounded-2xl max-w-lg w-full p-6 shadow-[0_24px_48px_rgba(27,28,29,0.16)] space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-mono text-primary font-semibold">
                  {releaseNotesApp.wingetId} · SHA-256 {releaseNotesApp.sha256Prefix}
                </p>
                <h3
                  id="release-notes-title"
                  className="font-headline text-xl font-bold text-on-surface mt-1"
                >
                  {releaseNotesApp.name} v{releaseNotesApp.latestVersion}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setReleaseNotesApp(null)}
                aria-label="Chiudi note di rilascio"
                className="p-1.5 rounded-lg text-on-surface-variant hover:bg-surface-container cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-on-surface-variant leading-relaxed">
              {releaseNotesApp.releaseNotes}
            </p>

            <ul className="space-y-2 bg-surface-container-low rounded-xl p-4">
              {releaseNotesApp.fullChangelog.map((entry, idx) => (
                <li key={idx} className="text-xs text-on-surface flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" aria-hidden="true" />
                  <span>{entry}</span>
                </li>
              ))}
            </ul>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setReleaseNotesApp(null)}
                className="px-4 py-2 rounded-xl bg-surface-container-low hover:bg-surface-container text-xs font-medium text-on-surface cursor-pointer"
              >
                Chiudi
              </button>
              <button
                type="button"
                onClick={() => {
                  const id = releaseNotesApp.id;
                  setReleaseNotesApp(null);
                  onStartSingleUpdate(id);
                }}
                className="px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:bg-primary-container cursor-pointer"
              >
                Aggiorna Ora
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
