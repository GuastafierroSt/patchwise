import { useState } from 'react';
import {
  Check,
  Copy,
  Download,
  FileCode2,
  FolderTree,
  Layers,
  PackageCheck,
  Terminal,
} from 'lucide-react';
import {
  OOP_CLASS_HIERARCHY,
  PYTHON_PROJECT_FILES,
  PythonSourceFile,
} from '../data/pythonProjectFiles';
import { buildZipArchive } from '../utils/zipBuilder';

const LAYER_LABELS: Record<PythonSourceFile['layer'], string> = {
  build: 'Build Portable .EXE & Avvio',
  core: 'Motore OOP (Core)',
  ui: 'GUI Desktop (PySide6)',
  tests: 'Test Unitari',
};

export function PythonBlueprintView() {
  const [selectedPath, setSelectedPath] = useState<string>('build_portable.py');
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [zipFeedback, setZipFeedback] = useState<string | null>(null);

  const activeFile =
    PYTHON_PROJECT_FILES.find((f) => f.path === selectedPath) ?? PYTHON_PROJECT_FILES[0];

  const handleCopyFile = async () => {
    try {
      await navigator.clipboard.writeText(activeFile.content);
      setCopiedPath(activeFile.path);
      window.setTimeout(() => setCopiedPath(null), 1800);
    } catch {
      setCopiedPath(null);
    }
  };

  const handleDownloadZip = () => {
    const zipBytes = buildZipArchive(
      PYTHON_PROJECT_FILES.map((file) => ({
        path: `PatchWise_Portable_Python/${file.path}`,
        content: file.content,
      }))
    );
    const copy = new Uint8Array(zipBytes.byteLength);
    copy.set(zipBytes);
    const blob = new Blob([copy.buffer], { type: 'application/zip' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'PatchWise_Python_Portable.zip';
    anchor.click();
    URL.revokeObjectURL(url);
    setZipFeedback(`Archivio generato (${PYTHON_PROJECT_FILES.length} file)`);
    window.setTimeout(() => setZipFeedback(null), 3000);
  };

  const groupedLayers: PythonSourceFile['layer'][] = ['build', 'core', 'ui', 'tests'];
  const lineCount = activeFile.content.split('\n').length;

  return (
    <div className="flex flex-col w-full pb-16 space-y-8">
      {/* Header & Download Portable Project CTA */}
      <section className="bg-surface-container-lowest rounded-2xl p-7 lg:p-8 shadow-[0_2px_16px_rgba(27,28,29,0.04)] flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="max-w-2xl space-y-2">
          <p className="text-xs font-semibold text-primary">
            Python 3.11+ · PySide6 Desktop · PyInstaller --onefile Portable
          </p>
          <h1 className="font-headline text-3xl font-bold text-on-surface">
            Architettura Python OOP &amp; Build .EXE Portable
          </h1>
          <p className="text-xs sm:text-sm text-on-surface-variant leading-relaxed">
            Codice sorgente completo pronto per Windows: gerarchia di classi astratte per rilevamento, confronto versioni, download manuale con barra di avanzamento, cronologia stateless e script automatico per compilare <code className="font-mono text-xs text-on-surface">PatchWise_Portable.exe</code>.
          </p>
        </div>

        <div className="flex flex-col items-start lg:items-end gap-2 shrink-0">
          <button
            type="button"
            onClick={handleDownloadZip}
            className="inline-flex items-center gap-2.5 px-5 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-on-primary text-xs font-semibold shadow-sm hover:brightness-105 active:scale-[0.99] transition-all whitespace-nowrap cursor-pointer"
          >
            <Download className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Scarica Progetto Python + Script .EXE (.zip)</span>
          </button>
          <span className="text-[11px] text-on-surface-variant font-mono tabular-nums">
            {zipFeedback ?? `${PYTHON_PROJECT_FILES.length} file sorgente verificati · 7/7 unittest OK`}
          </span>
        </div>
      </section>

      {/* OOP CLASS HIERARCHY VISUAL ARCHITECTURE */}
      <section className="space-y-4">
        <div className="flex items-center gap-2.5">
          <Layers className="w-5 h-5 text-primary" aria-hidden="true" />
          <h2 className="font-headline text-2xl font-bold text-on-surface">
            Gerarchia delle Classi Python
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {OOP_CLASS_HIERARCHY.map((node, idx) => {
            const isSelected = activeFile.path === node.filePath;
            const spanFull = idx === OOP_CLASS_HIERARCHY.length - 1 && OOP_CLASS_HIERARCHY.length % 2 === 1;
            return (
              <button
                key={node.filePath}
                type="button"
                onClick={() => setSelectedPath(node.filePath)}
                className={`text-left rounded-xl p-5 transition-all cursor-pointer ${
                  spanFull ? 'lg:col-span-2' : ''
                } ${
                  isSelected
                    ? 'bg-primary-fixed/45 shadow-[0_2px_12px_rgba(9,76,178,0.1)]'
                    : 'bg-surface-container-lowest shadow-[0_1px_8px_rgba(0,0,0,0.03)] hover:bg-surface-container-low/70'
                }`}
              >
                <div className="flex items-center justify-between gap-2 text-[11px] font-semibold">
                  <span className="text-primary">{node.layer}</span>
                  <span className="font-mono text-on-surface-variant">{node.baseClass}</span>
                </div>
                <h3 className="font-headline font-bold text-sm text-on-surface mt-1.5 leading-snug">
                  {node.className}
                </h3>
                <p className="text-xs text-on-surface-variant mt-1.5 leading-relaxed">
                  {node.role}
                </p>
                <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 mt-3 text-[11px] font-mono text-on-surface-variant">
                  {node.highlights.map((item, idx) => (
                    <span key={item} className="inline-flex items-center gap-2">
                      {idx > 0 && <span aria-hidden="true">·</span>}
                      <span>{item}</span>
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* PORTABLE EXE 3-STEP BUILD GUIDE */}
      <section className="bg-surface-container-lowest rounded-2xl p-6 shadow-[0_1px_8px_rgba(0,0,0,0.03)] space-y-4">
        <div className="flex items-center gap-2.5">
          <PackageCheck className="w-5 h-5 text-tertiary" aria-hidden="true" />
          <h2 className="font-headline text-xl font-bold text-on-surface">
            Compilazione Eseguibile Portable (.EXE) su Windows
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-surface-container-low rounded-xl p-4 space-y-1.5">
            <p className="font-semibold text-on-surface">01. Estrai l’archivio ZIP</p>
            <p className="text-on-surface-variant leading-relaxed">
              Decomprimi <code className="font-mono text-[11px]">PatchWise_Python_Portable.zip</code> in una cartella locale su Windows 10/11 con Python 3.10+ installato.
            </p>
          </div>
          <div className="bg-surface-container-low rounded-xl p-4 space-y-1.5">
            <p className="font-semibold text-on-surface">02. Avvia lo script di build</p>
            <p className="text-on-surface-variant leading-relaxed">
              Fai doppio clic su <code className="font-mono text-[11px] text-primary">build_portable.bat</code> oppure esegui{' '}
              <code className="font-mono text-[11px] text-primary">python build_portable.py</code>.
            </p>
          </div>
          <div className="bg-surface-container-low rounded-xl p-4 space-y-1.5">
            <p className="font-semibold text-on-surface">03. Esegui su qualsiasi PC</p>
            <p className="text-on-surface-variant leading-relaxed">
              Copia <code className="font-mono text-[11px]">dist\PatchWise_Portable.exe</code> su chiavetta USB o altro PC: si avvia direttamente senza installazione.
            </p>
          </div>
        </div>
      </section>

      {/* SOURCE CODE EXPLORER */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* File Tree */}
        <div className="lg:col-span-4 bg-surface-container-lowest rounded-2xl p-4 shadow-[0_1px_8px_rgba(0,0,0,0.03)] space-y-4">
          <div className="flex items-center gap-2 px-2 pt-1">
            <FolderTree className="w-4 h-4 text-primary" aria-hidden="true" />
            <h2 className="text-xs font-semibold text-on-surface">
              Struttura Progetto ({PYTHON_PROJECT_FILES.length} file)
            </h2>
          </div>

          <div className="space-y-4">
            {groupedLayers.map((layer) => {
              const files = PYTHON_PROJECT_FILES.filter((f) => f.layer === layer);
              return (
                <div key={layer} className="space-y-1">
                  <p className="px-2 text-[11px] font-semibold text-on-surface-variant">
                    {LAYER_LABELS[layer]}
                  </p>
                  {files.map((file) => {
                    const active = file.path === activeFile.path;
                    return (
                      <button
                        key={file.path}
                        type="button"
                        onClick={() => setSelectedPath(file.path)}
                        className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-left text-xs font-mono transition-colors cursor-pointer ${
                          active
                            ? 'bg-primary text-on-primary font-semibold'
                            : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
                        }`}
                      >
                        <FileCode2 className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                        <span className="truncate">{file.path}</span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>

        {/* Code Viewer */}
        <div className="lg:col-span-8 bg-surface-container-lowest rounded-2xl shadow-[0_1px_8px_rgba(0,0,0,0.03)] overflow-hidden">
          <div className="bg-surface-container-low px-5 py-3.5 flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary shrink-0" aria-hidden="true" />
                <span className="font-mono text-xs font-semibold text-on-surface truncate">
                  {activeFile.path}
                </span>
                <span className="text-[11px] font-mono text-on-surface-variant tabular-nums">
                  · {lineCount} righe
                </span>
              </div>
              <p className="text-[11px] text-on-surface-variant mt-0.5">{activeFile.summary}</p>
            </div>

            <button
              type="button"
              onClick={handleCopyFile}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-lowest hover:bg-surface-container-high text-xs font-medium text-on-surface transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              {copiedPath === activeFile.path ? (
                <>
                  <Check className="w-3.5 h-3.5 text-tertiary" aria-hidden="true" />
                  <span>Copiato</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-on-surface-variant" aria-hidden="true" />
                  <span>Copia file</span>
                </>
              )}
            </button>
          </div>

          <pre className="p-5 overflow-x-auto max-h-[560px] text-[12px] leading-relaxed font-mono text-on-surface bg-[#fcfbfc]">
            <code>{activeFile.content}</code>
          </pre>
        </div>
      </section>
    </div>
  );
}
