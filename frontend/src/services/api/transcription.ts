/**
 * Transcription API client for ElevenLabs Speech-to-Text.
 *
 * Sends audio blobs to the backend transcription endpoint which proxies
 * to ElevenLabs STT and returns cached or fresh transcription results.
 */

import { apiClient } from './client';

export interface TranscribeResponse {
  transcriptId: string;
  text: string;
  languageCode: string | null;
  durationSeconds: number | null;
  cached: boolean;
}

export const transcriptionApi = {
  /**
   * Transcribe an audio blob using the backend ElevenLabs STT proxy.
   *
   * @param audioBlob - Audio blob from MediaRecorder (audio/webm or similar)
   * @param workspaceId - Workspace UUID for key lookup and cache scoping
   * @param language - Optional ISO 639-1 language code hint (e.g. 'en')
   * @returns Transcription result with text and optional metadata
   */
  transcribe: async (
    audioBlob: Blob,
    workspaceId: string,
    language?: string
  ): Promise<TranscribeResponse> => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.webm');
    if (language) {
      formData.append('language', language);
    }
    return apiClient.post<TranscribeResponse>('/ai/transcribe', formData, {
      headers: {
        'X-Workspace-Id': workspaceId,
        // Let browser set Content-Type with boundary for multipart
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};
