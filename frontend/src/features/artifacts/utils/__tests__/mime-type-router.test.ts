import { describe, it, expect } from 'vitest';
import { resolveRenderer, getLanguageForFile } from '../mime-type-router';

describe('resolveRenderer', () => {
  describe('image MIME types', () => {
    it('returns "image" for image/png', () => {
      expect(resolveRenderer('image/png', 'photo.png')).toBe('image');
    });

    it('returns "image" for image/jpeg', () => {
      expect(resolveRenderer('image/jpeg', 'photo.jpg')).toBe('image');
    });

    it('returns "image" for image/gif', () => {
      expect(resolveRenderer('image/gif', 'anim.gif')).toBe('image');
    });

    it('returns "image" for image/webp', () => {
      expect(resolveRenderer('image/webp', 'photo.webp')).toBe('image');
    });

    it('returns "html-preview" for image/svg+xml (SVGs are sandboxed)', () => {
      expect(resolveRenderer('image/svg+xml', 'icon.svg')).toBe('html-preview');
    });
  });

  describe('CSV files', () => {
    it('returns "csv" for text/csv MIME type', () => {
      expect(resolveRenderer('text/csv', 'data.csv')).toBe('csv');
    });

    it('returns "csv" for text/plain with .csv extension', () => {
      expect(resolveRenderer('text/plain', 'data.csv')).toBe('csv');
    });

    it('returns "csv" for application/csv MIME type via extension', () => {
      expect(resolveRenderer('application/csv', 'report.csv')).toBe('csv');
    });
  });

  describe('Markdown files', () => {
    it('returns "markdown" for text/markdown MIME type', () => {
      expect(resolveRenderer('text/markdown', 'README.md')).toBe('markdown');
    });

    it('returns "markdown" for text/plain with .md extension (filename wins)', () => {
      expect(resolveRenderer('text/plain', 'README.md')).toBe('markdown');
    });
  });

  describe('JSON files', () => {
    it('returns "json" for application/json MIME type', () => {
      expect(resolveRenderer('application/json', 'data.json')).toBe('json');
    });

    it('returns "json" for text/json via extension fallback', () => {
      expect(resolveRenderer('text/json', 'data.json')).toBe('json');
    });

    it('returns "json" for text/plain with .json extension', () => {
      expect(resolveRenderer('text/plain', 'config.json')).toBe('json');
    });
  });

  describe('HTML files — routes to "html-preview" renderer', () => {
    it('returns "html-preview" for text/html MIME type', () => {
      expect(resolveRenderer('text/html', 'page.html')).toBe('html-preview');
    });

    it('returns "html-preview" for text/plain with .html extension', () => {
      expect(resolveRenderer('text/plain', 'index.html')).toBe('html-preview');
    });

    it('returns "html-preview" for .htm extension', () => {
      expect(resolveRenderer('text/plain', 'index.htm')).toBe('html-preview');
    });
  });

  describe('code files (text/plain with code extension)', () => {
    it('returns "code" for text/plain with .py extension (Python file extension)', () => {
      expect(resolveRenderer('text/plain', 'main.py')).toBe('code');
    });

    it('returns "code" for text/plain with .ts extension', () => {
      expect(resolveRenderer('text/plain', 'app.ts')).toBe('code');
    });

    it('returns "code" for text/plain with .tsx extension', () => {
      expect(resolveRenderer('text/plain', 'App.tsx')).toBe('code');
    });

    it('returns "code" for text/plain with .js extension', () => {
      expect(resolveRenderer('text/plain', 'script.js')).toBe('code');
    });

    it('returns "code" for text/plain with .sh extension', () => {
      expect(resolveRenderer('text/plain', 'deploy.sh')).toBe('code');
    });

    it('returns "code" for text/plain with .go extension', () => {
      expect(resolveRenderer('text/plain', 'main.go')).toBe('code');
    });

    it('returns "code" for text/plain with .rs extension (Rust)', () => {
      expect(resolveRenderer('text/plain', 'lib.rs')).toBe('code');
    });

    it('returns "code" for text/plain with .css extension', () => {
      expect(resolveRenderer('text/plain', 'style.css')).toBe('code');
    });

    it('returns "code" for text/plain with .scss extension', () => {
      expect(resolveRenderer('text/plain', 'style.scss')).toBe('code');
    });
  });

  describe('plain text files', () => {
    it('returns "text" for text/plain with .txt extension', () => {
      expect(resolveRenderer('text/plain', 'notes.txt')).toBe('text');
    });

    it('returns "text" for text/plain with no recognized extension', () => {
      expect(resolveRenderer('text/plain', 'unknown')).toBe('text');
    });
  });

  describe('download fallback', () => {
    it('returns "download" for application/pdf', () => {
      expect(resolveRenderer('application/pdf', 'doc.pdf')).toBe('download');
    });

    it('returns "download" for application/octet-stream binary', () => {
      expect(resolveRenderer('application/octet-stream', 'binary.bin')).toBe('download');
    });

    it('returns "download" for application/zip', () => {
      expect(resolveRenderer('application/zip', 'archive.zip')).toBe('download');
    });

    it('returns "download" for video/mp4', () => {
      expect(resolveRenderer('video/mp4', 'video.mp4')).toBe('download');
    });
  });

  describe('case insensitivity', () => {
    it('handles uppercase MIME type', () => {
      expect(resolveRenderer('IMAGE/PNG', 'photo.png')).toBe('image');
    });

    it('handles mixed case MIME type', () => {
      expect(resolveRenderer('Text/CSV', 'data.csv')).toBe('csv');
    });
  });
});

