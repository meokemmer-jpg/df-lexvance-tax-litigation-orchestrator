# df-lexvance-tax-litigation-orchestrator [CRUX-MK]

**Welle:** 48 Track-A Wave-1 DC-1
**Status:** SKELETON-CONDITIONAL (NICHT laden vor Martin-Phronesis-Approval Welle-49)
**Coverage:** LexVance Gap-Cluster B (Steuerrecht + Steuerstreit)

## Scope

Tax-Litigation-Orchestrator fuer:
- **Einspruch** (§ 347 AO, Frist 30 Tage)
- **Klage FG** (§ 47 FGO, Frist 30 Tage)
- **Revision BFH** (§ 116 FGO, Frist 30 Tage)
- **EuGH-Vorlage** (Art. 267 AEUV)
- **DBA-Verstaendigungsverfahren** (Mutual Agreement)
- **BEPS Action 13** Verrechnungspreis-Check
- **Wegzugsbesteuerung** (K_0-DIREKT: Cape-Coral)
- **E-2-Visa-Steuer-Implikation**

Output: TaxLitigationResult mit Verfahrens-Status + naechster Frist + DBA-Refs.

## LexVance-Coverage-Mapping

| LexVance-Funktion | Vor Welle-48 | Nach Welle-48 |
|-------------------|---------------|----------------|
| Einspruchs-/Klage-Frist-Tracker | UNGEDECKT | df-lexvance-tax-litigation-orchestrator |
| BFH/EuGH-Verfahrens-Status | UNGEDECKT | df-lexvance-tax-litigation-orchestrator |
| DBA-Anwendung + Mutual Agreement | UNGEDECKT | df-lexvance-tax-litigation-orchestrator |
| BEPS-Verrechnungspreis | UNGEDECKT | df-lexvance-tax-litigation-orchestrator |
| Wegzugsbesteuerung Cape-Coral | UNGEDECKT | df-lexvance-tax-litigation-orchestrator (K_0-DIREKT) |

## Compliance

- K11-K16 voll (Cascade-Isolation, Distillation-Resistenz, Pre-Action-Verification, Override-Decay, Entropy, Mutex)
- LC1-LC5 voll (Lose-Coupling)
- Trinity-Pattern (Conservative/Aggressive/Contrarian via Frist-Kritikalitaet)
- Audit-Trail (rules/audit-trail.md §1)
- ENV-Var-gated Default-Disabled
- K_0-Sperr-Liste P6-1 (Wegzugsbesteuerung) PHRONESIS_TICKET Pflicht

## Activation

1. Martin-Phronesis-Approval (Welle-49 Pflicht, **K_0-DIREKT Cape-Coral**)
2. Cross-LLM-3OF3-Audit (Codex+Gemini+Copilot)
3. Tests passing: `python3 -m pytest tests/ -v`
4. Real-Mode: ENV `DF_LEXVANCE_TAX_REAL_ENABLED=true` + `PHRONESIS_TICKET=PT-...`

## STOP

`touch /tmp/df-lexvance-tax-litigation-orchestrator.stop` oder LaunchAgent unloaden.

## Welle-49+ Roadmap

- [ ] BFH-DB-Connector (Welle-49)
- [ ] DBA-Corpus-Loader (Welle-49)
- [ ] Verrechnungspreis-Calculator (Welle-50)
- [ ] Wegzugsbesteuerung-Modul Cape-Coral (Welle-50, K_0-DIREKT)
- [ ] Cross-LLM-3OF3-Audit-Verdict (Welle-49)

## rho

~200k EUR/J (Wegzugsbesteuerung K_0-DIREKT + BEPS-Verrechnungspreis + Fristen-Vermeidung).

[CRUX-MK]
