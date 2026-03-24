import { apiClient } from './client';

export interface AnnotationResponse {
  id: string;
  artifact_id: string;
  slide_index: number;
  content: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface AnnotationListResponse {
  annotations: AnnotationResponse[];
  total: number;
}

export const annotationsApi = {
  /**
   * List annotations for an artifact, optionally filtered by slide index.
   *
   * GET /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations?slide_index=N
   */
  list(
    workspaceId: string,
    projectId: string,
    artifactId: string,
    slideIndex?: number
  ): Promise<AnnotationListResponse> {
    const params = slideIndex !== undefined ? `?slide_index=${slideIndex}` : '';
    return apiClient.get<AnnotationListResponse>(
      `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}/annotations${params}`
    );
  },

  /**
   * Create an annotation on a specific slide.
   *
   * POST /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations
   */
  create(
    workspaceId: string,
    projectId: string,
    artifactId: string,
    data: { slide_index: number; content: string }
  ): Promise<AnnotationResponse> {
    return apiClient.post<AnnotationResponse>(
      `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}/annotations`,
      data
    );
  },

  /**
   * Update an annotation's content.
   *
   * PUT /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations/{annotationId}
   */
  update(
    workspaceId: string,
    projectId: string,
    artifactId: string,
    annotationId: string,
    data: { content: string }
  ): Promise<AnnotationResponse> {
    return apiClient.put<AnnotationResponse>(
      `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}/annotations/${annotationId}`,
      data
    );
  },

  /**
   * Delete an annotation.
   *
   * DELETE /workspaces/{wid}/projects/{pid}/artifacts/{aid}/annotations/{annotationId}
   */
  delete(
    workspaceId: string,
    projectId: string,
    artifactId: string,
    annotationId: string
  ): Promise<void> {
    return apiClient.delete<void>(
      `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}/annotations/${annotationId}`
    );
  },
};
