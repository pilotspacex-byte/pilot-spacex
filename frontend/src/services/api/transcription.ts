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
  /** Signed URL for audio playback (1h expiry). Null if storage upload failed or for cache hits. */
  audioUrl: string | null;
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
    // Use the raw axios instance so we can properly override headers.
    // The apiClient defaults Content-Type to 'application/json', which prevents
    // axios from auto-detecting multipart/form-data from the FormData body.
    // Setting Content-Type to undefined tells axios to auto-set it with the
    // correct multipart boundary from FormData.
    const config = {
      headers: {
        'Content-Type': undefined as unknown as string,
        ...(workspaceId ? { 'X-Workspace-Id': workspaceId } : {}),
      },
    };
    return apiClient.instance
      .post<TranscribeResponse>('/ai/transcribe', formData, config)
      .then((res) => res.data);
  },
};
