export type SymbolKind =
  | 'heading'
  | 'pm-block'
  | 'function'
  | 'class'
  | 'variable'
  | 'interface'
  | 'method'
  | 'property';

export interface DocumentSymbol {
  /** Display name (heading text, function name, PM block type, etc.) */
  name: string;
  /** Kind of symbol for icon selection. */
  kind: SymbolKind;
  /** 1-based line number where the symbol starts. */
  line: number;
  /** Heading level (1-6) or 0 for flat symbols like functions. */
  level: number;
  /** Nested child symbols. */
  children: DocumentSymbol[];
}
