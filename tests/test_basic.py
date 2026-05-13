"""Basic Tests fuer DF-LEXVANCE-TAX-LITIGATION-ORCHESTRATOR [CRUX-MK]."""
from __future__ import annotations

import os
import sys
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.engine import (
    VERFAHREN_TYPEN, FRISTEN_TAGE,
    TaxLitigationResult,
    mock_tax_status, real_tax_status, dispatch_tax_status,
    is_frist_critical, to_audit_record, _calc_frist,
)


def _clear_env(monkeypatch):
    monkeypatch.delenv("DF_LEXVANCE_TAX_REAL_ENABLED", raising=False)
    monkeypatch.delenv("PHRONESIS_TICKET", raising=False)


def test_default_mock_no_env(monkeypatch):
    _clear_env(monkeypatch)
    result = dispatch_tax_status("V-001", "M-001")
    assert result.source == "mock"
    assert result.status == "PENDING"
    assert result.phronesis_ticket is None
    assert "MOCK_MODE_NO_REAL_VERFAHRENS_DB" in result.warnings


def test_env_true_with_phronesis_ticket(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("DF_LEXVANCE_TAX_REAL_ENABLED", "true")
    monkeypatch.setenv("PHRONESIS_TICKET", "PT-W48-TAX-001")
    result = dispatch_tax_status("V-002", "M-002")
    assert result.source == "real-api"
    assert result.phronesis_ticket == "PT-W48-TAX-001"


def test_env_true_without_phronesis_fallback(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("DF_LEXVANCE_TAX_REAL_ENABLED", "true")
    result = dispatch_tax_status("V-003", "M-003")
    assert result.source == "mock", "PHRONESIS-Missing muss graceful fallback ausloesen"


def test_frist_einspruch_30_tage():
    """§ 355 AO: Einspruch-Frist 30 Tage."""
    frist_iso, tage_bis = _calc_frist("EINSPRUCH")
    # 29 oder 30, je nach Mikrosekunden-Drift
    assert tage_bis in (29, 30), f"expected ~30 days, got {tage_bis}"
    assert frist_iso  # ISO-Format


def test_unknown_verfahren_typ_raises():
    with pytest.raises(AssertionError):
        _calc_frist("UNKNOWN_TYPE")


def test_is_frist_critical():
    """Fristen-Kritikalitaet: <=7 Tage = critical."""
    result_crit = TaxLitigationResult(
        verfahren_id="x", mandant_id="m", verfahren_typ="EINSPRUCH",
        status="PENDING", naechste_frist_iso="2026-05-13", tage_bis_frist=2,
        dba_referenzen=(), verrechnungspreis_check=False,
        source="mock", iso_timestamp="2026-05-11T12:00:00+00:00",
    )
    result_ok = TaxLitigationResult(
        verfahren_id="x", mandant_id="m", verfahren_typ="EINSPRUCH",
        status="PENDING", naechste_frist_iso="2026-06-11", tage_bis_frist=30,
        dba_referenzen=(), verrechnungspreis_check=False,
        source="mock", iso_timestamp="2026-05-11T12:00:00+00:00",
    )
    assert is_frist_critical(result_crit)
    assert not is_frist_critical(result_ok)


def test_conservation_all_verfahren_typen():
    """Conservation: alle 5 Pflicht-Verfahrens-Typen haben Fristen-Eintrag."""
    for typ in VERFAHREN_TYPEN:
        assert typ in FRISTEN_TAGE, f"Frist fehlt fuer {typ}"
    assert len(VERFAHREN_TYPEN) == 5


def test_audit_record_format():
    result = mock_tax_status("V-AUD", "M-AUD")
    rec = to_audit_record(result)
    assert {"ts", "df", "verfahren_id", "mandant_id", "verfahren_typ", "status", "tage_bis_frist", "source"} <= set(rec.keys())
    assert rec["df"] == "DF-LEXVANCE-TAX-LITIGATION-ORCHESTRATOR"
