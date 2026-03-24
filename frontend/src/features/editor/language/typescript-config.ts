import type * as monacoNs from 'monaco-editor';

/**
 * Configures Monaco's built-in TypeScript and JavaScript language services.
 *
 * Sets strict compiler options for TypeScript IntelliSense (autocomplete, hover info,
 * go-to-definition) and enables full syntax + semantic validation for both TS and JS.
 *
 * IMPORTANT: This function ONLY touches typescriptDefaults and javascriptDefaults.
 * JSON, CSS, and HTML language services use Monaco's built-in defaults and must NOT
 * be modified here (LSP-03 non-regression).
 *
 * Must be called BEFORE any editor models are created (Pitfall 1: TS defaults are
 * global singletons that apply to all models).
 *
 * NOTE: Monaco 0.55+ moved TS language service to `monaco.typescript` namespace
 * (top-level). `monaco.languages.typescript` is deprecated.
 */
export function configureTypeScriptDefaults(monaco: typeof monacoNs): void {
  const tsDefaults = monaco.typescript.typescriptDefaults;
  const jsDefaults = monaco.typescript.javascriptDefaults;

  // TypeScript compiler options
  tsDefaults.setCompilerOptions({
    target: monaco.typescript.ScriptTarget.ESNext,
    module: monaco.typescript.ModuleKind.ESNext,
    moduleResolution: monaco.typescript.ModuleResolutionKind.NodeJs,
    jsx: monaco.typescript.JsxEmit.ReactJSX,
    allowJs: true,
    checkJs: false,
    strict: true,
    noEmit: true,
    esModuleInterop: true,
    allowNonTsExtensions: true,
    lib: ['esnext', 'dom', 'dom.iterable'],
  });

  // TypeScript diagnostics options — enable all validation
  tsDefaults.setDiagnosticsOptions({
    noSemanticValidation: false,
    noSyntaxValidation: false,
    noSuggestionDiagnostics: false,
  });

  // JavaScript diagnostics options — enable syntax and semantic validation
  jsDefaults.setDiagnosticsOptions({
    noSemanticValidation: false,
    noSyntaxValidation: false,
  });
}
