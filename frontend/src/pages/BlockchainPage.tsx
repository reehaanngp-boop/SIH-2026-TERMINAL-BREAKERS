import { useState, useEffect, type FormEvent } from "react";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { Modal } from "../components/Modal";
import { StatCard } from "../components/StatCard";

export function BlockchainPage() {
  const [ledger, setLedger] = useState<any[]>([]);
  const [stats, setStats] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchCertId, setSearchCertId] = useState("");
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [selectedBlock, setSelectedBlock] = useState<any | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const fetchLedger = async () => {
    setLoading(true);
    try {
      const [ledgerRes, statsRes] = await Promise.all([
        api.getBlockchainLedger(50),
        api.getBlockchainStats(),
      ]);
      setLedger(ledgerRes.blocks || []);
      setStats(statsRes);
    } catch (e: any) {
      console.error("Failed to fetch blockchain ledger:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, []);

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    if (!searchCertId.trim()) return;
    setVerifying(true);
    setVerificationResult(null);
    try {
      const res = await api.verifyBlockchainCertificate(searchCertId.trim());
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({
        valid: false,
        error: err?.message || "Certificate verification failed or certificate not found.",
      });
    } finally {
      setVerifying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const getVerdictTone = (verdict: string) => {
    if (!verdict) return "status";
    if (verdict.includes("CRITICAL") || verdict.includes("FRAUD")) return "high";
    if (verdict.includes("SUSPICIOUS") || verdict.includes("BORDERLINE")) return "medium";
    return "low";
  };

  const formatVerdictText = (verdict: string) => {
    if (!verdict) return "Unknown";
    return verdict.replace(/_/g, " ");
  };

  return (
    <div className="page">
      {/* Hero Banner */}
      <div className="hero-banner">
        <div className="hero-banner-content">
          <div className="hero-badge">
            <span className="pulse-dot" />
            <span>Theme: Blockchain & Cybersecurity · Problem Statement 26104</span>
          </div>
          <h1 className="hero-title">Blockchain Voice Integrity Ledger</h1>
          <p className="hero-sub">
            Tamper-proof, cryptographically signed audit trail of telephony & VoIP authentications. Admissible under Bharatiya Sakshya Adhiniyam 2023 / Section 65B Indian IT Act.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchLedger}
          disabled={loading}
          className="btn btn-secondary"
          style={{ padding: "9px 16px" }}
        >
          <span>🔄</span> {loading ? "Refreshing..." : "Refresh Ledger"}
        </button>
      </div>

      {/* KPI Stats Cards */}
      {stats && (
        <div className="grid grid-4" style={{ marginBottom: 20 }}>
          <StatCard
            label="Total Blocks"
            value={stats.total_blocks}
            hint="Genesis + Verified Sessions"
            accent
          />
          <StatCard
            label="Verified Calls"
            value={stats.total_verified_calls}
            hint="Signed with SHA-256 Merkle Root"
          />
          <StatCard
            label="Fraud Calls Intercepted"
            value={stats.fraud_attacks_intercepted}
            hint="Synthetic Vocoders Blocked"
            alert={stats.fraud_attacks_intercepted > 0}
          />
          <div className="stat">
            <div className="stat-label">Chain Integrity</div>
            <div className="stat-value" style={{ fontSize: 20, color: "var(--low)", display: "flex", alignItems: "center", gap: 6 }}>
              <span>🛡️</span> {stats.chain_integrity}
            </div>
            <div className="stat-hint mono-xs" style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
              {stats.last_block_hash?.slice(0, 18)}...
            </div>
          </div>
        </div>
      )}

      {/* Certificate Verifier Bar */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span>🔍</span> Verify Voice Integrity Certificate (Public Forensic Validator)
        </div>
        <div className="card-sub">
          Verify digital signatures and Merkle integrity for court-admissible forensic certificates
        </div>

        <form onSubmit={handleVerify} style={{ display: "flex", gap: 10, marginTop: 14, flexWrap: "wrap" }}>
          <input
            type="text"
            value={searchCertId}
            onChange={(e) => setSearchCertId(e.target.value)}
            placeholder="Paste Certificate ID (e.g. DR-VOICE-CERT-20260916-...)"
            className="input"
            style={{ flex: "1 1 320px", fontFamily: "var(--mono)" }}
          />
          <button
            type="submit"
            disabled={verifying}
            className="btn btn-primary"
            style={{ padding: "9px 20px" }}
          >
            {verifying ? "Validating Cryptography..." : "Verify Certificate"}
          </button>
        </form>

        {/* Quick Example Chips */}
        {ledger.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            <span className="small faint">Quick Test:</span>
            {ledger.slice(0, 3).map((b, i) => (
              <button
                key={i}
                type="button"
                className="link small mono-xs"
                style={{
                  background: "var(--elevated)",
                  padding: "3px 8px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--line-soft)"
                }}
                onClick={() => setSearchCertId(b.certificate_id)}
              >
                {b.certificate_id} ({b.claimed_identity})
              </button>
            ))}
          </div>
        )}

        {/* Verification Result Card */}
        {verificationResult && (
          <div
            style={{
              marginTop: 16,
              padding: "16px",
              borderRadius: "var(--radius-sm)",
              border: `1px solid ${verificationResult.valid ? "rgba(52, 211, 153, 0.35)" : "rgba(248, 113, 113, 0.35)"}`,
              background: verificationResult.valid ? "var(--low-soft)" : "var(--high-soft)"
            }}
          >
            {verificationResult.valid ? (
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, fontSize: 14, color: "var(--low)" }}>
                  <span>✅</span> CERTIFICATE VERIFIED & UNTAMPERED IN BLOCKCHAIN
                </div>
                <p style={{ margin: "6px 0 12px", fontSize: 13, color: "var(--ink)" }}>
                  Certificate <strong className="mono">{verificationResult.certificate_id}</strong> matched block #{verificationResult.block?.block_index}. Cryptographic Merkle chain and HMAC-SHA256 signature are valid.
                </p>
                <div className="grid grid-4" style={{ gap: 8 }}>
                  <div style={{ background: "var(--bg)", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--line)" }}>
                    <span className="small faint" style={{ display: "block" }}>Caller Number</span>
                    <strong style={{ fontSize: 13 }}>{verificationResult.block?.caller_id}</strong>
                  </div>
                  <div style={{ background: "var(--bg)", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--line)" }}>
                    <span className="small faint" style={{ display: "block" }}>Claimed Identity</span>
                    <strong style={{ fontSize: 13 }}>{verificationResult.block?.claimed_identity}</strong>
                  </div>
                  <div style={{ background: "var(--bg)", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--line)" }}>
                    <span className="small faint" style={{ display: "block" }}>Forensic Verdict</span>
                    <Badge tone={getVerdictTone(verificationResult.block?.verdict)}>
                      {formatVerdictText(verificationResult.block?.verdict)}
                    </Badge>
                  </div>
                  <div style={{ background: "var(--bg)", padding: "8px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--line)" }}>
                    <span className="small faint" style={{ display: "block" }}>Legal Validity</span>
                    <strong style={{ fontSize: 12, color: "var(--low)" }}>Sec 65B Admissible</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: "var(--high)", fontSize: 13 }}>
                <strong>❌ Verification Failed:</strong> {verificationResult.error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Block Explorer Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10
        }}>
          <div>
            <div className="card-title" style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
              <span>⛓️</span> Immutable Block Ledger
            </div>
            <div className="card-sub">Chronological chain of custody anchored on local SHA-256 Merkle ledger</div>
          </div>
          <span className="mono-xs faint">Latest 50 blocks</span>
        </div>

        {loading ? (
          <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)" }}>
            <div className="spinner" style={{ margin: "0 auto 10px" }} />
            <p>Loading cryptographic audit ledger...</p>
          </div>
        ) : ledger.length === 0 ? (
          <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--muted)" }}>
            No forensic blocks recorded in ledger yet.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th style={{ width: 80 }}>Block</th>
                  <th>Timestamp (Local)</th>
                  <th>Certificate ID</th>
                  <th>Caller ID</th>
                  <th>Claimed Identity</th>
                  <th style={{ width: 90 }}>Risk</th>
                  <th>Verdict</th>
                  <th style={{ textAlign: "right", width: 110 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((block: any) => (
                  <tr key={block.block_index}>
                    <td className="mono-xs" style={{ fontWeight: 700, color: "var(--brand)" }}>
                      #{block.block_index}
                    </td>
                    <td className="mono-xs faint">
                      {block.timestamp ? new Date(block.timestamp).toLocaleString() : "Genesis"}
                    </td>
                    <td className="mono-xs" style={{ color: "var(--brand)" }}>
                      {block.certificate_id}
                    </td>
                    <td className="mono-xs">{block.caller_id}</td>
                    <td style={{ fontWeight: 600, color: "var(--ink)" }}>
                      {block.claimed_identity}
                    </td>
                    <td className="tnum">
                      <strong style={{
                        color: block.impersonation_risk_score >= 0.5 ? "var(--high)" : block.impersonation_risk_score >= 0.28 ? "var(--medium)" : "var(--low)"
                      }}>
                        {(block.impersonation_risk_score * 100).toFixed(0)}%
                      </strong>
                    </td>
                    <td>
                      <Badge tone={getVerdictTone(block.verdict)}>
                        {formatVerdictText(block.verdict)}
                      </Badge>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        type="button"
                        onClick={() => setSelectedBlock(block)}
                        className="btn btn-sm btn-secondary"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Block Inspector Modal */}
      {selectedBlock && (
        <Modal
          title={`Forensic Block #${selectedBlock.block_index}`}
          onClose={() => setSelectedBlock(null)}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
              <div>
                <span className="small faint" style={{ display: "block" }}>Certificate Identifier</span>
                <strong className="mono" style={{ color: "var(--brand)", fontSize: 13 }}>
                  {selectedBlock.certificate_id}
                </strong>
              </div>
              <Badge tone={getVerdictTone(selectedBlock.verdict)}>
                {formatVerdictText(selectedBlock.verdict)}
              </Badge>
            </div>

            <div style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span className="small faint">SHA-256 Block Hash</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(selectedBlock.block_hash)}
                  className="link small mono-xs"
                >
                  {copiedHash === selectedBlock.block_hash ? "✓ Copied" : "Copy"}
                </button>
              </div>
              <div className="mono-xs" style={{ wordBreak: "break-all", color: "var(--brand)" }}>
                {selectedBlock.block_hash}
              </div>
            </div>

            <div style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span className="small faint">Previous Block Hash</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(selectedBlock.previous_hash)}
                  className="link small mono-xs"
                >
                  {copiedHash === selectedBlock.previous_hash ? "✓ Copied" : "Copy"}
                </button>
              </div>
              <div className="mono-xs faint" style={{ wordBreak: "break-all" }}>
                {selectedBlock.previous_hash}
              </div>
            </div>

            <div className="grid grid-2" style={{ gap: 10 }}>
              <div style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
                <span className="small faint" style={{ display: "block" }}>Merkle Root</span>
                <span className="mono-xs" style={{ wordBreak: "break-all" }}>{selectedBlock.merkle_root}</span>
              </div>
              <div style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
                <span className="small faint" style={{ display: "block" }}>HMAC Signature</span>
                <span className="mono-xs" style={{ wordBreak: "break-all", color: "var(--medium)" }}>{selectedBlock.signature}</span>
              </div>
            </div>

            <div style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "10px 12px" }}>
              <span className="small faint" style={{ display: "block", marginBottom: 4 }}>Raw Merkle Block Payload</span>
              <pre className="mono-xs" style={{ margin: 0, maxHeight: 160, overflowY: "auto", whiteSpace: "pre-wrap", color: "var(--muted)" }}>
                {JSON.stringify(selectedBlock, null, 2)}
              </pre>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
              <button
                type="button"
                onClick={() => setSelectedBlock(null)}
                className="btn btn-secondary"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
