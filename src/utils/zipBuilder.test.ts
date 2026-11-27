import test from 'node:test';
import assert from 'node:assert/strict';
import { buildZipArchive, computeCrc32 } from './zipBuilder';

test('computeCrc32 matches standard IEEE 802.3 vector for "123456789"', () => {
  const bytes = new TextEncoder().encode('123456789');
  assert.equal(computeCrc32(bytes), 0xcbf43926);
});

test('buildZipArchive produces valid PKZIP local header and EOCD signatures', () => {
  const zip = buildZipArchive([
    { path: 'patchwise/main.py', content: 'print("PatchWise")\n' },
    { path: 'patchwise/README.md', content: '# PatchWise Portable\n' },
  ]);

  const view = new DataView(zip.buffer, zip.byteOffset, zip.byteLength);
  // First 4 bytes must be Local File Header signature PK\x03\x04
  assert.equal(view.getUint32(0, true), 0x04034b50);
  // Last 22 bytes must start with End of Central Directory signature PK\x05\x06
  const eocdOffset = zip.byteLength - 22;
  assert.equal(view.getUint32(eocdOffset, true), 0x06054b50);
  // Total entries count in EOCD must be 2
  assert.equal(view.getUint16(eocdOffset + 10, true), 2);
});
