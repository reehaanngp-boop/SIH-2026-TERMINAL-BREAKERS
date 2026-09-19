/** API types mirroring backend/app/schemas/*.py */

export interface LocalizedText {
  en: string;
  hi: string;
}

export type RiskLevel = "low" | "medium" | "high";
export type MediaType = "audio" | "video" | "text";

export interface RiskVerdict {
  level: RiskLevel;
  score: number;
  label: LocalizedText;
}

export interface RedFlag {
  id: string;
  category: "voice" | "video" | "text" | "ai";
  severity: "info" | "warning" | "critical";
  title: LocalizedText;
  detail: LocalizedText;
}

export interface NextStep {
  id: string;
  kind: "call" | "visit" | "verify" | "report" | "generic";
  title: LocalizedText;
  detail: LocalizedText;
  href?: string | null;
}

export interface DetectorSignal {
  name: string;
  status: "available" | "unavailable" | "error";
  available: boolean;
  score: number | null;
  label: string | null;
  detail: string | null;
  metrics: Record<string, unknown>;
  engine?: string | null;
}

export interface ReportInfo {
  helpline: string;
  portal: string;
  i4c: string;
}

export interface AiVerdict {
  is_scam: boolean;
  confidence: number;
  scam_category?: string | null;
  key_indicators: string[];
  explanation?: LocalizedText | null;
}

export interface AiAnalysis {
  status: "ok" | "unavailable";
  model?: string | null;
  error?: string | null;
  verdict?: AiVerdict | null;
}

export interface AnalysisResult {
  scan_id: string;
  status: string;
  media_type: MediaType;
  original_filename?: string | null;
  duration_seconds?: number | null;
  language?: string | null;
  transcript?: string | null;
  risk: RiskVerdict;
  signals: Record<string, DetectorSignal>;
  red_flags: RedFlag[];
  next_steps: NextStep[];
  report: ReportInfo;
  ai_analysis?: AiAnalysis | null;
}

export interface JobCreated {
  job_id: string;
  status: string;
  detail?: string | null;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  message?: string | null;
  error?: string | null;
  result?: AnalysisResult;
}

export interface ScanListItem {
  scan_id: string;
  created_at: string;
  status: string;
  media_type: MediaType;
  original_filename?: string | null;
  risk_level?: string | null;
  risk_score?: number | null;
  language?: string | null;
}

export interface FamilyMember {
  id: string;
  name: string;
  relationship?: string | null;
  phone?: string | null;
  note?: string | null;
  created_at: string;
  enrollments_count: number;
}

export interface Enrollment {
  enrollment_id: string;
  member_id: string;
  created_at: string;
  duration_seconds?: number | null;
}

export interface VerifyResult {
  member_id: string;
  member_name: string;
  match: boolean;
  similarity: number;
  threshold: number;
  guidance: Record<string, LocalizedText>;
}

export interface MetaInfo {
  app: string;
  version: string;
  detectors: {
    asr: { name: string; available: boolean; description?: string };
    voice: { name: string; available: boolean; engine?: string };
    video: { name: string; available: boolean };
    text: { name: string; available: boolean };
    speaker?: { name: string; available: boolean; engine?: string };
    ai?: { name: string; available: boolean; engine?: string };
  };
  report: ReportInfo;
}

// ---------------------------------------------------------------------------
// Police suite (cases / evidence / people / voice / phone / analytics)
// ---------------------------------------------------------------------------
export type CaseStatus = "open" | "investigating" | "closed";
export type Priority = "low" | "normal" | "high" | "critical";

export interface AuthStatus {
  setup_required: boolean;
  authenticated: boolean;
  officer_name?: string | null;
}

export interface LoginResult {
  token: string;
  officer_name: string;
  expires_in_hours: number;
}

export interface EvidenceEvent {
  id: string;
  action: string;
  actor?: string | null;
  detail?: string | null;
  created_at: string;
}

export interface Evidence {
  id: string;
  case_id?: string | null;
  case_number?: string | null;
  filename: string;
  original_filename: string;
  media_type?: string | null;
  size_bytes?: number | null;
  sha256: string;
  scan_id?: string | null;
  risk_level?: string | null;
  risk_score?: number | null;
  uploaded_at: string;
  uploaded_by?: string | null;
  note?: string | null;
  events: EvidenceEvent[];
}

