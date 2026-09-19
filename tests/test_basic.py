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


def test_adversarial_verfahren_typ_discrimination():
    """KERN-TEST: Diskriminierung unterschiedlicher Verfahrenstypen.
    MISSION: Beweise, dass unterschiedliche verfahren_typ-Eingaben
    unterschiedliche Fristen (Output) erzeugen."""
    result_einspruch = mock_tax_status("V-ADV-1", "M-ADV-1", "EINSPRUCH")
    result_revision = mock_tax_status("V-ADV-2", "M-ADV-2", "REVISION_BFH")
    result_vorlage = mock_tax_status("V-ADV-3", "M-ADV-3", "VORLAGE_EUGH")

    # Gegenteil: unterschiedliche verfahren_typ muessen unterschiedliche Fristen liefern
    assert result_einspruch.tage_bis_frist != result_revision.tage_bis_frist, \
        "EINSPRUCH und REVISION_BFH muessen unterschiedliche Fristen haben"
    assert result_einspruch.tage_bis_frist != result_vorlage.tage_bis_frist, \
        "EINSPRUCH und VORLAGE_EUGH muessen unterschiedliche Fristen haben"
    assert result_revision.tage_bis_frist != result_vorlage.tage_bis_frist, \
        "REVISION_BFH und VORLAGE_EUGH muessen unterschiedliche Fristen haben"

    # Zusaetzlich: gleicher Typ -> gleiche Frist (naeherungsweise, da Zeitabhaengigkeit)
    result_einspruch2 = mock_tax_status("V-ADV-4", "M-ADV-4", "EINSPRUCH")
    frist1 = result_einspruch.naechste_frist_iso[:10]  # nur Datum vergleichen
    frist2 = result_einspruch2.naechste_frist_iso[:10]
    # Da beide fast gleichzeitig aufgerufen, sollten die Fristen nahezu identisch sein
    # (max 1 Tag Differenz durch Ausfuehrungszeit)
    assert abs(result_einspruch.tage_bis_frist - result_einspruch2.tage_bis_frist) <= 1, \
        "Gleiche Verfahrenstypen sollten nahezu gleiche Fristen haben"


def test_adversarial_mandant_verfahren_discrimination():
    """KERN-TEST: Diskriminierung unterschiedlicher mandant_id/verfahren_id.
    Unterschiedliche IDs duerfen nicht zu identischen Ergebnissen fuehren
    (ausser Zufall bei gleichem Verfahrenstyp)."""
    result1 = mock_tax_status("V-100", "M-100", "KLAGE_FG")
    result2 = mock_tax_status("V-200", "M-200", "KLAGE_FG")

    # Unterschiedliche IDs -> unterschiedliche Objekte (auch wenn Felder aehnlich)
    assert result1 != result2, "Unterschiedliche IDs muessen unterschiedliche Resultate liefern"
    assert result1.verfahren_id != result2.verfahren_id, "verfahren_id muss unterschiedlich sein"
    assert result1.mandant_id != result2.mandant_id, "mandant_id muss unterschiedlich sein"


def test_adversarial_env_gating_discrimination(monkeypatch):
    """KERN-TEST: Diskriminierung durch ENV-Var-Gating.
    Mit vs. ohne DF_LEXVANCE_TAX_REAL_ENABLED=true muss unterschiedlicher source kommen."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("PHRONESIS_TICKET", "PT-ADV-TEST")

    # Ohne real-Modus
    result_mock = dispatch_tax_status("V-ADV-ENV1", "M-ADV-ENV1", "EINSPRUCH")
    assert result_mock.source == "mock", "Ohne env muss mock sein"

    # Mit real-Modus
    monkeypatch.setenv("DF_LEXVANCE_TAX_REAL_ENABLED", "true")
    result_real = dispatch_tax_status("V-ADV-ENV2", "M-ADV-ENV2", "EINSPRUCH")
    assert result_real.source == "real-api", "Mit env muss real-api sein"

    # Gegenteil: unterschiedliche source
    assert result_mock.source != result_real.source, "ENV-Gating muss unterschiedliche source erzeugen"


def test_adversarial_phronesis_ticket_discrimination(monkeypatch):
    """KERN-TEST: Diskriminierung durch Phronesis-Ticket-Praesenz.
    Mit vs. ohne Ticket -> unterschiedliches Verhalten (real-api vs. mock)."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("DF_LEXVANCE_TAX_REAL_ENABLED", "true")

    # Ohne Ticket: Fallback zu mock
    result_no_ticket = dispatch_tax_status("V-ADV-PT1", "M-ADV-PT1", "EINSPRUCH")
    assert result_no_ticket.source == "mock", "Ohne Ticket muss mock sein"

    # Mit Ticket: real-api
    monkeypatch.setenv("PHRONESIS_TICKET", "PT-ADV-REAL")
    result_with_ticket = dispatch_tax_status("V-ADV-PT2", "M-ADV-PT2", "EINSPRUCH")
    assert result_with_ticket.source == "real-api", "Mit Ticket muss real-api sein"

    # Gegenteil: unterschiedliche source
    assert result_no_ticket.source != result_with_ticket.source, \
        "Phronesis-Ticket-Praesenz muss unterschiedliche source erzeugen"

    # Zusaetzlich: unterschiedliche phronesis_ticket Werte
    assert result_with_ticket.phronesis_ticket == "PT-ADV-REAL"
    assert result_no_ticket.phronesis_ticket is None
