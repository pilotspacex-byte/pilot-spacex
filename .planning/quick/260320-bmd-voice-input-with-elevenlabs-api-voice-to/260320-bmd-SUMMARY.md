---
phase: quick-260320-bmd
plan: 01
subsystem: voice-input
tags: [voice, stt, elevenlabs, transcription, byok, chat, settings]
dependency_graph:
  requires:
    - backend AI provider constants (PROVIDER_SERVICE_SLOTS, VALID_PROVIDER_SERVICES)
    - SecureKeyStorage key management
    - Workspace AI settings schema + router
    - ChatInput toolbar pattern
    - ProviderSection/ProviderConfigForm settings UI
  provides:
    - POST /api/v1/ai/transcribe endpoint
    - ElevenLabs STT provider registration (elevenlabs:stt)
    - Voice recording UI (mic button in ChatInput)
    - Transcript caching (transcript_cache table)
    - Voice Services section in AI Settings
  affects:
    - backend/src/pilot_space/ai/providers/constants.py
    - backend/src/pilot_space/ai/infrastructure/key_storage.py
    - backend/src/pilot_space/api/v1/schemas/workspace.py
    - frontend/src/services/api/ai.ts (WorkspaceAISettingsProvider.serviceType + defaultSttProvider)
    - frontend/src/stores/ai/AISettingsStore.ts
tech_stack:
  added:
    - httpx async HTTP client for ElevenLabs API calls (already a dep)
    - MediaRecorder Web API for browser audio capture
    - ElevenLabs Scribe v1 STT model
  patterns:
    - SHA-256 audio hash deduplication (TranscriptCache)
    - BYOK provider pattern extended to stt service type
    - MediaRecorder lifecycle hook pattern (useVoiceRecording)
key_files:
  created:
    - backend/src/pilot_space/api/v1/routers/transcription.py
    - backend/src/pilot_space/api/v1/schemas/transcription.py
    - backend/src/pilot_space/infrastructure/database/models/transcript_cache.py
    - backend/alembic/versions/091_add_transcript_cache_table.py
    - frontend/src/features/ai/ChatView/ChatInput/RecordButton.tsx
    - frontend/src/features/ai/ChatView/hooks/useVoiceRecording.ts
    - frontend/src/services/api/transcription.ts
  modified:
    - backend/src/pilot_space/ai/providers/constants.py
    - backend/src/pilot_space/ai/infrastructure/key_storage.py
    - backend/src/pilot_space/api/v1/schemas/workspace.py
    - backend/src/pilot_space/infrastructure/database/models/__init__.py
    - backend/src/pilot_space/main.py
    - frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx
    - frontend/src/features/settings/pages/ai-settings-page.tsx
    - frontend/src/features/settings/components/provider-section.tsx
    - frontend/src/features/settings/components/provider-config-form.tsx
    - frontend/src/stores/ai/AISettingsStore.ts
    - frontend/src/services/api/ai.ts
decisions:
  - "ElevenLabs STT uses model_id=scribe_v1 (fixed endpoint, no base_url needed)"
  - "MediaRecorder MIME type selection: webm+opus > webm > ogg+opus > ogg > default"
  - "SHA-256 hash of audio bytes for cache key — ON CONFLICT DO NOTHING for race safety"
  - "stt service type added to VALID_SERVICE_TYPES in SecureKeyStorage (critical fix flagged by plan checker)"
  - "RecordButton uses animate-ping for recording ring (Tailwind built-in, no custom CSS needed)"
  - "handleSave in ProviderConfigForm skips default provider update for stt (only elevenlabs, no choice)"
metrics:
  duration: 15 minutes
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 11
---

# Quick Task 260320-bmd: Voice Input with ElevenLabs API (Voice-to-Text)

**One-liner:** ElevenLabs STT voice input with SHA-256-cached backend proxy, MediaRecorder hook, pulsing RecordButton, and Voice Services section in AI Settings.

## What Was Built

Voice-to-text dictation for AI Chat using ElevenLabs Speech-to-Text API. BYOK pattern — workspace admins configure their ElevenLabs API key in AI Settings under a new "Voice Services" section. Users click the mic button in ChatInput, speak, and the transcript appears in the textarea.

## Task 1: Backend

**ElevenLabs provider registration:**
- Added `("elevenlabs", "stt", False)` to `PROVIDER_SERVICE_SLOTS`
- Added `"elevenlabs": {"stt"}` to `VALID_PROVIDER_SERVICES`
- Added `"stt"` to `SecureKeyStorage.VALID_SERVICE_TYPES` (critical fix — was `frozenset({"embedding", "llm"})`)
- ElevenLabs validation: GET `https://api.elevenlabs.io/v1/models` with `xi-api-key` header
- Updated `APIKeyUpdate` schema patterns to accept `elevenlabs` provider and `stt` service type

