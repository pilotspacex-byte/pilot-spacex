import type * as monaco from 'monaco-editor';

/**
 * Monaco theme constants — use these when setting the `theme` prop on <Editor />.
 */
export const PILOT_SPACE_LIGHT = 'pilot-space-light';
export const PILOT_SPACE_DARK = 'pilot-space-dark';

/**
 * Warm Pilot Space syntax palette (from CONTEXT.md design spec):
 *
 * Keywords : #8B7EC8  — soft violet
 * Strings  : #29A386  — teal (matches --primary)
 * Comments : #9C9590  — warm gray, italic
 * Functions: #5B8FC9  — cool blue
 * Numbers  : #D9853F  — warm amber/orange
 * Types    : #6B8FAD  — muted steel blue
 *
 * Backgrounds:
 *   Light: #FAF9F7  — warm parchment
 *   Dark : #1A1A1E  — near-black with warm undertone
 *
 * Cursor: #29A386 (teal — var(--primary) equivalent)
 * Font  : JetBrains Mono, 13px, line-height 20px
 */

/**
 * Registers both Pilot Space Monaco themes (light and dark).
 * Call once from a `beforeMount` callback in MonacoFileEditor.
 *
 * @param monacoInstance - The monaco namespace (from @monaco-editor/react `beforeMount`)
 */
