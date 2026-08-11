/** Thin typed client for the DigiRaksha REST API (attaches the PIN session token). */
import type {
  AnalyticsStats,
  AuthStatus,
  CaseCreatePayload,
  CaseDetail,
  CaseListItem,
  Evidence,
  EvidenceList,
  FamilyMember,
  HashVerifyResult,
  JobCreated,
  JobStatus,
  LoginResult,
  MetaInfo,
  Person,
  PersonCreatePayload,
  PhoneLookup,
  PhoneRecord,
  ScanListItem,
  VerifyResult,
  VoiceMatchResult,
  VoicePrintCreateResult,
} from "./types";

const API = "/api/v1";
const TOKEN_KEY = "digiraksha.token";

let token: string | null = localStorage.getItem(TOKEN_KEY);
let onUnauthorized: (() => void) | null = null;

export function getAuthToken(): string | null {
  return token;
}

export function setAuthToken(t: string | null): void {
  token = t;
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

/** Register a handler invoked when any request returns 401 (session expired). */
export function onAuthError(fn: () => void): void {
  onUnauthorized = fn;
}

function parseError(res: Response, body: unknown): string {
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;
    const err = obj.error as Record<string, unknown> | undefined;
    if (err && typeof err.message === "string") return err.message;
    if (typeof obj.detail === "string") return obj.detail;
    if (typeof obj.message === "string") return obj.message;
  }
  return res.statusText || `Request failed (${res.status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    if (res.status === 401 && onUnauthorized) onUnauthorized();
    const text = await res.text().catch(() => "");
    let body: unknown = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = text;
    }
    throw new Error(parseError(res, body));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function download(path: string): Promise<Blob> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API}${path}`, { headers });
  if (!res.ok) {
    if (res.status === 401 && onUnauthorized) onUnauthorized();
    throw new Error(`Download failed (${res.status})`);
  }
  return res.blob();
}

