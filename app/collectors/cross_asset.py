"""
Cross-Asset Collector & Analytics Engine — Werkudoro Macro Intelligence Portal
Peran: MACRO-synt-wrkdr-1 & BACKEND-synt-wrkdr-1

Menganalisis korelasi dan transmisi lintas kelas aset:
1. Gold (XAU/USD) & US Real Yields Correlation (Safe haven vs debasement regime).
2. Crypto (BTC/USD, ETH/USD) Macro Liquidity Indicator (Global liquidity sponge & risk beta).
3. Komoditas Energi & Ekspor RI: Brent Oil, Batubara Newcastle, CPO (Impact pada Trade Balance & APBN RI).
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.database import DBContext

logger = logging.getLogger("macro.cross_asset")

def get_latest_indicators() -> Dict[str, Dict[str, Any]]:
    """Mengambil snapshot indikator makro terkini dari PostgreSQL."""
    with DBContext(commit=False) as cur:
        cur.execute("SELECT key, name, category, region, value, prev_value, unit, change_pct, trend FROM macro.indicators")
        rows = cur.fetchall()
        return {r["key"]: dict(r) for r in rows}

def analyze_gold_real_yields(indicators: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analisis Korelasi Emas (XAU/USD) vs US Real Yields.
    Korelasi klasik: Real Yield naik -> Opportunity cost emas naik -> Emas tertekan.
    Regime divergensi: Emas tetap rally di tengah Real Yield tinggi menandakan
    akumulasi struktural bank sentral (de-dolarisasi) dan perlindungan debasement utang negara.
    """
    gold = indicators.get("GOLD", {})
    gold_price = gold.get("value", 2700.0)
    gold_chg = gold.get("change_pct", 0.0)
    
    us_10y = indicators.get("US_10Y", {}).get("value", 4.50)
    us_cpi = indicators.get("US_CPI", {}).get("value", 2.70)
    real_yield = round(us_10y - us_cpi, 2)
    
    tip_etf = indicators.get("US_TIPS_10Y", {})
    tip_val = tip_etf.get("value", 104.5)
    tip_chg = tip_etf.get("change_pct", 0.0)
    
    # Deteksi anomali/divergensi
    is_divergent = real_yield > 1.50 and gold_price > 2500.0
    
    if is_divergent:
        signal = "STRUCTURAL_DEBASEMENT_ACCUMULATION"
        signal_label = "Divergensi Struktural: Akumulasi De-Dolarisasi"
        regime_desc = (
            f"Emas bertahan kuat di ${gold_price:,.2f}/oz ({gold_chg:+.2f}%) meskipun US 10Y Real Yield "
            f"berada di level restriktif +{real_yield}% (Nominal 10Y: {us_10y}% - CPI: {us_cpi}%). "
            f"Kondisi ini mengonfirmasi de-coupling dari suku bunga riil klasik, didorong oleh akumulasi agresif "
            f"cadangan emas bank sentral global (PBOC, RBI) serta hedging terhadap ekspansi utang fiskal AS."
        )
    elif real_yield > 2.0 and gold_chg < 0:
        signal = "BEARISH_REAL_RATE_DRAG"
        signal_label = "Tekanan Suku Bunga Riil Positif"
        regime_desc = (
            f"Suku bunga riil AS tinggi (+{real_yield}%) meningkatkan opportunity cost emas, menekan harga spot."
        )
    else:
        signal = "BULLISH_SAFE_HAVEN"
        signal_label = "Monetary Easing & Safe Haven Tailwind"
        regime_desc = (
            f"Penurunan suku bunga riil AS (+{real_yield}%) memberikan dorongan likuiditas bagi reli emas dunia."
        )

    insights = [
        f"US 10-Year Real Yield berada di level {real_yield:+.2f}% (Spread Nominal 10Y {us_10y}% vs Inflasi {us_cpi}%).",
        f"Harga spot Emas Dunia (XAU/USD) tercatat ${gold_price:,.2f}/toz dengan variasi harian {gold_chg:+.2f}%.",
        f"Instrumen TIPS ETF (TIP) diperdagangkan di ${tip_val:.2f} ({tip_chg:+.2f}%).",
        f"Status Regim: {signal_label}. {regime_desc}"
    ]

    metrics = {
        "gold_price_usd": gold_price,
        "gold_change_pct": gold_chg,
        "us_10y_nominal_yield": us_10y,
        "us_cpi_yoy": us_cpi,
        "us_10y_real_yield": real_yield,
        "tips_etf_price": tip_val,
        "tips_etf_change_pct": tip_chg,
        "divergence_active": is_divergent,
        "signal_label": signal_label
    }

    return {
        "id": "gold_real_yields",
        "category": "Precious Metals & Real Rates",
        "title": "Korelasi Emas (XAU/USD) & US Real Yields",
        "metrics": metrics,
        "insights": insights,
        "signal": signal
    }

