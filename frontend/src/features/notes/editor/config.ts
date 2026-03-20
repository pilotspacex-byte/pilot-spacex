import { Editor, type Extensions } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import { toast } from 'sonner';
import { artifactsApi } from '@/services/api/artifacts';
import { rootStore } from '@/stores/RootStore';
import type { EditorOptions } from './types';

/**
 * Default character limit for notes
 */
const DEFAULT_CHARACTER_LIMIT = 100000;

/**
 * Default placeholder text
 */
const DEFAULT_PLACEHOLDER = 'Start writing your thoughts...';

/**
 * Base TipTap extensions for the note editor
 */
export function getBaseExtensions(options?: {
  placeholder?: string;
  characterLimit?: number;
}): Extensions {
  const { placeholder = DEFAULT_PLACEHOLDER, characterLimit = DEFAULT_CHARACTER_LIMIT } =
    options ?? {};

  return [
    StarterKit.configure({
      // Configure heading levels
      heading: {
        levels: [1, 2, 3],
      },
      // Disable code block from StarterKit (we have our own)
      codeBlock: false,
      // Configure horizontal rule
      horizontalRule: {
        HTMLAttributes: {
          class: 'note-divider',
        },
      },
      // Configure paragraph
      paragraph: {
        HTMLAttributes: {
          class: 'note-paragraph',
        },
      },
      // Configure bullet list
      bulletList: {
        HTMLAttributes: {
          class: 'note-bullet-list',
        },
        keepMarks: true,
        keepAttributes: false,
      },
      // Configure ordered list
      orderedList: {
        HTMLAttributes: {
          class: 'note-ordered-list',
        },
        keepMarks: true,
        keepAttributes: false,
      },
      // Configure blockquote
      blockquote: {
        HTMLAttributes: {
          class: 'note-blockquote',
        },
      },
    }),
    Placeholder.configure({
      placeholder: ({ node }) => {
        if (node.type.name === 'heading') {
          const level = node.attrs.level as number;
          return `Heading ${level}`;
        }
        return placeholder;
      },
      emptyEditorClass: 'is-editor-empty',
      emptyNodeClass: 'is-empty',
      showOnlyWhenEditable: true,
      showOnlyCurrent: true,
      includeChildren: false,
    }),
    CharacterCount.configure({
      limit: characterLimit,
      mode: 'textSize',
    }),
  ];
}

/**
 * Upload a file and update the corresponding TipTap node attrs.
 *
 * Inserts a placeholder node first, then updates attrs on upload completion
 * or marks it as 'error' if the upload fails.
 *
 * @param editor - The TipTap editor instance
 * @param file - The file to upload
 * @param nodeType - 'figure' | 'fileCard' — determines which attrs to update
 * @param workspaceId - Required for the artifacts API route
 * @param projectId - Required for the artifacts API route
 */
async function uploadFileAndUpdateNode(
  editor: Editor,
  file: File,
  nodeType: 'figure' | 'fileCard',
  workspaceId: string,
  projectId: string
): Promise<void> {
  const uploadKey = `${file.name}-${Date.now()}`;
  rootStore.artifacts.startUpload(uploadKey, file.name);

  try {
    const result = await artifactsApi.upload(workspaceId, projectId, file, (progress) => {
      rootStore.artifacts.setProgress(uploadKey, progress);
    });

    rootStore.artifacts.completeUpload(uploadKey);

    // Find the uploading node with matching filename/alt and update it
    const { doc } = editor.state;
    let targetPos: number | null = null;

    doc.descendants((node, pos) => {
      if (targetPos !== null) return false;
      if (node.type.name === nodeType && node.attrs.status === 'uploading') {
        if (
          (nodeType === 'fileCard' && node.attrs.filename === file.name) ||
          (nodeType === 'figure' && node.attrs.alt === file.name)
        ) {
          targetPos = pos;
        }
      }
    });

    if (targetPos !== null) {
      let updatedAttrs: Record<string, unknown>;

      if (nodeType === 'figure') {
        // Get signed URL for image display
        let src: string = result.id;
        try {
          const urlResult = await artifactsApi.getSignedUrl(workspaceId, projectId, result.id);
          src = urlResult.url;
        } catch {
          // Fall back to artifact ID if signed URL fetch fails
        }
        updatedAttrs = { artifactId: result.id, src, status: 'ready' };
      } else {
        updatedAttrs = { artifactId: result.id, status: 'ready' };
      }

      const currentNode = editor.state.doc.nodeAt(targetPos);
      if (currentNode) {
        editor.view.dispatch(
          editor.state.tr.setNodeMarkup(targetPos, undefined, {
            ...currentNode.attrs,
            ...updatedAttrs,
          })
        );
      }
    }
  } catch (err) {
    rootStore.artifacts.completeUpload(uploadKey);

    // Update the node to error state
    const { doc } = editor.state;
    let targetPos: number | null = null;
    doc.descendants((node, pos) => {
      if (targetPos !== null) return false;
      if (node.type.name === nodeType && node.attrs.status === 'uploading') {
        targetPos = pos;
      }
    });
    if (targetPos !== null) {
      const currentNode = editor.state.doc.nodeAt(targetPos);
      if (currentNode) {
        editor.view.dispatch(
          editor.state.tr.setNodeMarkup(targetPos, undefined, {
            ...currentNode.attrs,
            status: 'error',
          })
        );
      }
    }

    const message = err instanceof Error ? err.message : 'Upload failed';
    toast.error(`Failed to upload ${file.name}`, { description: message });
  }
}

