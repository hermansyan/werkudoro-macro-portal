"""
Opportunity & Action Radar Analytics Engine — Werkudoro Macro Intelligence Portal
Peran: MACRO-synt-wrkdr-1 & BACKEND-synt-wrkdr-1
Target: TASK-003

Fitur:
1. Macro Regime Engine: Penentuan kuadran/fase siklus makro ekonomi
   - EXPANSIVE (Growth accelerating, Inflation moderate/falling)
   - STAGNANT / RECESSIONARY (Growth decelerating, Inflation moderate/falling)
   - INFLATIONARY_SHOCK / STAGFLATION (Inflation accelerating, Growth decelerating/mixed)
   - TIGHTENING / RESTRICTIVE (Central banks hiking/hawkish, liquidity contracting)
2. Asset Impact Matrix: Skor ekspektasi performa & korelasi (+100 s.d -100)
   - Forex (USD, IDR, EUR, JPY)
   - Crypto (BTC, ETH, Altcoins)
   - Precious Metals (Gold, Silver)
   - Energy & Soft Commodities (Oil, Coal, CPO)
   - Equities (IHSG, S&P 500, Tech/Nasdaq, Defensive/Consumer)
3. Winners & Losers Identification:
   - Sektor dan entitas pasar yang diuntungkan vs dirugikan oleh kondisi saat ini.
4. Actionable Decisions:
   - Keputusan Finansial & Hidup (Cash ratio, emergency fund, cost of living hedging)
   - Keputusan Investasi & Trading (Aset prioritas, sizing, risk regime)
   - Keputusan Bisnis Riil (Ekspansi capex, hedging valas/impor, inventory strategy)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.database import DBContext
from app.collectors.cross_asset import get_latest_indicators

logger = logging.getLogger("macro.opportunity_radar")

def evaluate_macro_regime(indicators: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluasi rezim makroekonomi berbasis data empiris indikator terkini:
    - US CPI & Indo CPI (Tekanan Inflasi)
    - US 10Y Yield & FFR vs BI Rate (Keketatan Moneter)
    - DXY (Kekuatan Dolar Global)
    - VIX (Volatilitas & Risiko Global)
    - GDP Growth & PMI (Kekuatan Pertumbuhan)
    """
    us_cpi = indicators.get("US_CPI", {}).get("value", 2.70)
    indo_cpi = indicators.get("INDO_CPI", {}).get("value", 2.15)
    us_10y = indicators.get("US_10Y", {}).get("value", 4.50)
    indo_10y = indicators.get("INDO_10Y", {}).get("value", 6.85)
    dxy = indicators.get("DXY", {}).get("value", 104.2)
    vix = indicators.get("VIX", {}).get("value", 16.5)
    ffr = indicators.get("US_FED_RATE", {}).get("value", 4.50)
    bi_rate = indicators.get("BI_RATE", {}).get("value", 6.00)
    
    # Real Rates
    real_rate_us = round(ffr - us_cpi, 2)
    real_rate_indo = round(bi_rate - indo_cpi, 2)
    
    # Scoring matrix
    # Growth vs Inflation dynamic
    is_inflation_elevated = us_cpi > 3.0 or indo_cpi > 3.5
    is_monetary_tight = real_rate_us > 1.5 and dxy > 103.0
    is_risk_off = vix > 22.0
    
    if is_inflation_elevated and is_monetary_tight:
        regime_id = "INFLATIONARY_SHOCK"
        regime_name = "Inflationary Shock / Stagflationary Pressure"
        color = "#f43f5e" # semantic red/rose
        desc = (
            f"Inflasi berada di atas target (US CPI: {us_cpi}%, ID CPI: {indo_cpi}%) disertai "
            f"suku bunga riil restriktif (+{real_rate_us}% di AS). Biaya modal tinggi membatasi valuasi aset berisiko."
        )
        recommendation = "Prioritaskan Cash Preservation, instrumen floating rate, emas, komoditas energi, dan hedging kurs."
    elif is_monetary_tight and not is_inflation_elevated:
        regime_id = "TIGHTENING"
        regime_name = "Monetary Tightening / Restrictive Plateau"
        color = "#eab308" # amber
        desc = (
            f"Bank sentral mempertahankan suku bunga tinggi (FFR: {ffr}%, BI Rate: {bi_rate}%) di tengah disinflasi lambat. "
            f"DXY kuat di {dxy:.2f} menyerap likuiditas global ke pasar instrumen pasar uang AS."
        )
        recommendation = "Akumulasi selektif aset berkualitas tinggi dengan dividen kuat, money market yield, dan durasi obligasi moderat."
    elif not is_monetary_tight and not is_inflation_elevated:
        regime_id = "EXPANSIVE"
        regime_name = "Disinflationary Expansion / Goldilocks"
        color = "#10b981" # emerald
        desc = (
            f"Kondisi moneter akomodatif, inflasi terkendali, dan premi likuiditas membaik. "
            f"Volatilitas pasar (VIX: {vix}) rendah, menciptakan iklim kondusif bagi aset pertumbuhan."
        )
        recommendation = "Overweight Equities (Saham Siklis & Tech), Aset Kripto berlikuiditas tinggi, dan ekspansi capex produktif."
    else:
        regime_id = "STAGNANT"
        regime_name = "Late Cycle Slowdown / Stagnation"
        color = "#06b6d4" # cyan
        desc = (
            f"Pertumbuhan ekonomi melambat di tengah suku bunga yang mulai memuncak. Volatilitas VIX di level {vix:.1f}."
        )
        recommendation = "Fokus pada obligasi negara jangka menengah-panjang, saham defensif (konsumer primer), dan kas likuid."

    return {
        "regime_id": regime_id,
        "name": regime_name,
        "color": color,
        "description": desc,
        "primary_recommendation": recommendation,
        "metrics": {
            "us_cpi": us_cpi,
            "indo_cpi": indo_cpi,
            "us_fed_rate": ffr,
            "bi_rate": bi_rate,
            "real_rate_us": real_rate_us,
            "real_rate_indo": real_rate_indo,
            "dxy": dxy,
            "vix": vix,
            "us_10y": us_10y,
            "indo_10y": indo_10y
        }
    }

