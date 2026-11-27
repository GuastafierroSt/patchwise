import {
  DashboardMetrics,
  DesktopApp,
  SessionHistoryState,
  SessionUpdateRecord,
  UpdateCategory,
} from './types';

export const AUTO_UPDATE_ALLOWED = false as const;

export function parseVersionSegments(raw: string): number[] {
  const matches = (raw || '').match(/\d+/g);
  if (!matches || matches.length === 0) {
    return [0];
  }
  return matches.map((part) => Number.parseInt(part, 10));
}

export function compareVersions(current: string, candidate: string): -1 | 0 | 1 {
  const a = parseVersionSegments(current);
  const b = parseVersionSegments(candidate);
  const maxLen = Math.max(a.length, b.length);
  for (let i = 0; i < maxLen; i += 1) {
    const va = a[i] ?? 0;
    const vb = b[i] ?? 0;
    if (va < vb) return -1;
    if (va > vb) return 1;
  }
  return 0;
}

export function hasPendingUpdate(app: DesktopApp): boolean {
  if (app.excluded) return false;
  if (app.skippedVersion && app.skippedVersion === app.latestVersion) return false;
  return compareVersions(app.installedVersion, app.latestVersion) < 0;
}

export function filterPendingApps(
  apps: DesktopApp[],
  category: 'all' | UpdateCategory,
  searchQuery: string
): DesktopApp[] {
  const q = searchQuery.trim().toLowerCase();
  return apps.filter((app) => {
    if (!hasPendingUpdate(app)) return false;
    if (category !== 'all' && app.category !== category) return false;
    if (!q) return true;
    return (
      app.name.toLowerCase().includes(q) ||
      app.publisher.toLowerCase().includes(q) ||
      app.wingetId.toLowerCase().includes(q) ||
      app.releaseNotes.toLowerCase().includes(q)
    );
  });
}

export function filterAllApps(
  apps: DesktopApp[],
  statusFilter: 'all' | 'pending' | 'up-to-date' | 'excluded',
  searchQuery: string
): DesktopApp[] {
  const q = searchQuery.trim().toLowerCase();
  return apps.filter((app) => {
    const pending = hasPendingUpdate(app);
    if (statusFilter === 'pending' && !pending) return false;
    if (statusFilter === 'up-to-date' && (pending || app.excluded)) return false;
    if (statusFilter === 'excluded' && !app.excluded) return false;
    if (!q) return true;
    return (
      app.name.toLowerCase().includes(q) ||
      app.publisher.toLowerCase().includes(q) ||
      app.wingetId.toLowerCase().includes(q)
    );
  });
}

export function computeDashboardMetrics(apps: DesktopApp[]): DashboardMetrics {
  const pending = apps.filter(hasPendingUpdate);
  const criticalCount = pending.filter((a) => a.category === 'security').length;
  const zeroDayCount = pending.filter((a) => Boolean(a.cveId)).length;
  const totalDownloadMb = Math.round(
    pending.reduce((sum, app) => sum + app.sizeMb, 0) * 10
  ) / 10;
  const estimatedCleanupMb = Math.round(totalDownloadMb * 0.62);

  return {
    totalInstalled: apps.length,
    pendingCount: pending.length,
    criticalCount,
    upToDateCount: apps.filter((a) => !hasPendingUpdate(a) && !a.excluded).length,
    totalDownloadMb,
    estimatedCleanupMb,
    zeroDayCount,
  };
}

export function applyCompletedUpdate(
  apps: DesktopApp[],
  appId: string,
  timestampLabel: string
): DesktopApp[] {
  return apps.map((app) =>
    app.id === appId
      ? {
          ...app,
          installedVersion: app.latestVersion,
          selected: false,
          lastCheckedAt: timestampLabel,
        }
      : app
  );
}

/**
 * Stateless session lifecycle transition:
 * - Current session records become the ONLY "last session" snapshot on restart.
 * - Any session older than the immediately closed one is permanently discarded.
 * - If the closing session had zero updates, the old snapshot is cleared as well.
 */
export function rotateSessionOnRestart(
  history: SessionHistoryState,
  newSessionLabel: string
): SessionHistoryState {
  const hasCurrentUpdates = history.currentSession.length > 0;
  return {
    currentSessionStartedAt: newSessionLabel,
    currentSession: [],
    lastSessionStartedAt: hasCurrentUpdates ? history.currentSessionStartedAt : null,
    lastSession: hasCurrentUpdates ? [...history.currentSession] : [],
  };
}

export function appendSessionRecord(
  history: SessionHistoryState,
  record: SessionUpdateRecord
): SessionHistoryState {
  return {
    ...history,
    currentSession: [record, ...history.currentSession],
  };
}

export function formatMegabytes(mb: number): string {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  if (mb < 10) {
    return `${mb.toFixed(1)} MB`;
  }
  return `${Math.round(mb)} MB`;
}