**Transcription endpoint (`POST /api/v1/ai/transcribe`):**
- Accepts multipart upload: `file` (audio/*) + optional `language` form field
- `X-Workspace-Id` header for workspace scoping
- Flow: validate MIME type → read bytes → SHA-256 hash → cache check → get ElevenLabs key → proxy to STT → persist cache → return
- Max 25MB file size, allowed types: webm/ogg/wav/mp4/mpeg/m4a/aac
- ON CONFLICT DO NOTHING on cache insert (race-safe deduplication)
- Returns `cached: true` on cache hits

**TranscriptCache model:** `(workspace_id, audio_hash)` unique constraint, index on both columns.

**Migration 091:** Creates `transcript_cache` table with workspace FK, timestamp columns, and indexes.

## Task 2: Frontend

**`transcriptionApi.transcribe()`:** Posts audio blob as multipart FormData with `X-Workspace-Id` header.

**`useVoiceRecording` hook:**
- States: idle → recording → transcribing → idle (or error → idle auto-reset after 3s)
- `startRecording()`: getUserMedia, MediaRecorder with MIME fallback, chunk collection, duration timer
- `stopRecording()`: triggers `onstop` → blob creation → `transcriptionApi.transcribe()` → `onTranscript(text)`
- `cancelRecording()`: discards chunks without transcribing
- Cleanup on unmount via useEffect

**`RecordButton` component:**
- Idle: ghost `Mic` icon (`text-muted-foreground/60`)
- Recording: red `Square` icon + `animate-ping` pulse ring + elapsed time in tooltip
- Transcribing: `Loader2 animate-spin`
- Integrated in `ChatInput` inline toolbar (leftmost, before AttachmentButton)
- `onTranscript` appends text to textarea value with a space separator

**AI Settings page:** New "Voice Services" `ProviderSection` between LLM and Feature Toggles.

**Provider UI updates:**
- `ProviderSection`: `serviceType` union extended to include `'stt'`, `ElevenLabs` display name added
- `ProviderConfigForm`: `serviceType` type updated, ElevenLabs config (api_key only), fixed handleSave to skip `default_*_provider` for stt
- `AISettingsStore`: `getProvidersByService`/`getDefaultProvider` accept `'stt'`, added `sttConfigured` computed, ElevenLabs key validation (length >= 20)
- `WorkspaceAISettings`: added `defaultSttProvider?: string`
- `WorkspaceAISettingsProvider.serviceType`: union now `'embedding' | 'llm' | 'stt'`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical Fix] Added "stt" to VALID_SERVICE_TYPES in SecureKeyStorage**
- **Found during:** Task 1 (flagged by plan checker in `<important_fix>` block)
- **Issue:** `SecureKeyStorage.VALID_SERVICE_TYPES` was hardcoded `frozenset({"embedding", "llm"})` — would raise `ValueError` when calling `store_api_key()` with `service_type="stt"` for ElevenLabs keys
- **Fix:** Updated `VALID_SERVICE_TYPES = frozenset({"embedding", "llm", "stt"})`
- **Files modified:** `backend/src/pilot_space/ai/infrastructure/key_storage.py`
- **Commit:** d38ac084

**2. [Rule 1 - Bug] Fixed handleSave to skip default_embedding_provider for stt**
- **Found during:** Task 2 (code review of existing logic)
- **Issue:** `ProviderConfigForm.handleSave` had `else` branch that would incorrectly set `default_embedding_provider = "elevenlabs"` when `serviceType === "stt"` and `setAsDefault === true`
- **Fix:** Changed `else` to `else if (serviceType === 'embedding')` with explicit comment for stt case
- **Files modified:** `frontend/src/features/settings/components/provider-config-form.tsx`
- **Commit:** 6db3557b

**3. [Rule 2 - Missing] Added `noqa: PLR0911` to validate_api_key**
- **Found during:** Task 1 (ruff check failure)
- **Issue:** Adding ElevenLabs branch pushed `validate_api_key` past the PLR0911 "too many return statements" threshold (9 > 6). Pre-existing design of branching per provider, not appropriate to restructure.
- **Fix:** Added `# noqa: PLR0911` to method signature
- **Files modified:** `backend/src/pilot_space/ai/infrastructure/key_storage.py`
- **Commit:** d38ac084

## Self-Check: PASSED

All 7 created files exist on disk. Both task commits (d38ac084, 6db3557b) exist in git history.
