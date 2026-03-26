/**
 * OCR API client — workspace OCR provider settings.
 * Supports HunyuanOCR (self-hosted vLLM) and Tencent Cloud OCR.
 */

import { apiClient } from './client';

export interface OcrSettingsResponse {
  provider_type: 'hunyuan_ocr' | 'tencent_ocr' | 'none';
  is_configured: boolean;
  is_valid: boolean | null;
  endpoint_url: string | null;
  model_name: string | null;
}

export interface UpdateOcrSettingsRequest {
  provider_type: 'hunyuan_ocr' | 'tencent_ocr' | 'none';
  endpoint_url?: string;
  api_key?: string;
  model_name?: string;
  region?: string;
  secret_id?: string;
  secret_key?: string;
}

export interface OcrConnectionTestResult {
  success: boolean;
  error: string | null;
  extracted_text: string | null;
}

export async function getOcrSettings(workspaceId: string): Promise<OcrSettingsResponse> {
  return apiClient.get<OcrSettingsResponse>(`/workspaces/${workspaceId}/ocr/settings`);
}

export async function updateOcrSettings(
  workspaceId: string,
  data: UpdateOcrSettingsRequest
): Promise<OcrSettingsResponse> {
  return apiClient.put<OcrSettingsResponse>(`/workspaces/${workspaceId}/ocr/settings`, data);
}

export async function testOcrConnection(
  workspaceId: string,
  data: UpdateOcrSettingsRequest,
): Promise<OcrConnectionTestResult> {
  return apiClient.post<OcrConnectionTestResult>(`/workspaces/${workspaceId}/ocr/settings/test`, data);
}