export function definePilotSpaceThemes(monacoInstance: typeof monaco): void {
  // ─── Light Theme ──────────────────────────────────────────────────────────
  monacoInstance.editor.defineTheme(PILOT_SPACE_LIGHT, {
    base: 'vs',
    inherit: true,
    rules: [
      // Core language tokens
      { token: 'keyword', foreground: '8B7EC8' },
      { token: 'keyword.operator', foreground: '8B7EC8' },
      { token: 'keyword.control', foreground: '8B7EC8' },

      { token: 'string', foreground: '29A386' },
      { token: 'string.escape', foreground: '29A386' },
      { token: 'string.template', foreground: '29A386' },

      { token: 'comment', foreground: '9C9590', fontStyle: 'italic' },
      { token: 'comment.line', foreground: '9C9590', fontStyle: 'italic' },
      { token: 'comment.block', foreground: '9C9590', fontStyle: 'italic' },

      { token: 'number', foreground: 'D9853F' },
      { token: 'number.float', foreground: 'D9853F' },
      { token: 'number.hex', foreground: 'D9853F' },

      { token: 'type', foreground: '6B8FAD' },
      { token: 'type.identifier', foreground: '6B8FAD' },
      { token: 'entity.name.type', foreground: '6B8FAD' },

      { token: 'entity.name.function', foreground: '5B8FC9' },
      { token: 'support.function', foreground: '5B8FC9' },

      // Markup (Markdown, HTML)
      { token: 'heading', foreground: '37352F', fontStyle: 'bold' },
      { token: 'emphasis', fontStyle: 'italic' },
      { token: 'strong', fontStyle: 'bold' },
      { token: 'tag', foreground: '8B7EC8' },
      { token: 'attribute.name', foreground: '5B8FC9' },
      { token: 'attribute.value', foreground: '29A386' },

      // Operators and punctuation
      { token: 'operator', foreground: '8B7EC8' },
      { token: 'delimiter', foreground: '6B6B6B' },
    ],
    colors: {
      // Editor chrome
      'editor.background': '#FAF9F7',
      'editor.foreground': '#37352F',
      'editor.lineHighlightBackground': '#F2F0EC',
      'editor.selectionBackground': '#D4ECE5',
      'editor.selectionHighlightBackground': '#E8F5F0',
      'editor.inactiveSelectionBackground': '#E8F0EC',

      // Cursor
      'editorCursor.foreground': '#29A386',

      // Line numbers
      'editorLineNumber.foreground': '#B8B0A8',
      'editorLineNumber.activeForeground': '#6B6460',

      // Ghost text (completions preview)
      'editorGhostText.foreground': '#B8B0A8',

      // Widgets (suggestions, hover)
      'editorWidget.background': '#FFFFFF',
      'editorWidget.border': '#E9E9E7',
      'editorSuggestWidget.background': '#FFFFFF',
      'editorSuggestWidget.border': '#E9E9E7',
      'editorSuggestWidget.selectedBackground': '#F0F7F4',
      'editorSuggestWidget.highlightForeground': '#29A386',

      // Hover / info card
      'editorHoverWidget.background': '#FFFFFF',
      'editorHoverWidget.border': '#E9E9E7',

      // Diagnostics
      'editorError.foreground': '#E5534B',
      'editorWarning.foreground': '#D9853F',
      'editorInfo.foreground': '#5B8FC9',
      'editorHint.foreground': '#9C9590',
      'editorError.border': '#FECACA',
      'editorWarning.border': '#FDE68A',

      // Scrollbar
      'scrollbarSlider.background': '#D4CDC5',
      'scrollbarSlider.hoverBackground': '#BCB5AD',
      'scrollbarSlider.activeBackground': '#A8A098',

      // Gutter / minimap
      'editorGutter.background': '#FAF9F7',
      'minimap.background': '#F5F3EF',

      // Indent guides
      'editorIndentGuide.background1': '#EEECE8',
      'editorIndentGuide.activeBackground1': '#CCCAC4',

      // Bracket match
      'editorBracketMatch.background': '#D4ECE5',
      'editorBracketMatch.border': '#29A386',

      // Find match highlights
      'editor.findMatchBackground': '#AADAC7',
      'editor.findMatchHighlightBackground': '#D4EBE3',
    },
  });

  // ─── Dark Theme ───────────────────────────────────────────────────────────
  monacoInstance.editor.defineTheme(PILOT_SPACE_DARK, {
    base: 'vs-dark',
    inherit: true,
    rules: [
      // Core language tokens — slightly adjusted for dark background readability
      { token: 'keyword', foreground: 'A594D8' },
      { token: 'keyword.operator', foreground: 'A594D8' },
      { token: 'keyword.control', foreground: 'A594D8' },

      { token: 'string', foreground: '3DB896' },
      { token: 'string.escape', foreground: '3DB896' },
      { token: 'string.template', foreground: '3DB896' },

      { token: 'comment', foreground: '6B6360', fontStyle: 'italic' },
      { token: 'comment.line', foreground: '6B6360', fontStyle: 'italic' },
      { token: 'comment.block', foreground: '6B6360', fontStyle: 'italic' },

      { token: 'number', foreground: 'E89B52' },
      { token: 'number.float', foreground: 'E89B52' },
      { token: 'number.hex', foreground: 'E89B52' },

      { token: 'type', foreground: '7DA3C1' },
      { token: 'type.identifier', foreground: '7DA3C1' },
      { token: 'entity.name.type', foreground: '7DA3C1' },

      { token: 'entity.name.function', foreground: '74A8D8' },
      { token: 'support.function', foreground: '74A8D8' },

      // Markup
      { token: 'heading', foreground: 'EBEBEB', fontStyle: 'bold' },
      { token: 'emphasis', fontStyle: 'italic' },
      { token: 'strong', fontStyle: 'bold' },
      { token: 'tag', foreground: 'A594D8' },
      { token: 'attribute.name', foreground: '74A8D8' },
      { token: 'attribute.value', foreground: '3DB896' },

      // Operators
      { token: 'operator', foreground: 'A594D8' },
      { token: 'delimiter', foreground: '8A8480' },
    ],
    colors: {
      // Editor chrome
      'editor.background': '#1A1A1E',
      'editor.foreground': '#EBEBEB',
      'editor.lineHighlightBackground': '#222228',
      'editor.selectionBackground': '#1F3D35',
      'editor.selectionHighlightBackground': '#193028',
      'editor.inactiveSelectionBackground': '#1A2E28',

      // Cursor
      'editorCursor.foreground': '#29A386',

      // Line numbers
      'editorLineNumber.foreground': '#4A4845',
      'editorLineNumber.activeForeground': '#8A8480',

      // Ghost text
      'editorGhostText.foreground': '#4A4845',

      // Widgets
      'editorWidget.background': '#222228',
      'editorWidget.border': '#333338',
      'editorSuggestWidget.background': '#222228',
      'editorSuggestWidget.border': '#333338',
      'editorSuggestWidget.selectedBackground': '#1F3D35',
      'editorSuggestWidget.highlightForeground': '#3DB896',

      // Hover
      'editorHoverWidget.background': '#222228',
      'editorHoverWidget.border': '#333338',

      // Diagnostics
      'editorError.foreground': '#F87171',
      'editorWarning.foreground': '#E89B52',
      'editorInfo.foreground': '#74A8D8',
      'editorHint.foreground': '#6B6360',

      // Scrollbar
      'scrollbarSlider.background': '#3A3838',
      'scrollbarSlider.hoverBackground': '#504E4C',
      'scrollbarSlider.activeBackground': '#606060',

      // Gutter / minimap
      'editorGutter.background': '#1A1A1E',
      'minimap.background': '#18181C',

      // Indent guides
      'editorIndentGuide.background1': '#2A2A2E',
      'editorIndentGuide.activeBackground1': '#444448',

      // Bracket match
      'editorBracketMatch.background': '#1F3D35',
      'editorBracketMatch.border': '#29A386',

      // Find match
      'editor.findMatchBackground': '#1F4D3F',
      'editor.findMatchHighlightBackground': '#193830',
    },
  });
}
