/**
 * AI Stores - Centralized exports for AI-related MobX stores.
 */

// AI Store (root)
export { AIStore, aiStore, getAIStore } from './AIStore';

// Feature Stores
export { GhostTextStore } from './GhostTextStore';
export { AIContextStore } from './AIContextStore';
export { ApprovalStore } from './ApprovalStore';
export { AISettingsStore } from './AISettingsStore';

// Types
export type { AIContextPhase, AIContextResult } from './AIContextStore';
export type { ApprovalRequest } from '@/services/api';