describe('getLanguageForFile', () => {
  it('returns "python" for .py files', () => {
    expect(getLanguageForFile('main.py')).toBe('python');
  });

  it('returns "typescript" for .tsx files', () => {
    expect(getLanguageForFile('app.tsx')).toBe('typescript');
  });

  it('returns "typescript" for .ts files', () => {
    expect(getLanguageForFile('types.ts')).toBe('typescript');
  });

  it('returns "javascript" for .js files', () => {
    expect(getLanguageForFile('script.js')).toBe('javascript');
  });

  it('returns "javascript" for .jsx files', () => {
    expect(getLanguageForFile('App.jsx')).toBe('javascript');
  });

  it('returns "scss" for .scss files', () => {
    expect(getLanguageForFile('style.scss')).toBe('scss');
  });

  it('returns "html" for .html files', () => {
    expect(getLanguageForFile('page.html')).toBe('html');
  });

  it('returns "css" for .css files', () => {
    expect(getLanguageForFile('style.css')).toBe('css');
  });

  it('returns "bash" for .sh files', () => {
    expect(getLanguageForFile('deploy.sh')).toBe('bash');
  });

  it('returns "yaml" for .yaml files', () => {
    expect(getLanguageForFile('config.yaml')).toBe('yaml');
  });

  it('returns "yaml" for .yml files', () => {
    expect(getLanguageForFile('docker-compose.yml')).toBe('yaml');
  });

  it('returns "go" for .go files', () => {
    expect(getLanguageForFile('main.go')).toBe('go');
  });

  it('returns "rust" for .rs files', () => {
    expect(getLanguageForFile('lib.rs')).toBe('rust');
  });

  it('returns "json" for .json files', () => {
    expect(getLanguageForFile('config.json')).toBe('json');
  });

  it('returns "sql" for .sql files', () => {
    expect(getLanguageForFile('migration.sql')).toBe('sql');
  });

  it('returns "graphql" for .graphql files', () => {
    expect(getLanguageForFile('schema.graphql')).toBe('graphql');
  });

  it('returns "graphql" for .gql files', () => {
    expect(getLanguageForFile('query.gql')).toBe('graphql');
  });

  it('returns "plaintext" for unknown .xyz extension', () => {
    expect(getLanguageForFile('unknown.xyz')).toBe('plaintext');
  });

  it('returns "dockerfile" for extensionless Dockerfile', () => {
    expect(getLanguageForFile('Dockerfile')).toBe('dockerfile');
  });

  it('handles uppercase extensions', () => {
    // Extensions are lowercased internally
    expect(getLanguageForFile('SCRIPT.JS')).toBe('javascript');
  });

  it('returns "markdown" for .md files', () => {
    expect(getLanguageForFile('README.md')).toBe('markdown');
  });

  it('returns "c" for .c files', () => {
    expect(getLanguageForFile('main.c')).toBe('c');
  });

  it('returns "cpp" for .cpp files', () => {
    expect(getLanguageForFile('app.cpp')).toBe('cpp');
  });
});
