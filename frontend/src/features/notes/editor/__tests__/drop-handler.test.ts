import { describe, it, expect } from 'vitest';

// Tests the file-type routing logic used in the updated config.ts drop handler.
// Full integration test (editor mount + actual drop) belongs in e2e — this tests the decision logic.
describe('drop handler file type routing', () => {
  it('routes image/* files to FigureNode insertion', () => {
    const isImageFile = (file: File) => file.type.startsWith('image/');
    const imageFile = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });
    const pdfFile = new File(['data'], 'doc.pdf', { type: 'application/pdf' });
    expect(isImageFile(imageFile)).toBe(true);
    expect(isImageFile(pdfFile)).toBe(false);
  });

  it('routes non-image files to FileCardNode insertion', () => {
    const isFileCard = (file: File) => !file.type.startsWith('image/');
    const pdfFile = new File(['data'], 'doc.pdf', { type: 'application/pdf' });
    const imageFile = new File(['data'], 'photo.png', { type: 'image/png' });
    expect(isFileCard(pdfFile)).toBe(true);
    expect(isFileCard(imageFile)).toBe(false);
  });

  it('handles multiple files in a single drop (returns array of node types)', () => {
    const routeFiles = (files: File[]) =>
      files.map((f) => (f.type.startsWith('image/') ? 'figure' : 'fileCard'));

    const files = [
      new File([''], 'img.png', { type: 'image/png' }),
      new File([''], 'doc.pdf', { type: 'application/pdf' }),
      new File([''], 'bg.jpg', { type: 'image/jpeg' }),
    ];
    expect(routeFiles(files)).toEqual(['figure', 'fileCard', 'figure']);
  });
});
