import type * as monacoNs from 'monaco-editor';

/**
 * A normalized diagnostic entry derived from Monaco marker data.
 * Language-agnostic — works with TypeScript, JavaScript, JSON, CSS, etc.
 */
export interface Diagnostic {
  severity: 'error' | 'warning' | 'info' | 'hint';
  message: string;
  source: string;
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
  /** URI string of the model this diagnostic belongs to */
  modelUri: string;
  /** Display-friendly file name extracted from model URI */
  fileName: string;
}

/** Aggregate counts of diagnostics by severity level. */
export interface DiagnosticCounts {
  errors: number;
  warnings: number;
  infos: number;
}

/**
 * Maps Monaco MarkerSeverity enum to a string severity level.
 *
 * Monaco MarkerSeverity values:
 *   Hint = 1, Info = 2, Warning = 4, Error = 8
 */
export function severityToString(severity: monacoNs.MarkerSeverity): Diagnostic['severity'] {
  switch (severity) {
    case 8:
      return 'error';
    case 4:
      return 'warning';
    case 2:
      return 'info';
    default:
      return 'hint';
  }
}

/**
 * Subscribes to Monaco's `onDidChangeMarkers` event and transforms raw markers
 * into normalized `Diagnostic[]` on every change.
 *
 * Uses event-driven updates (not polling) for optimal performance.
 *
 * @returns An `IDisposable` — call `.dispose()` to unsubscribe.
 */
export function subscribeToDiagnostics(
  monaco: typeof monacoNs,
  onUpdate: (diagnostics: Diagnostic[]) => void
): monacoNs.IDisposable {
  return monaco.editor.onDidChangeMarkers(() => {
    const markers = monaco.editor.getModelMarkers({});
    const diagnostics: Diagnostic[] = markers.map((marker) => {
      const uri = marker.resource.toString();
      // Extract file name from URI path (last segment)
      const segments = marker.resource.path.split('/');
      const fileName = segments[segments.length - 1] || uri;

      return {
        severity: severityToString(marker.severity),
        message: marker.message,
        source: marker.source ?? '',
        startLineNumber: marker.startLineNumber,
        startColumn: marker.startColumn,
        endLineNumber: marker.endLineNumber,
        endColumn: marker.endColumn,
        modelUri: uri,
        fileName,
      };
    });

    onUpdate(diagnostics);
  });
}

/** Counts diagnostics by severity level. */
export function countDiagnostics(diagnostics: Diagnostic[]): DiagnosticCounts {
  let errors = 0;
  let warnings = 0;
  let infos = 0;

  for (const d of diagnostics) {
    switch (d.severity) {
      case 'error':
        errors++;
        break;
      case 'warning':
        warnings++;
        break;
      case 'info':
        infos++;
        break;
      // hints are not counted
    }
  }

  return { errors, warnings, infos };
}
