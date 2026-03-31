/**
 * Monaco Editor loader configuration.
 *
 * Configures @monaco-editor/react to use the locally bundled monaco-editor package
 * instead of loading from CDN (cdn.jsdelivr.net). This avoids:
 * - CSP connect-src / script-src violations in Next.js
 * - Network latency on first editor render
 * - Offline / air-gapped environment failures
 *
 * IMPORTANT: This module must be imported (as a side-effect) before the first
 * <Editor /> render. Import it at the top of MonacoFileEditor.tsx.
 */

import { loader } from '@monaco-editor/react';
import * as monaco from 'monaco-editor';

// Tell @monaco-editor/react to use the local bundled monaco-editor package
// instead of downloading from CDN.
loader.config({ monaco });
