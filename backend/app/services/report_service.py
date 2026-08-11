"""Formal PDF case report (reportlab) with evidence hash + chain of custody."""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Case, EvidenceEvent, Scan
from app.services import audit

settings = get_settings()


def _clean(text: str | None) -> str:
    if not text:
        return "—"
    return re.sub(r"\s+", " ", text).strip()


def _esc(text: str | None) -> str:
    """Escape XML special characters reportlab paragraphs need."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_case_report(db: Session, case: Case, actor: str | None = None) -> Path:
    """Render the case report to ``data/reports/`` and return the file path."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = settings.reports_dir / f"{case.case_number}.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"DigiRaksha Case Report {case.case_number}",
        author="DigiRaksha",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=18, leading=22, textColor=colors.HexColor("#0f766e"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, leading=16, textColor=colors.HexColor("#134e4a"), spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=13, alignment=TA_LEFT)
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#555555"))

    def _date(value) -> str:
        return value.strftime("%d %b %Y %H:%M UTC") if value else "—"

    story = [Paragraph(f"DigiRaksha — Police Case Report", h1), Spacer(1, 2)]

    # ---- Header block -------------------------------------------------------
    header = [
        ["Case Number", case.case_number],
        ["Title", _esc(case.title)],
        ["Status", case.status.title()],
        ["Priority", case.priority.title()],
        ["Officer", f"{_esc(case.officer_name or '—')}  ({_esc(case.officer_badge or 'no badge')})"],
        ["Opened", _date(case.created_at)],
        ["Last Updated", _date(case.updated_at)],
        ["Closed", _date(case.closed_at)],
    ]
    t = Table(header, colWidths=[34 * mm, None])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#334155")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t)

    if case.description:
        story += [Spacer(1, 4), Paragraph("Description", h2), Paragraph(_esc(case.description), body)]
    if case.notes:
        story += [Spacer(1, 4), Paragraph("Case Notes", h2), Paragraph(_esc(case.notes).replace("\n", "<br/>"), body)]

    # ---- Parties -------------------------------------------------------------
    victim = case.victim_name or case.victim_phone
    suspect = case.suspect_name or case.suspect_phone
    if victim or suspect:
        story += [Spacer(1, 4), Paragraph("Parties", h2)]
        party_rows = [["Role", "Name", "Phone"]]
        if victim:
            party_rows.append(["Victim", _esc(case.victim_name or "—"), _esc(case.victim_phone or "—")])
        if suspect:
            party_rows.append(["Suspect", _esc(case.suspect_name or "—"), _esc(case.suspect_phone or "—")])
        pt = Table(party_rows, colWidths=[26 * mm, None, None])
        pt.setStyle(_table_style())
        story.append(pt)

    persons = case.persons or []
    if persons:
        story += [Spacer(1, 4), Paragraph("Persons of Interest", h2)]
        p_rows = [["Name", "Role", "Phone", "ID"]]
        for p in persons:
            p_rows.append([_esc(p.name), _esc(p.role), _esc(p.phone), _esc(p.id_number)])
        pt = Table(p_rows, colWidths=[40 * mm, 24 * mm, 28 * mm, None])
        pt.setStyle(_table_style())
        story.append(pt)

    # ---- Evidence ------------------------------------------------------------
    evidence = case.evidence or []
    story += [Spacer(1, 6), Paragraph(f"Evidence Attached ({len(evidence)})", h2)]
    if not evidence:
        story.append(Paragraph("No evidence items attached to this case yet.", body))
    else:
        ev_rows = [["File", "Type", "Size", "Risk", "SHA-256"]]
        for e in evidence:
            scan = db.get(Scan, e.scan_id) if e.scan_id else None
            risk = f"{scan.risk_level.title() if scan and scan.risk_level else '—'}"
            if scan and scan.risk_score is not None:
                risk += f" ({scan.risk_score:.0f})"
            ev_rows.append([
                _esc(e.original_filename),
                _esc(e.media_type or "—"),
                _human_size(e.size_bytes),
                risk,
                f"<font size='7.5'>{_esc(e.sha256)}</font>",
            ])
        et = Table(ev_rows, colWidths=[42 * mm, 16 * mm, 16 * mm, 18 * mm, None])
        et.setStyle(_table_style())
        story.append(et)

        story.append(Spacer(1, 4))
        for e in evidence:
            scan = db.get(Scan, e.scan_id) if e.scan_id else None
            if not scan or not scan.result_json:
                continue
            result = scan.result_json
            flags = result.get("red_flags") or []
            steps = result.get("next_steps") or []
            story.append(Paragraph(f"Analysis — {_esc(e.original_filename)}", h2))
            risk = result.get("risk") or {}
            story.append(Paragraph(
                f"Risk level: <b>{risk.get('level', '—').upper()}</b> · score {risk.get('score', '—')} / 100",
                body,
            ))
            if flags:
                story.append(Paragraph("<b>Detected red flags:</b>", body))
                for f in flags:
                    title = (f.get("title") or {}).get("en", "")
                    story.append(Paragraph(f"• {_esc(title)} — severity: {f.get('severity', '')}", body))
            if steps:
                story.append(Paragraph("<b>Recommended next steps:</b>", body))
                for s in steps:
                    title = (s.get("title") or {}).get("en", "")
                    story.append(Paragraph(f"• {_esc(title)}", body))
            transcript = scan.transcript or (result.get("transcript") or "")
            if transcript:
                story.append(Paragraph("<b>Transcript excerpt:</b>", body))
                story.append(Paragraph(_esc(transcript[:1200]), small))

    # ---- Chain of custody ----------------------------------------------------
    evidence_ids = [e.id for e in evidence]
    events = (
        db.query(EvidenceEvent)
        .filter(
            (EvidenceEvent.case_id == case.id)
            | (EvidenceEvent.evidence_id.in_(evidence_ids) if evidence_ids else False)
        )
        .order_by(EvidenceEvent.created_at)
        .all()
    )
    story += [Spacer(1, 6), Paragraph("Chain of Custody / Audit Timeline", h2)]
    if not events:
        story.append(Paragraph("No audit events recorded.", body))
    else:
        ev_rows = [["When", "Action", "Actor", "Detail"]]
        for ev in events:
            ev_rows.append([_date(ev.created_at), _esc(ev.action), _esc(ev.actor), _esc(ev.detail)])
        et = Table(ev_rows, colWidths=[30 * mm, 24 * mm, 22 * mm, None])
        et.setStyle(_table_style())
        story.append(et)

    # ---- Footer --------------------------------------------------------------
    story += [Spacer(1, 12), Paragraph(
        "Generated by DigiRaksha. If you suspect cyber-fraud call <b>1930</b> or report at "
        "<b>https://cybercrime.gov.in</b>. This report is a case aid; its analysis is indicative "
        "and should be corroborated by standard investigation procedure.",
        small,
    )]

    doc.build(story)

    audit.log_event(db, action="report_exported", case_id=case.id, actor=actor,
                    detail=f"PDF report exported ({out_path.name})")
    db.commit()
    return out_path


def _table_style():
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    return TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _human_size(size: int | None) -> str:
    if not size:
        return "—"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"
