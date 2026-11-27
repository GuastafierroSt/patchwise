import test from 'node:test';
import assert from 'node:assert/strict';
import { INITIAL_APPS, INITIAL_SESSION_HISTORY } from './seedData';
import {
  AUTO_UPDATE_ALLOWED,
  appendSessionRecord,
  applyCompletedUpdate,
  compareVersions,
  computeDashboardMetrics,
  filterAllApps,
  filterPendingApps,
  hasPendingUpdate,
  rotateSessionOnRestart,
} from './updaterEngine';

test('auto update policy is permanently disabled', () => {
  assert.equal(AUTO_UPDATE_ALLOWED, false);
});

test('compareVersions accurately compares semantic and multi-segment versions', () => {
  assert.equal(compareVersions('123.0.6312.86', '124.0.6367.60'), -1);
  assert.equal(compareVersions('3.0.21', '3.0.21'), 0);
  assert.equal(compareVersions('24.05', '23.01'), 1);
  assert.equal(compareVersions('1.88.1', '1.89.0'), -1);
});

test('computeDashboardMetrics counts pending, critical, and up-to-date apps', () => {
  const metrics = computeDashboardMetrics(INITIAL_APPS);
  assert.equal(metrics.totalInstalled, INITIAL_APPS.length);
  assert.equal(metrics.pendingCount, 5);
  assert.equal(metrics.criticalCount, 2);
  assert.equal(metrics.zeroDayCount, 2);
  assert.equal(metrics.upToDateCount, INITIAL_APPS.length - 5);
});

test('filterPendingApps filters by category and search query', () => {
  const securityOnly = filterPendingApps(INITIAL_APPS, 'security', '');
  assert.equal(securityOnly.length, 2);
  assert.deepEqual(
    securityOnly.map((a) => a.id),
    ['google-chrome', 'vlc-media-player']
  );

  const searchVlc = filterPendingApps(INITIAL_APPS, 'all', 'vlc');
  assert.equal(searchVlc.length, 1);
  assert.equal(searchVlc[0].id, 'vlc-media-player');
});

test('applyCompletedUpdate transitions app to up-to-date and decreases pending count', () => {
  const updated = applyCompletedUpdate(INITIAL_APPS, '7zip-archiver', 'Oggi alle 11:02');
  const sevenZip = updated.find((a) => a.id === '7zip-archiver')!;
  assert.equal(sevenZip.installedVersion, '24.05');
  assert.equal(hasPendingUpdate(sevenZip), false);
  assert.equal(computeDashboardMetrics(updated).pendingCount, 4);
});

test('filterAllApps respects excluded flag', () => {
  const modified = INITIAL_APPS.map((a) =>
    a.id === 'spotify-desktop' ? { ...a, excluded: true } : a
  );
  assert.equal(filterAllApps(modified, 'excluded', '').length, 1);
  assert.equal(filterAllApps(modified, 'pending', '').length, 4);
});

test('stateless session history retains only the immediately preceding session on restart', () => {
  // Start with initial history (has 2 records from yesterday in lastSession)
  const withCurrent = appendSessionRecord(INITIAL_SESSION_HISTORY, {
    id: 'cur-1',
    appId: '7zip-archiver',
    appName: '7-Zip Archiver',
    publisher: 'Igor Pavlov',
    fromVersion: '23.01',
    toVersion: '24.05',
    sizeMb: 1.8,
    category: 'patch',
    status: 'success',
    completedAt: 'Oggi · 10:50',
    durationSeconds: 2.3,
    sourceProvider: 'Winget',
  });

  // First restart: currentSession becomes lastSession; yesterday's session is discarded
  const afterRestart1 = rotateSessionOnRestart(withCurrent, 'Oggi · 11:00');
  assert.equal(afterRestart1.currentSession.length, 0);
  assert.equal(afterRestart1.lastSession.length, 1);
  assert.equal(afterRestart1.lastSession[0].appId, '7zip-archiver');

  // Second restart with zero updates performed: lastSession clears completely
  const afterRestart2 = rotateSessionOnRestart(afterRestart1, 'Oggi · 11:15');
  assert.equal(afterRestart2.currentSession.length, 0);
  assert.equal(afterRestart2.lastSession.length, 0);
  assert.equal(afterRestart2.lastSessionStartedAt, null);
});
