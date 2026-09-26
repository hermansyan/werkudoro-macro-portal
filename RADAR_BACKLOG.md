# 🎯 Radar Backlog — Werkudoro Macro Intelligence Portal
> Disusun oleh: `CPO-synt-wrkdr-1` & `MACRO-synt-wrkdr-1`  
> Target Operasional: Autonomous Improvement Looping

Daftar backlog berikut adalah tugas-tugas terukur dan atomik untuk dieksekusi secara otonom oleh tim agent `synt-wrkdr-1`.

---

## Sprint 1: Macro Matrix & Opportunity Radar (Core Intelligence)

- [x] **TASK-001 (DEVOPS/CTO):** Inisialisasi arsitektur multi-agent `synt-wrkdr-1`, Git repo GitHub, dan SOP Company Charter.
- [x] **TASK-002 (MACRO/BACKEND):** Tambahkan Cross-Asset Collector:
  - Gold (XAU/USD) & Real Yields correlation.
  - Crypto (BTC/USD, ETH/USD) macro liquidity indicator.
  - Komoditas Energi & Ekspor RI: Brent Oil, Batubara (Newcastle), CPO.
- [ ] **TASK-003 (MACRO/BACKEND):** Bangun API Engine `/api/opportunity-radar`:
  - Algoritma penentuan Macro Regime (Expansive, Stagnant, Inflationary Shock, Tightening).
  - Matriks Dampak Aset: Forex, Crypto, Gold, Komoditas, Saham IHSG/Global.
  - Identifikasi Sektor/Entitas yang Diuntungkan (Winners) vs Dirugikan (Losers).
- [ ] **TASK-004 (FRONTEND):** Bangun Modul Visual "Opportunity & Action Radar" pada Dashboard:
  - Tampilan Institutional Terminal dengan tabular numbers.
  - Ringkasan Aksi: Keputusan Hidup (Saving/Cash ratio), Keputusan Trading (Aset berpotensi), Keputusan Bisnis Riil (Ekspansi/Hedging valas).
  - Tampilan responsif mobile thumb-dock tanpa horizontal sway.
- [ ] **TASK-005 (QA):** Buat E2E Automated Verification Test Suite (Playwright + Pytest):
  - Uji validasi endpoint data `/api/opportunity-radar`.
  - Uji visual snapshot rendering UI desktop & mobile.
  - Verifikasi stop signal (tolak deploy jika ada runtime exception atau broken UI).
