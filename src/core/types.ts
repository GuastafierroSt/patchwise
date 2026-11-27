export type UpdateCategory = 'security' | 'features' | 'patch';

export type UpdatePhase =
  | 'idle'
  | 'queued'
  | 'downloading'
  | 'verifying'
  | 'installing'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type NavSection =
  | 'dashboard'
  | 'all-apps'
  | 'history'
  | 'queue'
  | 'python-export';

export type AppIconKey =
  | 'browser'
  | 'code'
  | 'music'
  | 'video'
  | 'archive'
  | 'shield'
  | 'chat'
  | 'audio'
  | 'git'
  | 'terminal'
  | 'notes'
  | 'image'
  | 'tools';

export interface DesktopApp {
  id: string;
  name: string;
  publisher: string;
  installedVersion: string;
  latestVersion: string;
  sizeMb: number;
  category: UpdateCategory;
  source: 'Winget + Registro' | 'Registro Windows' | 'Winget';
  wingetId: string;
  installPath: string;
  icon: AppIconKey;
  releaseNotes: string;
  fullChangelog: string[];
  cveId?: string;
  sha256Prefix: string;
  lastCheckedAt: string;
  selected: boolean;
  excluded: boolean;
  skippedVersion?: string;
  compatibilityVerified?: boolean;
}

export interface ActiveDownloadState {
  appId: string;
  appName: string;
  publisher: string;
  fromVersion: string;
  toVersion: string;
  icon: AppIconKey;
  phase: UpdatePhase;
  percent: number;
  downloadedMb: number;
  totalMb: number;
  speedMbps: number;
  etaSeconds: number;
  message: string;
  startedAtMs: number;
}

export interface SessionUpdateRecord {
  id: string;
  appId: string;
  appName: string;
  publisher: string;
  fromVersion: string;
  toVersion: string;
  sizeMb: number;
  category: UpdateCategory;
  status: 'success' | 'cancelled' | 'failed';
  completedAt: string;
  durationSeconds: number;
  sourceProvider: string;
}

export interface SessionHistoryState {
  currentSessionStartedAt: string;
  currentSession: SessionUpdateRecord[];
  lastSessionStartedAt: string | null;
  lastSession: SessionUpdateRecord[];
}

export interface DashboardMetrics {
  totalInstalled: number;
  pendingCount: number;
  criticalCount: number;
  upToDateCount: number;
  totalDownloadMb: number;
  estimatedCleanupMb: number;
  zeroDayCount: number;
}