export const api = {
  // -- access control -----------------------------------------------------
  authStatus(): Promise<AuthStatus> {
    return request("/auth/status");
  },
  authSetup(officerName: string, pin: string): Promise<LoginResult> {
    return request("/auth/setup", {
      method: "POST",
      body: JSON.stringify({ officer_name: officerName, pin }),
    });
  },
  authLogin(pin: string): Promise<LoginResult> {
    return request("/auth/login", { method: "POST", body: JSON.stringify({ pin }) });
  },
  authLogout(): Promise<void> {
    return request("/auth/logout", { method: "POST" });
  },
  authChangePin(currentPin: string, newPin: string): Promise<void> {
    return request("/auth/change-pin", {
      method: "POST",
      body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
    });
  },

  // -- analysis (consumer, no auth required) -------------------------------
  analyzeTranscript(text: string, languageHint?: string): Promise<import("./types").AnalysisResult> {
    return request("/analyze/transcript", {
      method: "POST",
      body: JSON.stringify({ text, language_hint: languageHint || null }),
    });
  },

  uploadMedia(file: File): Promise<JobCreated> {
    const form = new FormData();
    form.append("file", file);
    return request("/analyze", { method: "POST", body: form });
  },

  getJob(jobId: string): Promise<JobStatus> {
    return request(`/analyze/jobs/${jobId}`);
  },

  getResult(scanId: string): Promise<import("./types").AnalysisResult> {
    return request(`/analyze/results/${scanId}`);
  },

  getHistory(limit = 50): Promise<ScanListItem[]> {
    return request(`/analyze/history?limit=${limit}`);
  },

  getMeta(): Promise<MetaInfo> {
    return request("/meta");
  },

  // -- family safe-voice registry ------------------------------------------
  listMembers(): Promise<FamilyMember[]> {
    return request("/registry/members");
  },
  createMember(data: { name: string; relationship?: string; phone?: string; note?: string }): Promise<FamilyMember> {
    return request("/registry/members", { method: "POST", body: JSON.stringify(data) });
  },
  deleteMember(id: string): Promise<void> {
    return request(`/registry/members/${id}`, { method: "DELETE" });
  },
  enrollMember(memberId: string, file: File): Promise<import("./types").Enrollment> {
    const form = new FormData();
    form.append("file", file);
    return request(`/registry/members/${memberId}/enroll`, { method: "POST", body: form });
  },
  verifyVoice(memberId: string, file: File, claimedName?: string): Promise<VerifyResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("member_id", memberId);
    if (claimedName) form.append("claimed_name", claimedName);
    return request("/registry/verify", { method: "POST", body: form });
  },

  // -- cases ---------------------------------------------------------------
  listCases(params?: { search?: string; status?: string }): Promise<CaseListItem[]> {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.status) q.set("status", params.status);
    const s = q.toString();
    return request(`/cases${s ? `?${s}` : ""}`);
  },
  createCase(data: CaseCreatePayload): Promise<CaseDetail> {
    return request("/cases", { method: "POST", body: JSON.stringify(data) });
  },
  getCase(id: string): Promise<CaseDetail> {
    return request(`/cases/${id}`);
  },
  updateCase(id: string, data: Partial<CaseCreatePayload>): Promise<CaseDetail> {
    return request(`/cases/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  },
  deleteCase(id: string): Promise<void> {
    return request(`/cases/${id}`, { method: "DELETE" });
  },
  setCaseStatus(id: string, status: string): Promise<CaseDetail> {
    return request(`/cases/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
  },
  addCaseNote(id: string, note: string): Promise<CaseDetail> {
    return request(`/cases/${id}/notes`, { method: "POST", body: JSON.stringify({ note }) });
  },
  linkEvidenceToCase(caseId: string, evidenceId: string): Promise<CaseDetail> {
    return request(`/cases/${caseId}/evidence/${evidenceId}`, { method: "POST" });
  },
  unlinkEvidenceFromCase(caseId: string, evidenceId: string): Promise<CaseDetail> {
    return request(`/cases/${caseId}/evidence/${evidenceId}`, { method: "DELETE" });
  },
  linkPersonToCase(caseId: string, personId: string): Promise<CaseDetail> {
    return request(`/cases/${caseId}/persons/${personId}`, { method: "POST" });
  },
  attachScanToCase(caseId: string, scanId: string): Promise<CaseDetail> {
    return request(`/cases/${caseId}/attach-scan/${scanId}`, { method: "POST" });
  },
  unlinkPersonFromCase(caseId: string, personId: string): Promise<CaseDetail> {
    return request(`/cases/${caseId}/persons/${personId}`, { method: "DELETE" });
  },

  // -- evidence vault ------------------------------------------------------
  uploadEvidence(file: File, caseId?: string, note?: string): Promise<Evidence> {
    const form = new FormData();
    form.append("file", file);
    if (caseId) form.append("case_id", caseId);
    if (note) form.append("note", note);
    return request("/evidence", { method: "POST", body: form });
  },
  listEvidence(params?: { search?: string; media_type?: string; risk_level?: string; case_id?: string }): Promise<EvidenceList> {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.media_type) q.set("media_type", params.media_type);
    if (params?.risk_level) q.set("risk_level", params.risk_level);
    if (params?.case_id) q.set("case_id", params.case_id);
    const s = q.toString();
    return request(`/evidence${s ? `?${s}` : ""}`);
  },
  getEvidence(id: string): Promise<Evidence> {
    return request(`/evidence/${id}`);
  },
  verifyEvidence(id: string): Promise<HashVerifyResult> {
    return request(`/evidence/${id}/verify`);
  },
  updateEvidenceNote(id: string, note: string): Promise<Evidence> {
    return request(`/evidence/${id}/note`, { method: "PATCH", body: JSON.stringify({ note }) });
  },
  linkEvidence(id: string, caseId: string): Promise<Evidence> {
    return request(`/evidence/${id}/link`, { method: "PATCH", body: JSON.stringify({ case_id: caseId }) });
  },
  unlinkEvidence(id: string): Promise<Evidence> {
    return request(`/evidence/${id}/link`, { method: "DELETE" });
  },
  deleteEvidence(id: string): Promise<void> {
    return request(`/evidence/${id}`, { method: "DELETE" });
  },
  downloadEvidence(id: string): Promise<Blob> {
    return download(`/evidence/${id}/download`);
  },

  // -- people --------------------------------------------------------------
  listPeople(params?: { search?: string; role?: string }): Promise<Person[]> {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.role) q.set("role", params.role);
    const s = q.toString();
    return request(`/people${s ? `?${s}` : ""}`);
  },
  createPerson(data: PersonCreatePayload): Promise<Person> {
    return request("/people", { method: "POST", body: JSON.stringify(data) });
  },
  getPerson(id: string): Promise<Person> {
    return request(`/people/${id}`);
  },
  updatePerson(id: string, data: Partial<PersonCreatePayload>): Promise<Person> {
    return request(`/people/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  },
  deletePerson(id: string): Promise<void> {
    return request(`/people/${id}`, { method: "DELETE" });
  },
  enrollPersonVoice(personId: string, file: File): Promise<VoicePrintCreateResult> {
    const form = new FormData();
    form.append("file", file);
    return request(`/people/${personId}/enroll-voice`, { method: "POST", body: form });
  },
  linkPerson(personId: string, caseId: string): Promise<Person> {
    return request(`/people/${personId}/link`, { method: "POST", body: JSON.stringify({ case_id: caseId }) });
  },
  unlinkPerson(personId: string, caseId: string): Promise<Person> {
    return request(`/people/${personId}/link`, { method: "DELETE", body: JSON.stringify({ case_id: caseId }) });
  },

  // -- voice matching ------------------------------------------------------
  voiceMatch(file: File): Promise<VoiceMatchResult> {
    const form = new FormData();
    form.append("file", file);
    return request("/voice-match", { method: "POST", body: form });
  },

  // -- phone intelligence --------------------------------------------------
  listReportedNumbers(): Promise<PhoneRecord[]> {
    return request("/phone");
  },
  lookupPhone(number: string): Promise<PhoneLookup> {
    return request(`/phone/${encodeURIComponent(number)}`);
  },
  reportPhone(phone: string, notes?: string): Promise<PhoneRecord> {
    return request("/phone/report", { method: "POST", body: JSON.stringify({ phone, notes: notes || null }) });
  },
  setPhoneStatus(id: string, status: string): Promise<PhoneRecord> {
    return request(`/phone/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
  },

  // -- analytics / export / reports ----------------------------------------
  getAnalytics(): Promise<AnalyticsStats> {
    return request("/analytics");
  },
  caseReportPdf(caseId: string): Promise<Blob> {
    return download(`/reports/${caseId}/pdf`);
  },
  exportCases(): Promise<Blob> {
    return download("/export/cases");
  },
  exportScans(): Promise<Blob> {
    return download("/export/scans");
  },
};
