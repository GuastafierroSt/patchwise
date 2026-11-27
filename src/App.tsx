import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AllAppsView } from './components/AllAppsView';
import { DashboardView } from './components/DashboardView';
import { HistoryView } from './components/HistoryView';
import { PythonBlueprintView } from './components/PythonBlueprintView';
import { QueueView } from './components/QueueView';
import { Sidebar } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { INITIAL_APPS, INITIAL_SESSION_HISTORY } from './core/seedData';
import {
  ActiveDownloadState,
  DesktopApp,
  NavSection,
  SessionHistoryState,
} from './core/types';
import {
  appendSessionRecord,
  applyCompletedUpdate,
  computeDashboardMetrics,
  hasPendingUpdate,
  rotateSessionOnRestart,
} from './core/updaterEngine';

function formatCurrentTimeLabel(): string {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  return `Oggi · ${hh}:${mm}`;
}

export default function App() {
  const [activeSection, setActiveSection] = useState<NavSection>('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const [apps, setApps] = useState<DesktopApp[]>(INITIAL_APPS);
  const [lastScanAt, setLastScanAt] = useState<string>('Oggi alle 10:45');
  const [lastScanShort, setLastScanShort] = useState<string>('10:45 oggi');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStageMessage, setScanStageMessage] = useState('');
  const [compatibilityChecked, setCompatibilityChecked] = useState(false);

  const [activeDownload, setActiveDownload] = useState<ActiveDownloadState | null>(null);
  const [queuedIds, setQueuedIds] = useState<string[]>([]);
  const [lastCompletedName, setLastCompletedName] = useState<string | null>(null);
  const [history, setHistory] = useState<SessionHistoryState>(INITIAL_SESSION_HISTORY);

  const appsRef = useRef(apps);
  appsRef.current = apps;

  const metrics = useMemo(() => computeDashboardMetrics(apps), [apps]);

  const startDownloadForApp = useCallback((app: DesktopApp) => {
    const initialSpeed = Math.max(8.5, Math.min(24.5, 11.2 + (app.sizeMb % 9)));
    const initialEta = Math.max(2, Math.ceil(app.sizeMb / initialSpeed));
    setActiveDownload({
      appId: app.id,
      appName: app.name,
      publisher: app.publisher,
      fromVersion: app.installedVersion,
      toVersion: app.latestVersion,
      icon: app.icon,
      phase: 'downloading',
      percent: 4,
      downloadedMb: Math.round(app.sizeMb * 0.04 * 10) / 10,
      totalMb: app.sizeMb,
      speedMbps: initialSpeed,
      etaSeconds: initialEta,
      message: 'Connessione al repository ufficiale e ricezione pacchetto',
      startedAtMs: Date.now(),
    });
  }, []);

  // Automatically pull the next app from the manual queue when idle
  useEffect(() => {
    if (activeDownload !== null || queuedIds.length === 0) return;
    const [nextId, ...rest] = queuedIds;
    const nextApp = appsRef.current.find((a) => a.id === nextId && hasPendingUpdate(a));
    setQueuedIds(rest);
    if (nextApp) {
      startDownloadForApp(nextApp);
    }
  }, [activeDownload, queuedIds, startDownloadForApp]);

  // Live deterministic download -> SHA-256 verification -> silent install ticker
  useEffect(() => {
    if (!activeDownload || activeDownload.phase === 'paused') return;

    const timer = window.setInterval(() => {
      setActiveDownload((prev) => {
        if (!prev || prev.phase === 'paused') return prev;

        // Smooth multi-phase progression (~5-7s total) so users clearly observe download, SHA-256 check, and install
        const step =
          prev.percent >= 76
            ? 2.8
            : prev.totalMb > 200
              ? 2.6
              : prev.totalMb > 60
                ? 3.4
                : 5.0;
        const nextPercent = Math.min(100, Math.round((prev.percent + step) * 10) / 10);

        if (nextPercent >= 100) {
          const completedTimeLabel = formatCurrentTimeLabel();
          const durationSec = Math.max(1.2, (Date.now() - prev.startedAtMs) / 1000);
          const finishedApp = appsRef.current.find((a) => a.id === prev.appId);

          if (finishedApp) {
            setApps((curr) => applyCompletedUpdate(curr, prev.appId, completedTimeLabel));
            setHistory((currHist) =>
              appendSessionRecord(currHist, {
                id: `${prev.appId}-${Date.now()}`,
                appId: prev.appId,
                appName: prev.appName,
                publisher: prev.publisher,
                fromVersion: prev.fromVersion,
                toVersion: prev.toVersion,
                sizeMb: prev.totalMb,
                category: finishedApp.category,
                status: 'success',
                completedAt: completedTimeLabel,
                durationSeconds: Math.round(durationSec * 10) / 10,
                sourceProvider: finishedApp.source,
              })
            );
            setLastCompletedName(`${prev.appName} v${prev.toVersion}`);
          }
          return null;
        }

        if (nextPercent >= 88) {
          return {
            ...prev,
            phase: 'installing',
            percent: nextPercent,
            downloadedMb: prev.totalMb,
            etaSeconds: 1,
            message: 'Installazione silenziosa del pacchetto aggiornato',
          };
        }

        if (nextPercent >= 76) {
          return {
            ...prev,
            phase: 'verifying',
            percent: nextPercent,
            downloadedMb: prev.totalMb,
            etaSeconds: 2,
            message: 'Verifica integrità firma digitale e checksum SHA-256',
          };
        }

        const dlRatio = Math.min(1, nextPercent / 76);
        const downloadedMb = Math.round(prev.totalMb * dlRatio * 10) / 10;
        const remainingMb = Math.max(0, prev.totalMb - downloadedMb);
        const speed = Math.max(6.4, prev.speedMbps + ((Math.floor(nextPercent) % 3) - 1) * 0.4);
        const etaSeconds = Math.max(1, Math.ceil(remainingMb / speed));

        return {
          ...prev,
          phase: 'downloading',
          percent: nextPercent,
          downloadedMb,
          speedMbps: Math.round(speed * 10) / 10,
          etaSeconds,
          message: 'Ricezione pacchetto dal repository ufficiale',
        };
      });
    }, 180);

    return () => window.clearInterval(timer);
  }, [activeDownload?.appId, activeDownload?.phase]);

  const handleTriggerScan = () => {
    if (isScanning) return;
    setIsScanning(true);
    setScanStageMessage('Fase 1/3 · Lettura rami Uninstall nel Registro di Windows...');

    window.setTimeout(() => {
      setScanStageMessage('Fase 2/3 · Interrogazione catalogo locale Winget...');
    }, 450);

    window.setTimeout(() => {
      setScanStageMessage('Fase 3/3 · Confronto versioni online (Winget & GitHub Releases)...');
    }, 950);

    window.setTimeout(() => {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      setLastScanAt(`Oggi alle ${hh}:${mm}`);
      setLastScanShort(`${hh}:${mm} oggi`);
      setIsScanning(false);
      setScanStageMessage('');
    }, 1450);
  };

  const handleVerifyCompatibility = () => {
    setApps((prev) =>
      prev.map((app) =>
        hasPendingUpdate(app) ? { ...app, compatibilityVerified: true } : app
      )
    );
    setCompatibilityChecked(true);
  };

  const handleToggleSelect = (appId: string) => {
    setApps((prev) =>
      prev.map((app) => (app.id === appId ? { ...app, selected: !app.selected } : app))
    );
  };

  const handleToggleSelectAll = () => {
    const pending = apps.filter(hasPendingUpdate);
    const allSelected = pending.length > 0 && pending.every((a) => a.selected);
    setApps((prev) =>
      prev.map((app) =>
        hasPendingUpdate(app) ? { ...app, selected: !allSelected } : app
      )
    );
  };

  const handleStartSingleUpdate = (appId: string) => {
    const target = apps.find((a) => a.id === appId && hasPendingUpdate(a));
    if (!target) return;
    if (activeDownload?.appId === appId || queuedIds.includes(appId)) return;

    if (!activeDownload) {
      startDownloadForApp(target);
    } else {
      setQueuedIds((prev) => [...prev, appId]);
    }
  };

  const handleStartSelectedUpdates = () => {
    const selected = apps.filter((a) => hasPendingUpdate(a) && a.selected);
    if (selected.length === 0) return;

    const toQueue = selected
      .map((a) => a.id)
      .filter((id) => id !== activeDownload?.appId && !queuedIds.includes(id));

    if (toQueue.length === 0) return;

    if (!activeDownload) {
      const [firstId, ...rest] = toQueue;
      const firstApp = apps.find((a) => a.id === firstId);
      if (firstApp) {
        startDownloadForApp(firstApp);
      }
      if (rest.length > 0) {
        setQueuedIds((prev) => [...prev, ...rest]);
      }
    } else {
      setQueuedIds((prev) => [...prev, ...toQueue]);
    }
  };

  const handleTogglePause = () => {
    setActiveDownload((prev) => {
      if (!prev) return null;
      if (prev.phase === 'downloading') {
        return { ...prev, phase: 'paused', message: 'Download sospeso manualmente dall’utente' };
      }
      if (prev.phase === 'paused') {
        return { ...prev, phase: 'downloading', message: 'Ripresa ricezione pacchetto...' };
      }
      return prev;
    });
  };

  const handleCancelDownload = () => {
    if (!activeDownload) return;
    const cancelled = activeDownload;
    const appObj = apps.find((a) => a.id === cancelled.appId);
    const durationSec = Math.max(0.5, (Date.now() - cancelled.startedAtMs) / 1000);
    setActiveDownload(null);

    setHistory((curr) =>
      appendSessionRecord(curr, {
        id: `${cancelled.appId}-cancel-${Date.now()}`,
        appId: cancelled.appId,
        appName: cancelled.appName,
        publisher: cancelled.publisher,
        fromVersion: cancelled.fromVersion,
        toVersion: cancelled.toVersion,
        sizeMb: cancelled.totalMb,
        category: appObj?.category ?? 'patch',
        status: 'cancelled',
        completedAt: formatCurrentTimeLabel(),
        durationSeconds: Math.round(durationSec * 10) / 10,
        sourceProvider: appObj?.source ?? 'Winget',
      })
    );
  };

  const handleSkipVersion = (appId: string) => {
    setApps((prev) =>
      prev.map((app) =>
        app.id === appId ? { ...app, skippedVersion: app.latestVersion, selected: false } : app
      )
    );
  };

  const handleToggleExclude = (appId: string) => {
    setApps((prev) =>
      prev.map((app) =>
        app.id === appId
          ? { ...app, excluded: !app.excluded, selected: false }
          : app
      )
    );
    setQueuedIds((prev) => prev.filter((id) => id !== appId));
  };

  const handleRemoveFromQueue = (appId: string) => {
    setQueuedIds((prev) => prev.filter((id) => id !== appId));
  };

  const handleClearQueue = () => {
    setQueuedIds([]);
  };

  const handleSimulateAppRestart = () => {
    setActiveDownload(null);
    setQueuedIds([]);
    setLastCompletedName(null);
    setHistory((curr) => rotateSessionOnRestart(curr, formatCurrentTimeLabel()));
  };

  const handleClearHistory = () => {
    setHistory({
      currentSessionStartedAt: formatCurrentTimeLabel(),
      currentSession: [],
      lastSessionStartedAt: null,
      lastSession: [],
    });
  };

  const queuedApps = useMemo(
    () =>
      queuedIds
        .map((id) => apps.find((a) => a.id === id))
        .filter((a): a is DesktopApp => Boolean(a)),
    [apps, queuedIds]
  );

  const activeQueueBadgeCount = queuedIds.length + (activeDownload ? 1 : 0);

  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <TopHeader
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        isScanning={isScanning}
        onTriggerScan={handleTriggerScan}
        onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)}
        mobileMenuOpen={mobileMenuOpen}
      />

      <Sidebar
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        pendingCount={metrics.pendingCount}
        queueCount={activeQueueBadgeCount}
        sessionHistoryCount={history.currentSession.length}
        lastScanTime={lastScanShort}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <div className="lg:pl-72">
        <main className="w-full pt-22 px-4 sm:px-6 lg:px-8 max-w-[1260px] mx-auto min-h-screen">
          {activeSection === 'dashboard' && (
            <DashboardView
              apps={apps}
              metrics={metrics}
              searchQuery={searchQuery}
              lastScanAt={lastScanAt}
              isScanning={isScanning}
              scanStageMessage={scanStageMessage}
              compatibilityChecked={compatibilityChecked}
              activeDownload={activeDownload}
              queuedIds={queuedIds}
              lastCompletedName={lastCompletedName}
              onTriggerScan={handleTriggerScan}
              onVerifyCompatibility={handleVerifyCompatibility}
              onToggleSelect={handleToggleSelect}
              onToggleSelectAll={handleToggleSelectAll}
              onStartSingleUpdate={handleStartSingleUpdate}
              onStartSelectedUpdates={handleStartSelectedUpdates}
              onTogglePause={handleTogglePause}
              onCancelDownload={handleCancelDownload}
              onSkipVersion={handleSkipVersion}
              onExcludeApp={handleToggleExclude}
              onOpenQueue={() => setActiveSection('queue')}
            />
          )}

          {activeSection === 'all-apps' && (
            <AllAppsView
              apps={apps}
              searchQuery={searchQuery}
              activeDownload={activeDownload}
              queuedIds={queuedIds}
              onStartSingleUpdate={handleStartSingleUpdate}
              onToggleExclude={handleToggleExclude}
            />
          )}

          {activeSection === 'history' && (
            <HistoryView
              history={history}
              onSimulateAppRestart={handleSimulateAppRestart}
              onClearHistory={handleClearHistory}
            />
          )}

          {activeSection === 'queue' && (
            <QueueView
              activeDownload={activeDownload}
              queuedApps={queuedApps}
              completedInSession={history.currentSession}
              onTogglePause={handleTogglePause}
              onCancelDownload={handleCancelDownload}
              onRemoveFromQueue={handleRemoveFromQueue}
              onClearQueue={handleClearQueue}
            />
          )}

          {activeSection === 'python-export' && <PythonBlueprintView />}
        </main>
      </div>
    </div>
  );
}