export interface EvidenceList {
  items: Evidence[];
  total: number;
}

export interface HashVerifyResult {
  evidence_id: string;
  matches: boolean;
  sha256: string;
  message: string;
}

export interface VoicePrint {
  id: string;
  label: string;
  owner_kind: string;
  owner_id: string;
  duration_seconds?: number | null;
  created_at: string;
}

export interface Person {
  id: string;
  name: string;
  role: string;
  phone?: string | null;
  id_type?: string | null;
  id_number?: string | null;
  address?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at?: string | null;
  case_ids: string[];
  voice_prints: VoicePrint[];
}

export interface VoicePrintCreateResult {
  voice_print_id: string;
  person_id: string;
  label: string;
  duration_seconds?: number | null;
  message: string;
}

export interface CaseListItem {
  id: string;
  case_number: string;
  title: string;
  status: CaseStatus;
  priority: Priority;
  officer_name?: string | null;
  victim_name?: string | null;
  suspect_name?: string | null;
  evidence_count: number;
  person_count: number;
  created_at: string;
}

export interface CaseDetail extends CaseListItem {
  description?: string | null;
  officer_badge?: string | null;
  victim_phone?: string | null;
  suspect_phone?: string | null;
  notes?: string | null;
  updated_at?: string | null;
  closed_at?: string | null;
  evidence: Evidence[];
  persons: Person[];
  events: EvidenceEvent[];
}

export interface CaseCreatePayload {
  title: string;
  description?: string | null;
  priority?: Priority;
  officer_name?: string | null;
  officer_badge?: string | null;
  victim_name?: string | null;
  victim_phone?: string | null;
  suspect_name?: string | null;
  suspect_phone?: string | null;
  notes?: string | null;
  scan_id?: string | null;
}

export interface PersonCreatePayload {
  name: string;
  role?: string;
  phone?: string | null;
  id_type?: string | null;
  id_number?: string | null;
  address?: string | null;
  notes?: string | null;
  case_ids?: string[];
}

export interface VoiceMatchItem {
  label: string;
  owner_kind: string;
  owner_id: string;
  owner_ref?: string | null;
  similarity: number;
  match: boolean;
}

export interface VoiceMatchResult {
  matches: VoiceMatchItem[];
  threshold: number;
  query_duration_seconds?: number | null;
}

export interface PhoneRecord {
  id: string;
  phone: string;
  status: string;
  count: number;
  first_seen: string;
  last_seen: string;
  notes?: string | null;
  linked_cases: string[];
}

export interface PhoneLookup {
  found: boolean;
  record?: PhoneRecord | null;
  message: string;
}

export interface StatCount {
  cases: number;
  evidence: number;
  scans: number;
  reported_numbers: number;
  high_risk_7d: number;
}

export interface AnalyticsStats {
  stats: StatCount;
  scam_categories: { category: string; count: number }[];
  risk_levels: { level: string; count: number }[];
  cases_by_status: { status: string; count: number }[];
  scans_last_14d: { date: string; count: number }[];
  recent_high_risk: {
    scan_id: string;
    created_at: string;
    media_type: string;
    original_filename?: string | null;
    risk_score?: number | null;
    transcript?: string | null;
  }[];
}

export interface AssistantChatMessage {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  model?: string;
  suggestions?: string[];
  error?: string | null;
}

export interface AssistantStatus {
  available: boolean;
  active_model: string;
  reason: string;
}

export interface QuickCheckResult {
  is_scam: boolean;
  scam_category: string;
  confidence: number;
  summary_en: string;
  summary_hi: string;
  urgency_level: "critical" | "high" | "medium" | "low";
  recommended_action: string;
}

export interface QuickCheckResponse {
  status: string;
  model: string;
  data: QuickCheckResult;
}

export interface DraftComplaintResponse {
  status: string;
  model: string;
  complaint_markdown: string;
}

export type NavKey =
  | "live-call"
  | "dashboard"
  | "analyze"
  | "media-auth"
  | "registry"
  | "blockchain"
  | "sdk"
  | "assistant"
  | "cases"
  | "evidence"
  | "voice-match"
  | "phone"
  | "history"
  | "settings";
