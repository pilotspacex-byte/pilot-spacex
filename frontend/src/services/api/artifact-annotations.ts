import { apiClient } from './client';

/**
 * ArtifactAnnotation — a text annotation scoped to a specific slide within a PPTX artifact.
 *
 * Annotations are ephemeral comments (hard-deleted, no soft-delete) owned by a single user.
 * RLS enforces workspace isolation; author ownership enforced at router layer.
 */
export interface ArtifactAnnotation {
  id: string;
  artifactId: string;
  slideIndex: number;
  content: string;
  userId: string;
  workspaceId: string;
  createdAt: string;
  updatedAt: string;
}

interface AnnotationListResponse {
  annotations: ArtifactAnnotation[];
  total: number;
}

/**
 * annotationApi — CRUD operations for PPTX slide annotations.
 *
 * All endpoints are scoped under:
 *   /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations
 */
export const annotationApi = {
  /**
   * List all annotations for a specific slide.
   *
   * GET /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations?slideIndex=N
   * Returns the `annotations` array from the paginated response.
   */
  list(wid: string, pid: string, aid: string, slideIndex: number): Promise<ArtifactAnnotation[]> {
    return apiClient
      .get<AnnotationListResponse>(
        `/workspaces/${wid}/projects/${pid}/artifacts/${aid}/annotations?slide_index=${slideIndex}`
      )
      .then((res) => res.annotations);
  },

  /**
   * Create a new annotation on a specific slide.
   *
   * POST /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations
   * Returns the newly created ArtifactAnnotation (201).
   */
  create(
    wid: string,
    pid: string,
    aid: string,
    body: { slideIndex: number; content: string }
  ): Promise<ArtifactAnnotation> {
    return apiClient.post<ArtifactAnnotation>(
      `/workspaces/${wid}/projects/${pid}/artifacts/${aid}/annotations`,
      { slide_index: body.slideIndex, content: body.content }
    );
  },

  /**
   * Update the content of an existing annotation (author only).
   *
   * PUT /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations/{annotationId}
   * Returns the updated ArtifactAnnotation.
   */
  update(
    wid: string,
    pid: string,
    aid: string,
    annotationId: string,
    body: { content: string }
  ): Promise<ArtifactAnnotation> {
    return apiClient.put<ArtifactAnnotation>(
      `/workspaces/${wid}/projects/${pid}/artifacts/${aid}/annotations/${annotationId}`,
      body
    );
  },

  /**
   * Delete an annotation (author only, hard delete).
   *
   * DELETE /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations/{annotationId}
   * Returns 204 No Content.
   */
  delete(wid: string, pid: string, aid: string, annotationId: string): Promise<void> {
    return apiClient.delete<void>(
      `/workspaces/${wid}/projects/${pid}/artifacts/${aid}/annotations/${annotationId}`
    );
  },
};
