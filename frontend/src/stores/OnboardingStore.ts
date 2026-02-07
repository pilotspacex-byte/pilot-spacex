'use client';

import { makeAutoObservable, computed, runInAction } from 'mobx';

/**
 * OnboardingStore - MobX UI state for onboarding modal.
 *
 * Tracks client-side UI state for the onboarding modal dialog.
 * Server state (step completion) is managed by TanStack Query.
 *
 * T004: Create OnboardingStore (MobX UI state)
 * Source: FR-001, FR-003, FR-013, US1
 */

export type OnboardingActiveStep = 'ai_providers' | 'invite_members' | 'first_note' | null;

const ONBOARDING_STORAGE_KEY = 'pilot-space:onboarding-ui-state';

interface PersistedOnboardingState {
  modalOpen: boolean;
}

export class OnboardingStore {
  /**
   * Whether the onboarding modal is open.
   * Persisted to localStorage so it stays closed if user manually closes it.
   */
  modalOpen = true;

  /**
   * Currently active/focused step in the checklist.
   */
  activeStep: OnboardingActiveStep = null;

  /**
   * Whether celebration animation is currently showing.
   * Auto-clears after 3 seconds.
   */
  showingCelebration = false;

  /**
   * Whether the invite dialog was opened from onboarding.
   * Used to trigger step completion on successful invite.
   */
  inviteDialogFromOnboarding = false;

  /**
   * Track hydration state for SSR.
   */
  private hydrated = false;

  private celebrationTimeout: NodeJS.Timeout | null = null;

  constructor() {
    makeAutoObservable(this, {
      isModalOpen: computed,
    });
  }

  /**
   * Hydrate state from localStorage (call in useEffect).
   */
  hydrate(): void {
    if (this.hydrated) return;

    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(ONBOARDING_STORAGE_KEY);
        if (stored) {
          const state: PersistedOnboardingState = JSON.parse(stored);
          this.modalOpen = state.modalOpen ?? true;
        }
      } catch {
        // Ignore parse errors
      }
    }

    this.hydrated = true;
  }

  /**
   * Whether onboarding modal should be open.
   */
  get isModalOpen(): boolean {
    return this.modalOpen;
  }

  /**
   * Open the onboarding modal.
   */
  openModal(): void {
    this.modalOpen = true;
    this.persist();
  }

  /**
   * Close the onboarding modal (local only, can re-open).
   */
  closeModal(): void {
    this.modalOpen = false;
    this.persist();
  }

  /**
   * Set the active step.
   */
  setActiveStep(step: OnboardingActiveStep): void {
    this.activeStep = step;
  }

  /**
   * Clear active step.
   */
  clearActiveStep(): void {
    this.activeStep = null;
  }

  /**
   * Mark that invite dialog was opened from onboarding.
   */
  setInviteDialogFromOnboarding(value: boolean): void {
    this.inviteDialogFromOnboarding = value;
  }

  /**
   * Trigger celebration animation (FR-013).
   * Auto-closes modal after 3 seconds.
   */
  triggerCelebration(): void {
    if (this.celebrationTimeout) {
      clearTimeout(this.celebrationTimeout);
    }

    this.showingCelebration = true;

    this.celebrationTimeout = setTimeout(() => {
      runInAction(() => {
        this.showingCelebration = false;
        this.closeModal();
        this.celebrationTimeout = null;
      });
    }, 3000);
  }

  /**
   * Clear celebration state.
   */
  clearCelebration(): void {
    if (this.celebrationTimeout) {
      clearTimeout(this.celebrationTimeout);
      this.celebrationTimeout = null;
    }
    this.showingCelebration = false;
  }

  /**
   * Persist state to localStorage.
   */
  private persist(): void {
    if (typeof window === 'undefined') return;

    try {
      const state: PersistedOnboardingState = {
        modalOpen: this.modalOpen,
      };
      localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Ignore storage errors
    }
  }

  /**
   * Clean up timeouts to prevent memory leaks.
   */
  dispose(): void {
    this.clearCelebration();
  }

  /**
   * Reset store to initial state.
   */
  reset(): void {
    this.modalOpen = true;
    this.activeStep = null;
    this.showingCelebration = false;
    this.inviteDialogFromOnboarding = false;
    this.clearCelebration();

    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem(ONBOARDING_STORAGE_KEY);
      } catch {
        // Ignore storage errors
      }
    }
  }
}
