'use client';

import { makeAutoObservable, runInAction } from 'mobx';
import type { ProjectEntry, GitProgress } from '@/lib/tauri';

export class ProjectStore {
  projects: ProjectEntry[] = [];
  projectsDir: string = '';
  isLoading = false;
  error: string | null = null;

  // Clone state
  isCloning = false;
  cloneProgress: GitProgress | null = null;
  cloneError: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  async loadProjects(): Promise<void> {
    this.isLoading = true;
    this.error = null;
    try {
      const { listProjects, getProjectsDir } = await import('@/lib/tauri');
      const [projects, dir] = await Promise.all([listProjects(), getProjectsDir()]);
      runInAction(() => {
        this.projects = projects;
        this.projectsDir = dir;
        this.isLoading = false;
      });
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
        this.isLoading = false;
      });
    }
  }

  async cloneRepo(url: string): Promise<void> {
    this.isCloning = true;
    this.cloneProgress = null;
    this.cloneError = null;
    try {
      const { gitClone, getProjectsDir } = await import('@/lib/tauri');
      const baseDir = await getProjectsDir();
      // Derive target dir from URL: https://github.com/user/repo.git -> repo
      const repoName = url.split('/').pop()?.replace(/\.git$/, '') || 'repo';
      const targetDir = `${baseDir}/${repoName}`;
      await gitClone(url, targetDir, (progress) => {
        runInAction(() => {
          this.cloneProgress = progress;
        });
      });
      runInAction(() => {
        this.isCloning = false;
        this.cloneProgress = null;
      });
      // Refresh project list after clone
      await this.loadProjects();
    } catch (e) {
      runInAction(() => {
        this.isCloning = false;
        this.cloneError = e instanceof Error ? e.message : String(e);
      });
    }
  }

  async cancelClone(): Promise<void> {
    try {
      const { cancelClone } = await import('@/lib/tauri');
      await cancelClone();
    } catch {
      // Best effort — ignore errors on cancel
    }
  }

  async linkExistingRepo(path: string): Promise<void> {
    this.error = null;
    try {
      const { linkRepo } = await import('@/lib/tauri');
      const entry = await linkRepo(path);
      runInAction(() => {
        this.projects.push(entry);
      });
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
      });
    }
  }

  reset(): void {
    this.projects = [];
    this.projectsDir = '';
    this.isLoading = false;
    this.error = null;
    this.isCloning = false;
    this.cloneProgress = null;
    this.cloneError = null;
  }
}
