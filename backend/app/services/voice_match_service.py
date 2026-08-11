"""Cross-evidence voice matching: unknown clip vs all known voices on record."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Evidence, FamilyMember, Person, VoiceEnrollment, VoicePrint

settings = get_settings()


def match_voice(db: Session, audio) -> dict:
    """Rank every stored voice print/enrollment against the probe clip."""
    from app.detectors.audio.speaker_verify import (
        cosine_similarity,
        compute_embedding,
        embedding_engine,
    )

    try:
        probe = compute_embedding(audio)
    except ValueError as exc:
        return {"error": str(exc), "threshold": settings.verify_similarity_threshold,
                "matches": [], "query_duration_seconds": None, "engine": embedding_engine()}

    candidates: list[dict] = []
    names: dict[tuple[str, str], str] = {}  # (kind, owner_id) -> display ref

    for print_ in db.execute(select(VoicePrint)).scalars().unique().all():
        if print_.embedding:
            candidates.append({
                "label": print_.label,
                "owner_kind": print_.owner_kind,
                "owner_id": print_.owner_id,
                "embedding": print_.embedding,
                "duration": print_.duration_seconds,
            })

    for enroll in db.execute(select(VoiceEnrollment)).scalars().unique().all():
        if enroll.embedding:
            candidates.append({
                "label": enroll.member.name,
                "owner_kind": "family",
                "owner_id": enroll.member_id,
                "embedding": enroll.embedding,
                "duration": enroll.duration_seconds,
            })

    # Resolve display references for people and evidence owners.
    person_ids = [c["owner_id"] for c in candidates if c["owner_kind"] == "person"]
    evidence_ids = [c["owner_id"] for c in candidates if c["owner_kind"] == "evidence"]
    if person_ids:
        for p in db.execute(select(Person).where(Person.id.in_(person_ids))).scalars().unique().all():
            names[("person", p.id)] = f"Person: {p.name}"
    if evidence_ids:
        for e in db.execute(select(Evidence).where(Evidence.id.in_(evidence_ids))).scalars().unique().all():
            names[("evidence", e.id)] = f"Evidence: {e.original_filename}"

    results = []
    threshold = settings.verify_similarity_threshold
    expected = int(len(probe))
    skipped_legacy = 0
    for c in candidates:
        emb = c["embedding"]
        if len(emb) != expected:  # old-model embedding, not comparable
            skipped_legacy += 1
            continue
        sim = cosine_similarity(probe, emb)
        results.append({
            "label": c["label"],
            "owner_kind": c["owner_kind"],
            "owner_id": c["owner_id"],
            "owner_ref": names.get((c["owner_kind"], c["owner_id"])),
            "similarity": round(sim, 4),
            "match": sim >= threshold,
        })
    results.sort(key=lambda r: r["similarity"], reverse=True)

    return {
        "matches": results,
        "threshold": threshold,
        "engine": embedding_engine(),
        "skipped_legacy_embeddings": skipped_legacy,
        "query_duration_seconds": round(float(getattr(audio, "duration", 0.0)), 2),
    }
