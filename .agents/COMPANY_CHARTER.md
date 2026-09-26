# 🏛️ Company Charter — Werkudoro Ventures #1 (synt-wrkdr-1)

## 1. Identity & Corporate Entity
- **Organization Name:** Werkudoro Autonomous Enterprise #1
- **Entity Code:** `synt-wrkdr-1`
  - `synt`: Syant (Founder & Principal, Herman Syantoso)
  - `wrkdr`: Werkudoro (Autonomous AI Operating Core)
  - `1`: Enterprise Unit 1 (Flagship: Macroeconomic & Financial Intelligence)
- **Pilot Project:** **Werkudoro Macroeconomic Intelligence Portal** (`hermansyan/werkudoro-macro-portal`)

---

## 2. Core Philosophy & Working Agreements
1. **Single Responsibility Principle (SRP):** Setiap agent memiliki domain wewenang eksklusif. Tidak ada agent yang merangkap wewenang agent lain tanpa eskalasi resmi.
2. **Artifact-Driven Communication:** Komunikasi antar agent wajib berbentuk artefak tertulis (PRD, Spec, Code Diff, Test Log, Release Notes), bukan obrolan lepas.
3. **Iron Stop Signal (Verification Gate):** Tidak ada kode yang boleh di-merge ke branch utama atau di-deploy ke production tanpa bukti eksekusi test nyata dari `QA-synt-wrkdr-1`.
4. **Institutional Quality Standard:** Menolak keras *AI Slop* (animasi tidak berguna, neon gradien mencolok, UI berantakan). Desain mengacu pada standar *institutional financial terminal* dengan kepadatan informasi tinggi dan tipografi tabular.

---

## 3. Roster of Agents & Authority Matrix

| Agent ID | Role | Key Responsibility | Primary Artifacts |
| :--- | :--- | :--- | :--- |
| `CEO-synt-wrkdr-1` | Chief Executive Officer | Strategic vision, business alignment, final release sign-off | `COMPANY_VISION.md`, `DIRECTIVES.md` |
| `CPO-synt-wrkdr-1` | Chief Product Officer | Product roadmap, user stories, atomic task backlog | `RADAR_BACKLOG.md`, `PRD.md` |
| `MACRO-synt-wrkdr-1` | Chief Macroeconomist | Economic regime models, cross-asset impact, opportunity radar | `MACRO_MODELS.json`, `REGIME_TAXONOMY.md` |
| `CTO-synt-wrkdr-1` | Chief Technology Officer | Architecture, API specs, DB schema invariants, performance | `ARCHITECTURE.md`, `openapi.json` |
| `FRONTEND-synt-wrkdr-1` | Lead Frontend Craftsman | Institutional terminal UI, mobile thumb dock, zero AI-slop | `static/index.html`, `static/styles.css` |
| `BACKEND-synt-wrkdr-1` | Senior Backend Engineer | FastAPI core, async data collectors, DB pooling, caching | `app/*.py`, `collectors/*.py` |
| `QA-synt-wrkdr-1` | Adversarial QA Sentinel | Playwright E2E tests, Pytest, visual regression, veto gate | `tests/*.py`, `TEST_REPORT.json` |
| `DEVOPS-synt-wrkdr-1` | Lead SRE & Release Eng | Git releases, systemd service, Cloudflare tunnel, rollback | `systemd/*.service`, `deploy.sh` |

---

## 4. The Autonomous Improvement Loop Lifecycle

```text
[ CPO-synt-wrkdr-1 ] ──────► Pick 1 atomic task from RADAR_BACKLOG.md
        │
        ▼
[ MACRO-synt-wrkdr-1 ] ────► Supply economic formulas & data sources
        │
        ▼
[ CTO-synt-wrkdr-1 ] ──────► Review API contract & architecture spec
        │
        ▼
[ FRONTEND / BACKEND ] ────► Implement in feature branch: feature/task-xxx
        │
        ▼
[ QA-synt-wrkdr-1 ] ───────► Run Pytest + Playwright headless verification
        │
  ┌─────┴────────────────────────┐
  │                              │
[ PASS ]                       [ FAIL ]
  │                              │
  ▼                              ▼
[ DEVOPS-synt-wrkdr-1 ]        [ Hard Revert & Log Reason ]
- Merge to main branch         - git checkout -f
- Restart service              - Mark task as blocked in backlog
- Audit live URL               - Notify failure to Telegram
- Notify Herman via Telegram
```