def analyze_crypto_macro_liquidity(indicators: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analisis Indikator Likuiditas Makro Crypto (BTC & ETH).
    Bitcoin bertindak sebagai high-beta macro liquidity proxy & monetary debasement hedge.
    ETH/BTC ratio mencerminkan selera risiko (risk appetite) spekulatif.
    """
    btc = indicators.get("BTC_USD", {})
    btc_price = btc.get("value", 84000.0)
    btc_chg = btc.get("change_pct", 0.0)

    eth = indicators.get("ETH_USD", {})
    eth_price = eth.get("value", 2680.0)
    eth_chg = eth.get("change_pct", 0.0)

    dxy = indicators.get("DXY", {}).get("value", 101.0)
    vix = indicators.get("VIX", {}).get("value", 15.0)

    eth_btc_ratio = round(eth_price / btc_price, 4) if btc_price > 0 else 0.0

    # Macro Liquidity Score (0 - 100)
    # DXY lebih rendah & VIX lebih rendah -> Likuiditas global lebih longgar
    dxy_factor = max(0, min(100, (108 - dxy) / 12 * 50))
    vix_factor = max(0, min(100, (28 - vix) / 16 * 30))
    crypto_momentum = 20 if (btc_chg > 0 and eth_chg > 0) else (10 if btc_chg > 0 else 0)
    liquidity_score = int(round(dxy_factor + vix_factor + crypto_momentum))
    liquidity_score = max(5, min(95, liquidity_score))

    if liquidity_score >= 65 and eth_btc_ratio > 0.035:
        signal = "EXPANSIVE_RISK_ON"
        signal_label = "Likuiditas Melimpah / Risk-On Agresif"
        regime_desc = "Likuiditas global dalam fase ekspansi. Altcoin dan aset spekulatif mendapatkan arus modal kuat."
    elif btc_price > 75000 and eth_btc_ratio <= 0.035:
        signal = "BITCOIN_DOMINANCE_DEFENSIVE"
        signal_label = "Dominasi Bitcoin / Likuiditas Selektif"
        regime_desc = (
            f"Modal terkonsentrasi pada Bitcoin (${btc_price:,.0f}) sebagai aset cadangan digital, "
            f"sementara rasio ETH/BTC ({eth_btc_ratio:.4f}) mencerminkan kehati-hatian investor terhadap alt-beta."
        )
    elif liquidity_score < 40:
        signal = "LIQUIDITY_CONTRACTION"
        signal_label = "Kontraksi Likuiditas Global / Risk-Off"
        regime_desc = "Penguatan DXY dan kenaikan yield menekan likuiditas aset kripto secara sistemik."
    else:
        signal = "NEUTRAL_CONSOLIDATION"
        signal_label = "Konsolidasi Likuiditas Netral"
        regime_desc = "Arus likuiditas berimbang antara stabilitas suku bunga The Fed dan selera risiko pasar modal."

    insights = [
        f"Bitcoin (BTC/USD) diperdagangkan pada ${btc_price:,.2f} ({btc_chg:+.2f}%).",
        f"Ethereum (ETH/USD) diperdagangkan pada ${eth_price:,.2f} ({eth_chg:+.2f}%).",
        f"Rasio ETH/BTC tercatat di {eth_btc_ratio:.4f}, bertindak sebagai barometer rotasi spekulatif risk-beta.",
        f"Indeks Likuiditas Makro Global terhitung di level {liquidity_score}/100 (Status: {signal_label}).",
        f"Kondisi DXY ({dxy:.2f}) dan VIX ({vix:.2f}) memandu selera risiko investor institusional."
    ]

    metrics = {
        "btc_price_usd": btc_price,
        "btc_change_pct": btc_chg,
        "eth_price_usd": eth_price,
        "eth_change_pct": eth_chg,
        "eth_btc_ratio": eth_btc_ratio,
        "global_liquidity_score": liquidity_score,
        "dxy_level": dxy,
        "vix_level": vix,
        "signal_label": signal_label
    }

    return {
        "id": "crypto_macro_liquidity",
        "category": "Digital Assets & Global Liquidity",
        "title": "Barometer Likuiditas Makro Kripto (BTC & ETH)",
        "metrics": metrics,
        "insights": insights,
        "signal": signal
    }

def analyze_commodity_export_ri(indicators: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analisis Komoditas Energi & Ekspor RI:
    - Brent & WTI Crude Oil (Impor energi bersih / Beban Subsidi BBM APBN)
    - Batubara Newcastle (Ekspor andalan RI / PNBP Minerba)
    - CPO (Minyak Kelapa Sawit) (Ekspor andalan RI / Surplus Neraca Dagang)
    """
    brent = indicators.get("BRENT_OIL", {})
    brent_price = brent.get("value", 95.0)
    brent_chg = brent.get("change_pct", 0.0)

    wti = indicators.get("WTI_OIL", {})
    wti_price = wti.get("value", 90.0)

    coal = indicators.get("COAL_PRICE", {})
    coal_price = coal.get("value", 138.5)
    coal_chg = coal.get("change_pct", 0.0)

    cpo = indicators.get("CPO_PRICE", {})
    cpo_price_myr = cpo.get("value", 4350.0)
    cpo_chg = cpo.get("change_pct", 0.0)

    # Estimasi konversi CPO ke USD/Ton (kurs rata-rata MYR/USD ~ 0.225)
    cpo_price_usd = round(cpo_price_myr * 0.225, 1)

    # Asumsi ICP APBN (Indonesian Crude Price) baseline ~$82/bbl
    icp_baseline = 82.0
    oil_subsidy_pressure = round(brent_price - icp_baseline, 2)

    # Terms of Trade Score Ekspor RI (0 - 100)
    # Coal > $120 & CPO > 4000 MYR = sangat positif bagi surplus ekspor
    export_engine_score = min(50, max(0, (coal_price - 80) / 80 * 25)) + min(50, max(0, (cpo_price_myr - 3200) / 1600 * 25))
    oil_drag_score = min(30, max(0, (brent_price - 70) / 40 * 30))
    terms_of_trade_score = int(round(max(10, min(95, 40 + export_engine_score - oil_drag_score))))

    if oil_subsidy_pressure > 10.0 and terms_of_trade_score >= 60:
        signal = "DUAL_IMPACT_WINNERS_EXPORTERS_FISCAL_PRESSURE"
        signal_label = "Windfall Ekspor Kuat / Tekanan Fiskal Energi"
        analysis = (
            f"Kombinasi Batubara (${coal_price}/Ton) dan CPO (RM {cpo_price_myr:,.0f}/Ton) menjaga surplus "
            f"neraca perdagangan tetap solid. Namun, minyak Brent (${brent_price:,.2f}/bbl) melampaui asumsi ICP "
            f"APBN (${icp_baseline}/bbl) sebesar +${oil_subsidy_pressure}/bbl, meningkatkan tagihan kompensasi energi/BBM."
        )
    elif terms_of_trade_score >= 65:
        signal = "FAVORABLE_TRADE_SURPLUS"
        signal_label = "Kondusif bagi Surplus Neraca Dagang RI"
        analysis = "Kekuatan ekspor CPO dan Batubara menopang stabilitas cadangan devisa dan ketahanan nilai tukar Rupiah."
    else:
        signal = "COMMODITY_DRAG_TERMS_OF_TRADE"
        signal_label = "Penurunan Terms of Trade Komoditas"
        analysis = "Pelemahan harga komoditas ekspor mempersempit surplus transaksi berjalan Indonesia."

    insights = [
        f"Minyak Mentah Brent berada di level ${brent_price:.2f}/bbl ({brent_chg:+.2f}%) vs WTI ${wti_price:.2f}/bbl.",
        f"Batubara Newcastle tercatat di ${coal_price:.1f}/Ton ({coal_chg:+.2f}%), kontributor utama PNBP SDA minerba RI.",
        f"Minyak Kelapa Sawit (CPO) diperdagangkan di RM {cpo_price_myr:,.0f}/Ton (~${cpo_price_usd}/Ton) ({cpo_chg:+.2f}%).",
        f"Deviasi Minyak terhadap Asumsi ICP APBN: {oil_subsidy_pressure:+.2f} USD/bbl (ICP acuan ${icp_baseline}/bbl).",
        f"Indeks Terms of Trade Komoditas Ekspor RI: {terms_of_trade_score}/100. Status: {signal_label}."
    ]

    metrics = {
        "brent_oil_usd": brent_price,
        "brent_change_pct": brent_chg,
        "wti_oil_usd": wti_price,
        "coal_newcastle_usd": coal_price,
        "coal_change_pct": coal_chg,
        "cpo_price_myr": cpo_price_myr,
        "cpo_price_usd_est": cpo_price_usd,
        "cpo_change_pct": cpo_chg,
        "icp_baseline_usd": icp_baseline,
        "oil_subsidy_delta_usd": oil_subsidy_pressure,
        "terms_of_trade_score": terms_of_trade_score,
        "signal_label": signal_label
    }

    return {
        "id": "commodity_export_ri",
        "category": "Commodity Energy & Indo Exports",
        "title": "Komoditas Energi & Ekspor RI (Brent, Coal, CPO)",
        "metrics": metrics,
        "insights": insights,
        "signal": signal
    }

def sync_cross_asset() -> List[Dict[str, Any]]:
    """
    Menjalankan kalkulasi korelasi lintas aset dan menyimpan hasilnya ke PostgreSQL
    tabel `macro.cross_asset_analytics`.
    """
    indicators = get_latest_indicators()
    if not indicators:
        logger.warning("Tidak ada indikator makro di database. Melakukan skip kalkulasi cross-asset.")
        return []

    gold_analysis = analyze_gold_real_yields(indicators)
    crypto_analysis = analyze_crypto_macro_liquidity(indicators)
    commodity_analysis = analyze_commodity_export_ri(indicators)

    all_analyses = [gold_analysis, crypto_analysis, commodity_analysis]
    now_iso = datetime.now(timezone.utc).isoformat()

    with DBContext(commit=True) as cur:
        for item in all_analyses:
            cur.execute("""
            INSERT INTO macro.cross_asset_analytics (id, category, title, metrics, insights, signal, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                category = EXCLUDED.category,
                title = EXCLUDED.title,
                metrics = EXCLUDED.metrics,
                insights = EXCLUDED.insights,
                signal = EXCLUDED.signal,
                updated_at = EXCLUDED.updated_at
            """, (
                item["id"],
                item["category"],
                item["title"],
                json.dumps(item["metrics"]),
                item["insights"],
                item["signal"],
                now_iso
            ))

    logger.info(f"Cross-asset analytics synchronized successfully: {len(all_analyses)} domains updated.")
    return all_analyses

def get_cross_asset_summary() -> Dict[str, Any]:
    """Mengambil summary cross-asset dari PostgreSQL."""
    with DBContext(commit=False) as cur:
        cur.execute("SELECT id, category, title, metrics, insights, signal, updated_at FROM macro.cross_asset_analytics")
        rows = cur.fetchall()

    if not rows:
        # Jika belum ada data tersimpan, sinkronkan sekali
        analyses = sync_cross_asset()
        return {item["id"]: item for item in analyses}

    result = {}
    for r in rows:
        metrics_val = r["metrics"]
        if isinstance(metrics_val, str):
            metrics_val = json.loads(metrics_val)
        result[r["id"]] = {
            "id": r["id"],
            "category": r["category"],
            "title": r["title"],
            "metrics": metrics_val,
            "insights": r["insights"],
            "signal": r["signal"],
            "updated_at": r["updated_at"]
        }
    return result

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    res = sync_cross_asset()
    print(f"Calculated and stored {len(res)} cross-asset analytics domains.")
