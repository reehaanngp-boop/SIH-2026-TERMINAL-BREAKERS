# DigiRaksha API Reference

All endpoints live under the `/api/v1` prefix. The interactive Swagger UI is available at `/docs` and ReDoc at `/redoc` when the server is running.

---

## Table of Contents

- [System Endpoints](#system-endpoints)
  - [GET /health](#get-health)
  - [GET /meta](#get-meta)
- [Analysis Endpoints](#analysis-endpoints)
  - [POST /analyze/transcript](#post-analyzetranscript)
  - [POST /analyze](#post-analyze)
  - [GET /analyze/jobs/{job_id}](#get-analyzejobsjob_id)
  - [GET /analyze/results/{scan_id}](#get-analyzeresultsscan_id)
  - [GET /analyze/history](#get-analyzehistory)
- [Family Safe-Voice Registry](#family-safe-voice-registry)
  - [POST /registry/members](#post-registrymembers)
  - [GET /registry/members](#get-registrymembers)
  - [DELETE /registry/members/{member_id}](#delete-registrymembersmember_id)
  - [POST /registry/members/{member_id}/enroll](#post-registrymembersmember_idenroll)
  - [POST /registry/verify](#post-registryverify)
- [Schemas](#schemas)
- [Error Handling](#error-handling)

---

## System Endpoints

### `GET /health`

Liveness probe. Returns application name, version, and API version.

**Response:**

```json
{
  "status": "ok",
  "app": "DigiRaksha",
  "version": "0.1.0",
  "api_version": "v1"
}
```

---

### `GET /meta`

Application metadata: detector availability, engine types, and official report channels.

**Response:**

```json
{
  "app": "DigiRaksha",
  "version": "0.1.0",
  "detectors": {
    "asr": { "name": "ASR", "available": true, "model": "small", "device": "cpu" },
    "voice": { "name": "Voice Anti-Spoof", "available": true, "aasist_available": true, "engine": "aasist" },
    "video": { "name": "Video Deepfake", "available": true },
    "text": { "name": "Scam Classifier", "available": true, "model_path": "data/models/scam_classifier.joblib" }
  },
  "report": {
    "helpline": "1930",
    "portal": "https://cybercrime.gov.in",
    "i4c": "https://i4c.mha.gov.in"
  }
}
```

---

## Analysis Endpoints

### `POST /analyze/transcript`

Analyse a raw call transcript synchronously (no media upload required).

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | The call transcript (1–20,000 characters) |
| `language_hint` | string \| null | No | ISO-639-1 code, e.g. `"en"`, `"hi"` |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/analyze/transcript \
  -H "Content-Type: application/json" \
  -d '{"text": "This is CBI, you are under digital arrest. Pay the verification fee.", "language_hint": "en"}'
```

**Response:** `AnalysisResult` (see [Schemas](#schemas))

---

### `POST /analyze`

Upload an audio or video file for asynchronous analysis. Returns a job ID for polling.

**Request Body:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Audio (.wav, .mp3, .m4a, .ogg, .flac) or video (.mp4, .mov, .webm) |

**Constraints:**

- Max file size: 50 MB (configurable via `max_upload_mb`)
- Max duration: 600 seconds (configurable via `max_duration_seconds`)

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@suspicious_call.wav"
```

**Response:**

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "queued",
  "detail": "Analysis started."
}
```

---

### `GET /analyze/jobs/{job_id}`

Poll the status of an analysis job. When completed, the response includes the full result.

**Path Parameters:**

| Parameter | Description |
|-----------|-------------|
| `job_id` | The job ID returned by `POST /analyze` |

**Response (in progress):**

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "running",
  "progress": 0.55,
  "message": "Analysing voice authenticity"
}
```

**Response (completed):**

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "completed",
  "progress": 1.0,
  "result": { "...AnalysisResult..." }
}
```

**Response (failed):**

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "failed",
  "progress": 1.0,
  "message": "Analysis failed",
  "error": "Traceback..."
}
```

---

### `GET /analyze/results/{scan_id}`

Fetch the completed result of a previous analysis by its scan ID.

**Path Parameters:**

| Parameter | Description |
|-----------|-------------|
| `scan_id` | The scan ID from the analysis result |

**Response:** `AnalysisResult`

---

### `GET /analyze/history`

List recent scan analyses, ordered by most recent first.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Number of results (max 200) |

**Response:**

```json
[
  {
    "scan_id": "a1b2c3d4-...",
    "created_at": "2024-10-15T14:30:00+00:00",
    "status": "completed",
    "media_type": "audio",
    "original_filename": "suspicious_call.wav",
    "risk_level": "high",
    "risk_score": 87.5,
    "language": "en"
  }
]
```

---

## Family Safe-Voice Registry

### `POST /registry/members`

Register a trusted family member for voice verification.

**Request Body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Member's name (1–120 chars) |
| `relationship` | string \| null | No | e.g. "Mother", "Father" (max 60 chars) |
| `phone` | string \| null | No | Contact number (max 30 chars) |
| `note` | string \| null | No | Free-text note (max 1,000 chars) |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/registry/members \
  -H "Content-Type: application/json" \
  -d '{"name": "Maa", "relationship": "Mother", "phone": "+919876543210"}'
```

**Response:**

```json
{
  "id": "m1a2b3c4-...",
  "name": "Maa",
  "relationship": "Mother",
  "phone": "+919876543210",
  "note": null,
  "created_at": "2024-10-15T14:30:00+00:00",
  "enrollments_count": 0
}
```

---

### `GET /registry/members`

List all registered family members with their enrollment counts.

**Response:** Array of `FamilyMemberOut` objects.

---

### `DELETE /registry/members/{member_id}`

Remove a family member and all their enrolled voice samples.

**Path Parameters:**

| Parameter | Description |
|-----------|-------------|
| `member_id` | The member's UUID |

**Response:** `204 No Content`

---

### `POST /registry/members/{member_id}/enroll`

Enrol a voice sample for a family member. The audio is processed to extract a speaker embedding (52-D MFCC feature vector) for future verification.

**Request Body:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Voice sample (recording or voice note) |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/registry/members/m1a2b3c4/enroll \
  -F "file=@maa_voice_sample.wav"
```

**Response:**

```json
{
  "enrollment_id": "e1a2b3c4-...",
  "member_id": "m1a2b3c4-...",
  "created_at": "2024-10-15T14:35:00+00:00",
  "duration_seconds": 8.5
}
```

---

### `POST /registry/verify`

Verify a suspicious voice note against a registered family member's enrolled voice(s).

**Request Body:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `member_id` | string | Yes | The family member to verify against |
| `file` | file | Yes | The suspicious voice note |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/registry/verify \
  -F "member_id=m1a2b3c4-..." \
  -F "file=@suspicious_voice.wav"
```

**Response:**

```json
{
  "member_id": "m1a2b3c4-...",
  "member_name": "Maa",
  "match": true,
  "similarity": 0.78,
  "threshold": 0.42,
  "guidance": {
    "en": "Voice matches the enrolled sample for Maa.",
    "hi": "आवाज़ माँ के दर्ज नमूने से मेल खाती है।"
  }
}
```

If `match` is `false`, the voice likely does not belong to the registered family member and may be a deepfake clone.

---

## Schemas

### AnalysisResult

The full result of a completed analysis:

| Field | Type | Description |
|-------|------|-------------|
| `scan_id` | string | Unique scan identifier |
| `status` | string | Always `"completed"` |
| `media_type` | `"audio"` \| `"video"` \| `"text"` | Type of input |
| `original_filename` | string \| null | Original uploaded filename |
| `duration_seconds` | float \| null | Media duration |
| `language` | string \| null | Detected language code |
| `transcript` | string \| null | ASR-transcribed text |
| `risk` | RiskVerdict | Overall risk assessment |
| `signals` | object | Per-detector results |
| `red_flags` | RedFlag[] | Explainable fraud indicators |
| `next_steps` | NextStep[] | Recommended actions |
| `report` | ReportInfo | Official reporting channels |

### RiskVerdict

| Field | Type | Description |
|-------|------|-------------|
| `level` | `"low"` \| `"medium"` \| `"high"` | Risk classification |
| `score` | float | 0–100 risk percentage |
| `label` | LocalizedText | Human-readable label (EN + HI) |

### RedFlag

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier, e.g. `"voice-ai-likely"` |
| `category` | `"voice"` \| `"video"` \| `"text"` \| `"audio"` | Source detector |
| `severity` | `"info"` \| `"warning"` \| `"critical"` | How serious |
| `title` | LocalizedText | Short title |
| `detail` | LocalizedText | Full explanation |

### NextStep

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable identifier |
| `kind` | `"call"` \| `"visit"` \| `"verify"` \| `"report"` \| `"generic"` | Action type |
| `title` | LocalizedText | Short title |
| `detail` | LocalizedText | Full explanation |
| `href` | string \| null | Actionable link (e.g. `tel:1930`) |

### DetectorSignal

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Detector name |
| `status` | `"available"` \| `"unavailable"` \| `"error"` | Availability |
| `available` | bool | Whether the detector ran |
| `score` | float \| null | 0–1 likelihood of fraud signal |
| `label` | string \| null | Short classification label |
| `detail` | string \| null | Description |
| `metrics` | object | Detector-specific metrics |

### LocalizedText

```json
{ "en": "English text", "hi": "हिंदी पाठ" }
```

---

## Error Handling

All errors return a JSON body:

```json
{
  "error": "Error message",
  "code": "optional_error_code",
  "status_code": 400
}
```

Common HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 204 | Success (no content, for DELETE) |
| 400 | Bad request / validation error |
| 404 | Resource not found (job, scan, or member) |
| 413 | File too large |
| 422 | Unprocessable entity (invalid input) |
| 500 | Internal server error |

---

## Rate Limits & Concurrency

- Maximum concurrent analysis jobs: 2 (configurable via `max_concurrent_jobs`)
- Job timeout: 900 seconds (configurable via `job_timeout_seconds`)
- No rate limiting is applied by default; add a reverse proxy (nginx, Caddy) for production
