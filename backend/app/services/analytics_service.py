"""Dashboard analytics: aggregate counts over cases, evidence and scans."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Case, Evidence, ReportedNumber, Scan


def get_stats(db: Session) -> dict:
    scans = list(db.execute(select(Scan)).scalars().all())
    cases = list(db.execute(select(Case)).scalars().all())

    high_risk_7d = 0
    # SQLite returns naive datetimes, so work in naive UTC throughout.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=7)

    category_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    scans_by_day: dict[str, int] = {}

    for scan in scans:
        level = scan.risk_level or "unknown"
        risk_counts[level] = risk_counts.get(level, 0) + 1

        created = scan.created_at
        if created and created >= cutoff and level == "high":
            high_risk_7d += 1
        if created:
            day = created.strftime("%Y-%m-%d")
            scans_by_day[day] = scans_by_day.get(day, 0) + 1

        result = scan.result_json or {}
        text_signal = (result.get("signals") or {}).get("text") or {}
        label = text_signal.get("label")
        if label and label not in {"benign", "uncertain", "unavailable", None}:
            category_counts[label] = category_counts.get(label, 0) + 1

    status_counts: dict[str, int] = {}
    for case in cases:
        status_counts[case.status] = status_counts.get(case.status, 0) + 1

    # Build the 14-day series with zero-fill for missing days.
    day_series: list[dict] = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        day_series.append({"date": day, "count": scans_by_day.get(day, 0)})

    recent = sorted(
        (s for s in scans if s.risk_level == "high"),
        key=lambda s: (s.created_at or datetime.min, s.id),
        reverse=True,
    )[:8]
    recent_out = [
        {
            "scan_id": s.id,
            "created_at": s.created_at.isoformat() if s.created_at else "",
            "media_type": s.media_type,
            "original_filename": s.original_filename,
            "risk_score": s.risk_score,
            "transcript": (s.transcript or "")[:160],
        }
        for s in recent
    ]

    return {
        "stats": {
            "cases": len(cases),
            "evidence": db.execute(select(func.count()).select_from(Evidence)).scalar() or 0,
            "scans": len(scans),
            "reported_numbers": db.execute(select(func.count()).select_from(ReportedNumber)).scalar() or 0,
            "high_risk_7d": high_risk_7d,
        },
        "scam_categories": [{"category": k, "count": v} for k, v in sorted(category_counts.items(), key=lambda kv: -kv[1])],
        "risk_levels": [{"level": k, "count": v} for k, v in sorted(risk_counts.items())],
        "cases_by_status": [{"status": k, "count": v} for k, v in status_counts.items()],
        "scans_last_14d": day_series,
        "recent_high_risk": recent_out,
    }