/**
 * Create a TipTap editor instance with the Note-First configuration
 *
 * @example
 * ```tsx
 * const editor = createEditor({
 *   content: note.content,
 *   placeholder: 'Start writing...',
 *   onUpdate: ({ editor }) => {
 *     noteStore.updateContent(noteId, editor.getJSON());
 *   },
 * });
 * ```
 */
export function createEditor(options: EditorOptions = {}): Editor {
  const {
    content,
    placeholder,
    editable = true,
    autofocus = false,
    workspaceId,
    projectId,
    onUpdate,
    onSelectionUpdate,
    onBlur,
    onFocus,
    onCreate,
    onDestroy,
  } = options;

  const extensions = getBaseExtensions({ placeholder });

  // Closure variable so the drop handler can access the Editor instance
  // (EditorView.editor is TipTap-specific at runtime but not in the @tiptap/pm types)
  let editorRef: Editor | null = null;

  return new Editor({
    extensions,
    content,
    editable,
    autofocus,
    editorProps: {
      attributes: {
        class: 'note-editor prose prose-lg dark:prose-invert focus:outline-none',
        spellcheck: 'true',
      },
      handleDOMEvents: {
        // Route file drops to FigureNode (images) or FileCardNode (other files)
        drop: (view, event) => {
          const files = event.dataTransfer?.files;
          if (!files?.length) return false;

          event.preventDefault();

          const coords = view.posAtCoords({ left: event.clientX, top: event.clientY });
          const insertPos = coords?.pos ?? view.state.doc.content.size;

          for (const file of Array.from(files)) {
            const isImage = file.type.startsWith('image/');
            const nodeType = isImage ? 'figure' : 'fileCard';

            const nodeAttrs = isImage
              ? { src: null, alt: file.name, artifactId: null, status: 'uploading' }
              : {
                  artifactId: null,
                  filename: file.name,
                  mimeType: file.type,
                  sizeBytes: file.size,
                  status: 'uploading',
                };

            try {
              const nodeJSON = {
                type: nodeType,
                attrs: nodeAttrs,
                ...(isImage ? { content: [] } : {}),
              };
              view.dispatch(
                view.state.tr.insert(insertPos, view.state.schema.nodeFromJSON(nodeJSON))
              );
            } catch {
              // Extension not registered — skip silently
              continue;
            }

            if (workspaceId && projectId && editorRef) {
              void uploadFileAndUpdateNode(editorRef, file, nodeType, workspaceId, projectId);
            }
          }
          return true;
        },
      },
    },
    parseOptions: {
      preserveWhitespace: 'full',
    },
    onUpdate: onUpdate
      ? ({ editor, transaction }) => {
          onUpdate({ editor, transaction });
        }
      : undefined,
    onSelectionUpdate: onSelectionUpdate
      ? ({ editor, transaction }) => {
          onSelectionUpdate({ editor, transaction });
        }
      : undefined,
    onBlur: onBlur
      ? ({ editor, event }) => {
          onBlur({ editor, event });
        }
      : undefined,
    onFocus: onFocus
      ? ({ editor, event }) => {
          onFocus({ editor, event });
        }
      : undefined,
    onCreate: ({ editor: createdEditor }) => {
      // Capture editor reference for use in the drop handler closure
      editorRef = createdEditor;

      // Cleanup: remove stale fileCard nodes with artifactId: null from crashed uploads
      const stalePositions: number[] = [];
      createdEditor.state.doc.descendants((node, pos) => {
        if (node.type.name === 'fileCard' && node.attrs.artifactId === null) {
          stalePositions.push(pos);
        }
      });

      if (stalePositions.length > 0) {
        console.warn(
          `[Phase32] Removing ${stalePositions.length} stale fileCard node(s) with artifactId: null`
        );
        // Delete from end to start so positions stay valid
        let tr = createdEditor.state.tr;
        for (const pos of stalePositions.reverse()) {
          const node = createdEditor.state.doc.nodeAt(pos);
          if (node) {
            tr = tr.delete(pos, pos + node.nodeSize);
          }
        }
        createdEditor.view.dispatch(tr);
      }

      // Listen for pilot:upload-artifact events dispatched by slash commands
      createdEditor.view.dom.addEventListener('pilot:upload-artifact', (e) => {
        const customEvent = e as CustomEvent<{
          file: File;
          nodeType: 'figure' | 'fileCard';
          editor: Editor;
        }>;
        const { file, nodeType } = customEvent.detail;
        if (workspaceId && projectId) {
          void uploadFileAndUpdateNode(
            customEvent.detail.editor,
            file,
            nodeType,
            workspaceId,
            projectId
          );
        }
      });

      // Chain into any existing onCreate callback from EditorOptions
      if (onCreate) {
        onCreate({ editor: createdEditor });
      }
    },
    onDestroy,
  });
}

/**
 * Default editor configuration values
 */
export const editorConfig = {
  characterLimit: DEFAULT_CHARACTER_LIMIT,
  placeholder: DEFAULT_PLACEHOLDER,
  headingLevels: [1, 2, 3] as const,
  historyDepth: 100,
  historyGroupDelay: 500,
} as const;

/**
 * CSS classes for editor elements
 */
export const editorClasses = {
  editor: 'note-editor',
  paragraph: 'note-paragraph',
  heading: 'note-heading',
  bulletList: 'note-bullet-list',
  orderedList: 'note-ordered-list',
  blockquote: 'note-blockquote',
  codeBlock: 'note-code-block',
  divider: 'note-divider',
  empty: 'is-editor-empty',
  emptyNode: 'is-empty',
} as const;
