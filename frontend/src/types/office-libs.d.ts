/**
 * Type declarations for Office document rendering libraries.
 *
 * These libraries lack @types/* packages. Minimal declarations are provided
 * to satisfy TypeScript without constraining runtime behavior.
 */

declare module 'docx-preview' {
  export interface DocxOptions {
    inWrapper?: boolean;
    ignoreLastRenderedPageBreak?: boolean;
  }
  export function renderAsync(
    data: ArrayBuffer | Blob,
    container: HTMLElement,
    styleContainer?: HTMLElement,
    options?: DocxOptions
  ): Promise<void>;
}

declare module 'mammoth' {
  interface ConvertResult {
    value: string;
    messages: unknown[];
  }

  interface ImageElement {
    read(encoding: 'base64'): Promise<string>;
    contentType: string;
  }

  interface ImageConverter {
    (image: ImageElement): Promise<{ src: string }>;
  }

  interface ConvertOptions {
    convertImage?: ReturnType<typeof images.imgElement>;
  }

  export function convertToHtml(
    input: { arrayBuffer: ArrayBuffer },
    options?: ConvertOptions
  ): Promise<ConvertResult>;

  export const images: {
    imgElement(handler: ImageConverter): ImageConverter;
  };
}

declare module 'pptxviewjs' {
  export class PPTXViewer {
    constructor(options: { canvas: HTMLCanvasElement | null });
    loadFile(data: ArrayBuffer): Promise<void>;
    getSlideCount(): number;
    renderSlide(index: number, canvas?: HTMLCanvasElement): Promise<void>;
    destroy(): void;
  }
}

declare module 'xlsx' {
  export interface CellAddress {
    c: number;
    r: number;
  }

  export interface Range {
    s: CellAddress;
    e: CellAddress;
  }

  export interface WorkBook {
    SheetNames: string[];
    Sheets: Record<string, WorkSheet>;
  }

  export interface WorkSheet {
    [key: string]: unknown;
    '!ref'?: string;
    '!merges'?: Range[];
  }

  export interface ReadOptions {
    dense?: boolean;
  }

  export interface Sheet2JSONOpts {
    header?: number | string[];
    raw?: boolean;
    defval?: unknown;
    range?: Range | string | number;
    blankrows?: boolean;
    skipHidden?: boolean;
  }

  export function read(data: ArrayBuffer, opts?: ReadOptions): WorkBook;

  export const utils: {
    sheet_to_json<T = unknown[]>(sheet: WorkSheet, opts?: Sheet2JSONOpts): T[];
    decode_range(range: string): Range;
    encode_range(range: Range): string;
    encode_range(s: CellAddress, e: CellAddress): string;
  };
}
