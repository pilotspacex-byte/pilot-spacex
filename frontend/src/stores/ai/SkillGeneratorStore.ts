/**
 * SkillGeneratorStore - MobX observable store for skill generation state.
 * Tracks draft content, preview state, and save confirmation during
 * conversational skill creation via SSE events.
 *
 * @module stores/ai/SkillGeneratorStore
 * @see ./types/events-skill-gen.ts for SSE event type definitions
 */
import { makeAutoObservable } from 'mobx';
import type {
  SkillDraftEvent,
  SkillPreviewEvent,
  SkillSavedEvent,
  GraphUpdateEvent,
} from './types/events-skill-gen';

export interface SkillDraft {
  sessionId: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  skillContent: string;
  examplePrompts: string[];
  contextRequirements: string[];
  toolDeclarations: string[];
  graphData: SkillPreviewEvent['data']['graphData'];
}

export class SkillGeneratorStore {
  /** Current skill draft being generated/refined */
  currentDraft: SkillDraft | null = null;
  /** Partial content being streamed */
  streamingContent: string = '';
  /** Whether a skill preview is visible in the editor panel */
  isPreviewVisible: boolean = false;
  /** Whether the save dialog is open */
  isSaveDialogOpen: boolean = false;
  /** Last saved skill info (for toast notification) */
  lastSaved: { skillId: string; skillName: string; saveType: 'personal' | 'workspace' } | null =
    null;
  /** Whether skill generation is in progress */
  isGenerating: boolean = false;

  constructor() {
    makeAutoObservable(this);
  }

  // --- Event handlers called by PilotSpaceStreamHandler ---

  handleSkillDraft(data: SkillDraftEvent['data']): void {
    this.isGenerating = true;
    this.streamingContent = data.content;
    if (!data.isPartial) {
      // Full content received, update draft if exists
      if (this.currentDraft) {
        this.currentDraft.skillContent = data.content;
      }
    }
  }

  handleSkillPreview(data: SkillPreviewEvent['data']): void {
    this.isGenerating = false;
    this.streamingContent = '';
    this.currentDraft = {
      sessionId: data.sessionId,
      name: data.name,
      description: data.description,
      category: data.category,
      icon: data.icon,
      skillContent: data.skillContent,
      examplePrompts: data.examplePrompts,
      contextRequirements: data.contextRequirements,
      toolDeclarations: data.toolDeclarations,
      graphData: data.graphData,
    };
    this.isPreviewVisible = true;
  }

  handleSkillSaved(data: SkillSavedEvent['data']): void {
    this.lastSaved = {
      skillId: data.skillId,
      skillName: data.skillName,
      saveType: data.saveType,
    };
    this.isSaveDialogOpen = false;
    this.isPreviewVisible = false;
    this.currentDraft = null;
  }

  handleGraphUpdate(_data: GraphUpdateEvent['data']): void {
    // Update graph data in current draft based on CRUD operation.
    // Graph CRUD operations will be expanded in Phase 52.
    // For now, the event is acknowledged but no-op without a draft.
    if (!this.currentDraft?.graphData) return;
  }

  // --- UI actions ---

  openSaveDialog(): void {
    this.isSaveDialogOpen = true;
  }
  closeSaveDialog(): void {
    this.isSaveDialogOpen = false;
  }
  dismissPreview(): void {
    this.isPreviewVisible = false;
  }
  clearLastSaved(): void {
    this.lastSaved = null;
  }

  reset(): void {
    this.currentDraft = null;
    this.streamingContent = '';
    this.isPreviewVisible = false;
    this.isSaveDialogOpen = false;
    this.lastSaved = null;
    this.isGenerating = false;
  }
}
