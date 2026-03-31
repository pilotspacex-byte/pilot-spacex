/**
 * ProjectMemberStore — MobX store for project membership UI state.
 *
 * T035 [US5]: Observable projectFilter for Members page filter UI.
 * Provides setProjectFilter and clearFilter actions.
 */

import { makeAutoObservable } from 'mobx';

export class ProjectMemberStore {
  /** Currently selected project filter ID, or null for "all projects". */
  projectFilter: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  setProjectFilter(projectId: string | null) {
    this.projectFilter = projectId;
  }

  clearFilter() {
    this.projectFilter = null;
  }
}

export const projectMemberStore = new ProjectMemberStore();
