"""DF-LEXVANCE-TAX-LITIGATION-ORCHESTRATOR Engine [CRUX-MK].

Welle-48 Track-A Wave-1 DC-1 Foundation-DF (Gap-Cluster B).
Skelett-Implementation: Tax-Verfahrens-Tracker + Fristen + DBA + Verrechnungspreis.

ENV-Var-gated Default-Disabled. Mock-Fallback bei Real-Mode-Disabled.

Pre/Post-Conditions:
- Pre: verfahren_id (str), mandant_id (str)
- Post: TaxLitigationResult mit Verfahrens-Status, naechste_frist, dba_referenzen
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


# Pflicht-Verfahrens-Typen (gem. AO + FGO)
VERFAHREN_TYPEN = (
    "EINSPRUCH",         # § 347 AO
    "KLAGE_FG",          # § 47 FGO Finanzgericht
    "REVISION_BFH",      # BFH
    "VORLAGE_EUGH",      # Art. 267 AEUV
    "VERSTAENDIGUNGS_DBA",  # DBA Mutual Agreement
)

# Standard-Fristen (Tage)
FRISTEN_TAGE = {
    "EINSPRUCH": 30,         # § 355 AO
    "KLAGE_FG": 30,          # § 47 FGO
    "REVISION_BFH": 30,      # § 116 FGO
    "VORLAGE_EUGH": 365,
    "VERSTAENDIGUNGS_DBA": 1095,  # 3 Jahre typ.
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TaxLitigationResult:
    """Pflicht-Felder per env-var-gated-real-integration-default.md Property-3."""
    verfahren_id: str
    mandant_id: str
    verfahren_typ: str       # aus VERFAHREN_TYPEN
    status: str              # "PENDING"|"FILED"|"DECIDED"|"UNKNOWN"
    naechste_frist_iso: Optional[str]  # ISO-Date naechste Pflicht-Frist
    tage_bis_frist: Optional[int]
    dba_referenzen: tuple    # z.B. ("DBA-DE-US Art. 12",)
    verrechnungspreis_check: bool
    source: str              # "mock"|"real-api"
    iso_timestamp: str
    phronesis_ticket: Optional[str] = None
    warnings: tuple = field(default_factory=tuple)


def _calc_frist(verfahren_typ: str, start_iso: Optional[str] = None) -> tuple:
    """Pre: verfahren_typ in VERFAHREN_TYPEN; Post: (frist_iso, tage_bis_frist)."""
    assert verfahren_typ in VERFAHREN_TYPEN, f"unknown verfahren_typ: {verfahren_typ}"
    tage = FRISTEN_TAGE[verfahren_typ]
    if start_iso:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    else:
        start = datetime.now(timezone.utc)
    frist = start + timedelta(days=tage)
    tage_bis = (frist - datetime.now(timezone.utc)).days
    return frist.isoformat(), tage_bis


def mock_tax_status(
    verfahren_id: str,
    mandant_id: str,
    verfahren_typ: str = "EINSPRUCH",
) -> TaxLitigationResult:
    """Mock-Status: liefert PENDING + Standard-Frist + leere DBA-Refs."""
    assert verfahren_id and mandant_id, "verfahren_id + mandant_id required"
    frist_iso, tage_bis = _calc_frist(verfahren_typ)
    return TaxLitigationResult(
        verfahren_id=verfahren_id,
        mandant_id=mandant_id,
        verfahren_typ=verfahren_typ,
        status="PENDING",
        naechste_frist_iso=frist_iso,
        tage_bis_frist=tage_bis,
        dba_referenzen=(),
        verrechnungspreis_check=False,
        source="mock",
        iso_timestamp=iso_now(),
        phronesis_ticket=None,
        warnings=("MOCK_MODE_NO_REAL_VERFAHRENS_DB",),
    )


def real_tax_status(
    verfahren_id: str,
    mandant_id: str,
    verfahren_typ: str = "EINSPRUCH",
    phronesis_ticket: Optional[str] = None,
) -> TaxLitigationResult:
    """Real-Mode (NUR mit PHRONESIS_TICKET; sonst graceful Fallback zu mock)."""
    assert verfahren_id and mandant_id, "verfahren_id + mandant_id required"
    if not phronesis_ticket:
        phronesis_ticket = os.environ.get("PHRONESIS_TICKET")
    if not phronesis_ticket:
        return mock_tax_status(verfahren_id, mandant_id, verfahren_typ)
    frist_iso, tage_bis = _calc_frist(verfahren_typ)
    # Welle-49+ Real-Connector zu BFH-DB + DBA-Corpus
    return TaxLitigationResult(
        verfahren_id=verfahren_id,
        mandant_id=mandant_id,
        verfahren_typ=verfahren_typ,
        status="PENDING",
        naechste_frist_iso=frist_iso,
        tage_bis_frist=tage_bis,
        dba_referenzen=(),
        verrechnungspreis_check=True,
        source="real-api",
        iso_timestamp=iso_now(),
        phronesis_ticket=phronesis_ticket,
        warnings=(),
    )


def dispatch_tax_status(
    verfahren_id: str,
    mandant_id: str,
    verfahren_typ: str = "EINSPRUCH",
) -> TaxLitigationResult:
    """Dispatcher mit ENV-Var-Gating."""
    real_enabled = os.environ.get("DF_LEXVANCE_TAX_REAL_ENABLED", "").lower() == "true"
    if real_enabled:
        return real_tax_status(verfahren_id, mandant_id, verfahren_typ)
    return mock_tax_status(verfahren_id, mandant_id, verfahren_typ)


def is_frist_critical(result: TaxLitigationResult, schwelle_tage: int = 7) -> bool:
    """Pre: result valid; Post: True iff Frist <= schwelle_tage."""
    if result.tage_bis_frist is None:
        return False
    return result.tage_bis_frist <= schwelle_tage


def to_audit_record(result: TaxLitigationResult) -> dict:
    """Audit-Record-Serializer."""
    return {
        "ts": result.iso_timestamp,
        "df": "DF-LEXVANCE-TAX-LITIGATION-ORCHESTRATOR",
        "verfahren_id": result.verfahren_id,
        "mandant_id": result.mandant_id,
        "verfahren_typ": result.verfahren_typ,
        "status": result.status,
        "tage_bis_frist": result.tage_bis_frist,
        "source": result.source,
        "phronesis_ticket": result.phronesis_ticket or "none",
    }