def calculate_asset_impact_matrix(regime_id: str, indicators: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Menghitung matriks dampak aset makro (Asset Impact Matrix).
    Skor berkisar antara -100 (Sangat Bearish / High Drag) hingga +100 (Sangat Bullish / High Tailwind).
    """
    dxy = indicators.get("DXY", {}).get("value", 104.2)
    us_10y = indicators.get("US_10Y", {}).get("value", 4.50)
    vix = indicators.get("VIX", {}).get("value", 16.5)
    brent = indicators.get("OIL_BRENT", {}).get("value", 74.5)
    gold = indicators.get("GOLD", {}).get("value", 2700.0)

    # Base scores according to regime
    if regime_id == "INFLATIONARY_SHOCK":
        matrix = [
            {"asset": "Emas (XAU/USD)", "category": "Precious Metals", "score": 85, "stance": "OVERWEIGHT", "driver": "Hedging debasement moneter & safe-haven geopolitik."},
            {"asset": "Komoditas Energi (Oil & Gas)", "category": "Commodities", "score": 75, "stance": "OVERWEIGHT", "driver": "Kekurangan suplai dan inflasi biaya primer."},
            {"asset": "Dolar AS (Cash / T-Bills)", "category": "Forex & Cash", "score": 80, "stance": "OVERWEIGHT", "driver": "Yield nominal tinggi dan pelarian ke likuiditas primer."},
            {"asset": "Rupiah (IDR)", "category": "Forex", "score": -45, "stance": "UNDERWEIGHT", "driver": "Tekanan imported inflation dan kekuatan DXY."},
            {"asset": "IHSG (Indeks Saham RI)", "category": "Equities", "score": -20, "stance": "NEUTRAL", "driver": "Komoditas RI menopang, namun valuasi tertekan yield tinggi."},
            {"asset": "US Equities (S&P 500 / Tech)", "category": "Equities", "score": -50, "stance": "UNDERWEIGHT", "driver": "Kompresi multiple P/E akibat discount rate tinggi."},
            {"asset": "Obligasi Negara (SBN / US Treasuries)", "category": "Fixed Income", "score": -40, "stance": "UNDERWEIGHT", "driver": "Kenaikan yield mengikis harga obligasi durasi panjang."},
            {"asset": "Kripto (BTC / ETH)", "category": "Digital Assets", "score": -35, "stance": "UNDERWEIGHT", "driver": "Kekeringan likuiditas global menekan aset beta tinggi."}
        ]
    elif regime_id == "TIGHTENING":
        matrix = [
            {"asset": "Dolar AS (USD / Money Market)", "category": "Forex & Cash", "score": 75, "stance": "OVERWEIGHT", "driver": "Suku bunga bebas risiko tinggi tanpa volatilitas ekuitas."},
            {"asset": "Emas (XAU/USD)", "category": "Precious Metals", "score": 60, "stance": "MODERATE_BUY", "driver": "Permintaan bank sentral menopang di tengah real yields positif."},
            {"asset": "Obligasi Jangka Pendek (SRBI / T-Bills)", "category": "Fixed Income", "score": 70, "stance": "OVERWEIGHT", "driver": "Yield menarik di kurva depan dengan durasi risiko minimal."},
            {"asset": "IHSG (Saham Perbankan & Value)", "category": "Equities", "score": 30, "stance": "SELECTIVE_BUY", "driver": "Net Interest Margin bank besar tetap solid."},
            {"asset": "Rupiah (IDR)", "category": "Forex", "score": -15, "stance": "NEUTRAL", "driver": "Dijaga oleh intervensi cadangan devisa dan instrumen SRBI."},
            {"asset": "Kripto (Bitcoin)", "category": "Digital Assets", "score": 25, "stance": "NEUTRAL", "driver": "Institusionalisasi ETF menahan likuiditas, tapi altcoin tertekan."},
            {"asset": "Komoditas Siklis (Batubara / Nikel)", "category": "Commodities", "score": -25, "stance": "UNDERWEIGHT", "driver": "Permintaan industri melambat akibat suku bunga tinggi."},
            {"asset": "US Equities (Growth / Mid-Caps)", "category": "Equities", "score": -20, "stance": "NEUTRAL", "driver": "Biaya utang tinggi membebani neraca non-mega caps."}
        ]
    elif regime_id == "EXPANSIVE":
        matrix = [
            {"asset": "Kripto (BTC & Altcoins)", "category": "Digital Assets", "score": 90, "stance": "OVERWEIGHT", "driver": "Sensitivitas tertinggi terhadap ekspansi M2 likuiditas global."},
            {"asset": "US Equities (Nasdaq / Tech)", "category": "Equities", "score": 85, "stance": "OVERWEIGHT", "driver": "Ekspansi valuasi multiple seiring pelonggaran finansial."},
            {"asset": "IHSG (Saham Siklis & Konsumer)", "category": "Equities", "score": 75, "stance": "OVERWEIGHT", "driver": "Daya beli domestik menguat dan inflow dana asing."},
            {"asset": "Rupiah (IDR)", "category": "Forex", "score": 60, "stance": "OVERWEIGHT", "driver": "Carry trade menarik dan pelemahan DXY menguatkan valas EM."},
            {"asset": "Obligasi Negara (SBN Durasi Panjang)", "category": "Fixed Income", "score": 70, "stance": "OVERWEIGHT", "driver": "Capital gain saat yield mengalami tren penurunan."},
            {"asset": "Emas (XAU/USD)", "category": "Precious Metals", "score": 50, "stance": "HOLD", "driver": "Tetap positif namun rotasi dana beralih ke aset high-growth."},
            {"asset": "Komoditas Industri (Tembaga, Minyak)", "category": "Commodities", "score": 65, "stance": "OVERWEIGHT", "driver": "Akselerasi PMI manufaktur dan permintaan riil global."},
            {"asset": "Dolar AS (USD Cash)", "category": "Forex & Cash", "score": -60, "stance": "UNDERWEIGHT", "driver": "Opportunity cost tinggi saat modal mengalir ke aset berisiko."}
        ]
    else: # STAGNANT
        matrix = [
            {"asset": "Obligasi Pemerintah (US Treasuries 10Y)", "category": "Fixed Income", "score": 80, "stance": "OVERWEIGHT", "driver": "Flight-to-safety dan ekspektasi pemangkasan bunga mendalam."},
            {"asset": "Emas (XAU/USD)", "category": "Precious Metals", "score": 75, "stance": "OVERWEIGHT", "driver": "Pelindung nilai klasik saat resesi dan kekhawatiran kredit."},
            {"asset": "Saham Defensif (Konsumer Primer, Telko)", "category": "Equities", "score": 40, "stance": "SELECTIVE_BUY", "driver": "Arus kas stabil dan dividend yield tahan resesi."},
            {"asset": "Dolar AS (USD)", "category": "Forex", "score": 50, "stance": "MODERATE_BUY", "driver": "Likuiditas global mengerut memicu USD shortage."},
            {"asset": "Rupiah (IDR)", "category": "Forex", "score": -30, "stance": "UNDERWEIGHT", "driver": "Outflow dari emerging markets saat sentimen global risk-off."},
            {"asset": "Komoditas Energi & Industri", "category": "Commodities", "score": -70, "stance": "UNDERWEIGHT", "driver": "Permintaan konsumsi anjlok drastis."},
            {"asset": "IHSG (Sektor Properti & Komoditas)", "category": "Equities", "score": -45, "stance": "UNDERWEIGHT", "driver": "Permintaan KPR lambat dan harga ekspor melemah."},
            {"asset": "Kripto (Altcoins)", "category": "Digital Assets", "score": -60, "stance": "UNDERWEIGHT", "driver": "Kapitalisasi spekulatif terlikuidasi pertama kali."}
        ]

    # Dinamisasi skor berdasarkan nilai live
    for item in matrix:
        if item["asset"].startswith("Emas") and gold > 2650:
            item["score"] = min(item["score"] + 5, 100)
        elif item["asset"].startswith("Dolar") and dxy > 105:
            item["score"] = min(item["score"] + 10, 100)
        elif item["asset"].startswith("Rupiah") and dxy > 105:
            item["score"] = max(item["score"] - 10, -100)
        elif item["asset"].startswith("Komoditas Energi") and brent > 80:
            item["score"] = min(item["score"] + 10, 100)

    # Urutkan dari score tertinggi ke terendah
    matrix.sort(key=lambda x: x["score"], reverse=True)
    return matrix

def identify_winners_and_losers(regime_id: str, indicators: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Identifikasi sektor spesifik, industri, dan emiten/entitas yang paling
    diuntungkan (Winners) vs dirugikan (Losers) dalam kondisi makro saat ini.
    """
    dxy = indicators.get("DXY", {}).get("value", 104.2)
    brent = indicators.get("OIL_BRENT", {}).get("value", 74.5)
    coal = indicators.get("COAL_NEWCASTLE", {}).get("value", 145.0)
    cpo = indicators.get("CPO_MYR", {}).get("value", 4850.0)
    
    winners = []
    losers = []

    if regime_id in ["INFLATIONARY_SHOCK", "TIGHTENING"]:
        winners.append({
            "sector": "Perbankan Big-4 (BBCA, BBRI, BMRI, BBNI)",
            "reason": "Margin bunga bersih (NIM) bertahan tebal; likuiditas CASA solid menopang cost of funds.",
            "impact_tag": "HIGH BENEFICIARY"
        })
        winners.append({
            "sector": "Eksportir Berbasis USD & Komoditas (Tambang Emas, Sawit)",
            "reason": f"Menerima pendapatan dalam USD kuat (DXY: {dxy:.1f}) sementara beban operasional dalam Rupiah.",
            "impact_tag": "STRONG TAILWIND"
        })
        winners.append({
            "sector": "Instrumen Pasar Uang & SRBI (Bank Indonesia)",
            "reason": "Yield risk-free di atas 6.5% - 7.0% tanpa risiko penurunan harga modal.",
            "impact_tag": "SAFE HARBOR"
        })
        winners.append({
            "sector": "Produsen Energi & Pertambangan Logam Mulia (MDKA, ANTM, PTBA)",
            "reason": "Kenaikan harga aset riil mengompensasi tekanan inflasi biaya finansial.",
            "impact_tag": "ASSET BACKED"
        })

        losers.append({
            "sector": "Importir Komponen & Farmasi/Bahan Baku (KLBF, TPIA, Industri Kimia)",
            "reason": "Margin tergerus pelemahan nilai tukar Rupiah terhadap Dolar AS (FX Drag).",
            "impact_tag": "HIGH FX RISK"
        })
        losers.append({
            "sector": "Sektor Properti & Konstruksi Berutang Tinggi (High Leverage)",
            "reason": "Beban bunga pinjaman melonjak dan permintaan KPR tertahan suku bunga acuan tinggi.",
            "impact_tag": "DEBT SQUEEZE"
        })
        losers.append({
            "sector": "Emiten Teknologi & Startup Bakar Uang (High Beta Growth)",
            "reason": "Valuasi DCF menyusut drastis karena kenaikan risk-free rate di AS dan domestik.",
            "impact_tag": "MULTIPLE COMPRESSION"
        })
        losers.append({
            "sector": "Maskapai Penerbangan & Logistik Darat",
            "reason": f"Harga avtur/bahan bakar minyak (${brent:.1f}/bbl) dan leasing armada valas menekan profitabilitas.",
            "impact_tag": "COST OF GOODS DRAG"
        })
    else: # EXPANSIVE or STAGNANT
        winners.append({
            "sector": "Sektor Teknologi, Digital & E-Commerce",
            "reason": "Cost of capital menurun membuka kembali investasi pertumbuhan dan ekspansi valuasi.",
            "impact_tag": "GROWTH ENGINE"
        })
        winners.append({
            "sector": "Sektor Properti & Real Estate Perumahan",
            "reason": "Bunga KPR lebih murah mendorong lonjakan permintaan residensial dan perbaikan cashflow.",
            "impact_tag": "INTEREST BENEFICIARY"
        })
        winners.append({
            "sector": "Konsumer Siklis & Ritel (ACES, MAPI, Otomotif ASII)",
            "reason": "Disposable income masyarakat meningkat didukung inflasi yang jinak dan pinjaman murah.",
            "impact_tag": "DOMESTIC DEMAND"
        })
        winners.append({
            "sector": "Obligasi Korporasi Rating Investment Grade",
            "reason": "Credit spread mengecil dan refinancing utang menjadi jauh lebih hemat.",
            "impact_tag": "CAPITAL GAIN"
        })

        losers.append({
            "sector": "Instrumen Deposito & Cash Rekening Tradisional",
            "reason": "Yield bunga riil terkikis dan tertinggal jauh dibandingkan imbal hasil aset produktif.",
            "impact_tag": "PURCHASING POWER LOSS"
        })
        losers.append({
            "sector": "Perusahaan Pengelola Valuta Asing / Speculative USD Hold",
            "reason": "Dolar AS melemah membuat kepemilikan kas USD mengalami penurunan nilai relatif terhadap Rupiah.",
            "impact_tag": "CURRENCY LOSS"
        })

    return {
        "winners": winners,
        "losers": losers
    }

def generate_actionable_decisions(regime_id: str, indicators: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merumuskan rekomendasi aksi terukur dan terapan:
    1. Financial & Living (Pribadi & Keluarga)
    2. Trading & Portfolio (Alokasi Modal)
    3. Real Business (Operasional UKM / Korporasi)
    """
    dxy = indicators.get("DXY", {}).get("value", 104.2)
    bi_rate = indicators.get("BI_RATE", {}).get("value", 6.0)

    if regime_id in ["INFLATIONARY_SHOCK", "TIGHTENING"]:
        life_decisions = [
            {
                "action": "Alokasi Kas Darurat ke Instrumen Yield Tinggi",
                "detail": f"Tempatkan 6-12 bulan dana darurat pada instrumen pasar uang berimbal hasil >6.0% (SRBI, Reksadana Pasar Uang, atau Deposito Digital) untuk mengalahkan inflasi tanpa mengorbankan likuiditas.",
                "priority": "HIGH"
            },
            {
                "action": "Kunci Bunga KPR Fixed Rate / Percepat Pelunasan Bunga Mengambang",
                "detail": "Hindari fasilitas floating rate jangka panjang di era BI-Rate tinggi. Jika memungkinkan, lakukan negosiasi tenor atau pelunasan sebagian pokok (deleveraging).",
                "priority": "URGENT"
            },
            {
                "action": "Diversifikasi Tabungan ke Logam Mulia Fisik",
                "detail": "Pertahankan minimal 10-15% portofolio kekayaan cair dalam bentuk emas fisik/digital sebagai benteng penurunan daya beli jangka panjang.",
                "priority": "MEDIUM"
            }
        ]

        trading_decisions = [
            {
                "strategy": "Core-Satellite: High Cash + Concentrated Leaders",
                "detail": "Porsi kas/risk-free 30-40%. Satelit pada saham perbankan Tier-1, emiten dividen tinggi, dan komoditas energi.",
                "stance": "DEFENSIVE_AGGRESSIVE"
            },
            {
                "strategy": "Kripto: DCA Hanya pada Bitcoin (Dominance Play)",
                "detail": "Fokus akumulasi pada BTC di area support kuat; batasi eksposur pada altcoins berkapitalisasi kecil karena likuiditas terserap ke DXY.",
                "stance": "SELECTIVE"
            },
            {
                "strategy": "Fixed Income: Barbell Strategy (SRBI + SBN 10Y)",
                "detail": "Kombinasikan instrumen tenor pendek (SRBI) untuk yield langsung dengan cicil obligasi 10Y untuk mengunci yield tinggi sebelum siklus pelonggaran.",
                "stance": "YIELD_HARVESTING"
            }
        ]

        business_decisions = [
            {
                "action": "Hedging Valas untuk Pembelian Bahan Baku Impor",
                "detail": f"Terapkan kontrak forward/FX hedging untuk transaksi impor di tengah level DXY ({dxy:.1f}) yang menekan kurs Rupiah.",
                "risk_area": "Treasury & FX"
            },
            {
                "action": "Restrukturisasi Piutang & Pengetatan Termin Pembayaran Pelanggan",
                "detail": "Persingkat termin pembayaran tagihan (TOP dari 60 hari ke 30 hari) guna mencegah idle capital dan risiko macet kredit.",
                "risk_area": "Working Capital"
            },
            {
                "action": "Tahan Capex Utang Spekulatif; Fokus Otomasi Efisiensi Opex",
                "detail": "Tunda ekspansi pabrik baru yang mengandalkan pinjaman bank komersial berbunga mahal; alihkan ke otomatisasi software yang langsung memangkas opex.",
                "risk_area": "Capital Expenditure"
            }
        ]
    else: # EXPANSIVE / STAGNANT
        life_decisions = [
            {
                "action": "Rotasi Likuiditas Kas Berlebih ke Aset Pertumbuhan",
                "detail": "Kurangi porsi idle cash di tabungan konvensional karena yield riil menurun; alokasikan ke saham bluechip dan reksadana indeks.",
                "priority": "HIGH"
            },
            {
                "action": "Manfaatkan Suku Bunga Rendah untuk Aset Produktif",
                "detail": "Waktu ideal untuk mengajukan pembiayaan properti atau modal kerja bisnis dengan suku bunga terendah siklus.",
                "priority": "MEDIUM"
            }
        ]

        trading_decisions = [
            {
                "strategy": "Full Risk-On: Beta Equities & Altcoins",
                "detail": "Tingkatkan alokasi ke saham teknologi, konsumer siklis, dan ekosistem layer-1 kripto (ETH, SOL).",
                "stance": "AGGRESSIVE_GROWTH"
            },
            {
                "strategy": "Perpanjang Durasi Portofolio Obligasi",
                "detail": "Beli obligasi durasi 10Y-20Y untuk memaksimalkan potensi capital gain saat kurva yield turun.",
                "stance": "CAPITAL_GAIN"
            }
        ]

        business_decisions = [
            {
                "action": "Ekspansi Kapasitas & Agresif Tambah Inventory",
                "detail": "Ambil momentum peningkatan daya beli konsumen untuk memperbesar pangsa pasar dan membuka cabang baru.",
                "risk_area": "Business Expansion"
            },
            {
                "action": "Refinancing Utang Lama ke Bunga Lebih Murah",
                "detail": "Lakukan renegosiasi suku bunga pinjaman korporasi atau penerbitan obligasi berkupon rendah.",
                "risk_area": "Corporate Finance"
            }
        ]

    return {
        "financial_living": life_decisions,
        "trading_investment": trading_decisions,
        "real_business": business_decisions
    }

def build_opportunity_radar() -> Dict[str, Any]:
    """
    Eksekusi kalkulasi menyeluruh Opportunity & Action Radar.
    """
    indicators = get_latest_indicators()
    if not indicators:
        logger.warning("Tidak ada indikator makro. Menghasilkan default fallback.")
        indicators = {}

    regime = evaluate_macro_regime(indicators)
    matrix = calculate_asset_impact_matrix(regime["regime_id"], indicators)
    entities = identify_winners_and_losers(regime["regime_id"], indicators)
    actions = generate_actionable_decisions(regime["regime_id"], indicators)

    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "timestamp": now_iso,
        "regime": regime,
        "asset_impact_matrix": matrix,
        "winners_and_losers": entities,
        "actionable_decisions": actions,
        "status": "active"
    }

    # Persist ke database tabel macro.opportunity_radar
    try:
        with DBContext(commit=True) as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS macro.opportunity_radar (
                id TEXT PRIMARY KEY,
                regime_id TEXT NOT NULL,
                data JSONB NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)
            cur.execute("""
            INSERT INTO macro.opportunity_radar (id, regime_id, data, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                regime_id = EXCLUDED.regime_id,
                data = EXCLUDED.data,
                updated_at = EXCLUDED.updated_at
            """, (
                "latest_radar",
                regime["regime_id"],
                json.dumps(payload),
                now_iso
            ))
        logger.info(f"Opportunity Radar successfully updated to DB. Regime: {regime['regime_id']}")
    except Exception as e:
        logger.error(f"Failed to persist Opportunity Radar to DB: {e}")

    return payload

def get_opportunity_radar_data() -> Dict[str, Any]:
    """Mengambil data opportunity radar terkini dari PostgreSQL atau kalkulasi jika kosong."""
    try:
        with DBContext(commit=False) as cur:
            cur.execute("SELECT data FROM macro.opportunity_radar WHERE id = 'latest_radar'")
            row = cur.fetchone()
            if row and row.get("data"):
                data = row["data"]
                if isinstance(data, str):
                    data = json.loads(data)
                return data
    except Exception as e:
        logger.warning(f"Failed to fetch stored radar, calculating on the fly: {e}")

    return build_opportunity_radar()

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    radar = build_opportunity_radar()
    print("Opportunity Radar compiled successfully:")
    print("Regime:", radar["regime"]["name"])
    print("Total Asset Impact Rows:", len(radar["asset_impact_matrix"]))
    print("Winners Count:", len(radar["winners_and_losers"]["winners"]))
    print("Losers Count:", len(radar["winners_and_losers"]["losers"]))
