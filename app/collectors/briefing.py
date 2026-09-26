import logging
from datetime import datetime, timezone
from app.database import DBContext

logger = logging.getLogger("macro.briefing")

DEFAULT_CALENDAR_EVENTS = [
    {
        "event_name": "Rapat Dewan Gubernur (RDG) Bank Indonesia",
        "region": "Indonesia",
        "impact": "Tinggi",
        "event_date": "2026-10-15",
        "time_wib": "14:00 WIB",
        "forecast": "6.00%",
        "previous": "6.00%",
        "actual": "Menunggu",
        "notes": "Keputusan BI-Rate untuk menjaga stabilitas nilai tukar Rupiah & memitigasi arus modal keluar."
    },
    {
        "event_name": "US FOMC Interest Rate Decision & Press Conference",
        "region": "Global",
        "impact": "Tinggi",
        "event_date": "2026-10-29",
        "time_wib": "01:00 WIB",
        "forecast": "4.25% - 4.50%",
        "previous": "4.50% - 4.75%",
        "actual": "Menunggu",
        "notes": "Penentuan jalur pelonggaran moneter The Fed pasca rilis data ketenagakerjaan dan inflasi AS."
    },
    {
        "event_name": "Rilis Data Inflasi Indonesia (CPI YoY) BPS",
        "region": "Indonesia",
        "impact": "Tinggi",
        "event_date": "2026-10-01",
        "time_wib": "11:00 WIB",
        "forecast": "1.85%",
        "previous": "1.71%",
        "actual": "Menunggu",
        "notes": "Indikator kunci tekanan harga pangan bergejolak (volatile food) dan inflasi inti."
    },
    {
        "event_name": "US Consumer Price Index (CPI YoY)",
        "region": "Global",
        "impact": "Tinggi",
        "event_date": "2026-10-10",
        "time_wib": "19:30 WIB",
        "forecast": "2.65%",
        "previous": "2.70%",
        "actual": "Menunggu",
        "notes": "Menjadi penentu utama laju penurunan Fed Funds Rate di kuartal akhir."
    },
    {
        "event_name": "Rilis Pertumbuhan PDB Indonesia Kuartal III BPS",
        "region": "Indonesia",
        "impact": "Sedang",
        "event_date": "2026-11-05",
        "time_wib": "11:00 WIB",
        "forecast": "5.08%",
        "previous": "5.05%",
        "actual": "Menunggu",
        "notes": "Mengukur ketahanan konsumsi domestik dan realisasi belanja modal pemerintah."
    },
    {
        "event_name": "ECB Monetary Policy Decision",
        "region": "Global",
        "impact": "Sedang",
        "event_date": "2026-10-17",
        "time_wib": "19:15 WIB",
        "forecast": "3.00%",
        "previous": "3.25%",
        "actual": "Menunggu",
        "notes": "Kebijakan pelonggaran bank sentral Eropa di tengah perlambatan manufaktur Jerman."
    },
    {
        "event_name": "Cadangan Devisa Indonesia Akhir Bulan (Bank Indonesia)",
        "region": "Indonesia",
        "impact": "Sedang",
        "event_date": "2026-10-07",
        "time_wib": "10:00 WIB",
        "forecast": "USD 151.0 Miliar",
        "previous": "USD 150.2 Miliar",
        "actual": "Menunggu",
        "notes": "Amunisi BI dalam melakukan intervensi triple intervention di pasar spot, DNDF, dan SBN."
    }
]

def sync_calendar():
    with DBContext(commit=True) as cursor:
        for ev in DEFAULT_CALENDAR_EVENTS:
            cursor.execute("SELECT id FROM macro.economic_calendar WHERE event_name = %s AND event_date = %s", (ev["event_name"], ev["event_date"]))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                INSERT INTO macro.economic_calendar (event_name, region, impact, event_date, time_wib, forecast, previous, actual, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ev["event_name"], ev["region"], ev["impact"], ev["event_date"],
                    ev["time_wib"], ev["forecast"], ev["previous"], ev["actual"], ev["notes"]
                ))
    logger.info("Economic calendar synchronized with PostgreSQL.")

def update_macro_briefing():
    now_iso = datetime.now(timezone.utc).isoformat()
    
    with DBContext(commit=True) as cursor:
        cursor.execute("SELECT key, value, unit, trend, change_pct FROM macro.indicators")
        ind_dict = {row["key"]: dict(row) for row in cursor.fetchall()}
        
        usd_idr = ind_dict.get("USD_IDR", {}).get("value", 17900)
        bi_rate = ind_dict.get("BI_RATE", {}).get("value", 6.00)
        dxy = ind_dict.get("DXY", {}).get("value", 100.9)
        us_10y = ind_dict.get("US_10Y", {}).get("value", 5.18)
        gold = ind_dict.get("GOLD", {}).get("value", 4325)
        brent = ind_dict.get("BRENT_OIL", {}).get("value", 97.5)
        
        headline = "Tekanan DXY & Yield Obligasi Global Mengharuskan Stabilitas Moneter Domestik yang Disiplin"
        
        summary_indo = f"""
1. **Kebijakan Moneter & Stabilitas Rupiah**:
   Nilai tukar Rupiah berada di kisaran Rp {usd_idr:,.0f} per USD di tengah tingginya yield US Treasury 10-Year ({us_10y:.2f}%). Bank Indonesia mempertahankan BI-Rate pada level {bi_rate:.2f}% dengan strategi *triple intervention* (pasar spot, DNDF, dan pembelian SBN di pasar sekunder) serta optimalisasi instrumen SRBI (Sekuritas Rupiah Bank Indonesia) untuk menyerap likuiditas valas dan menjaga *interest rate differential*.
2. **Kinerja Fiskal & Makro Riil**:
   Neraca perdagangan nasional tetap mempertahankan tren surplus ditopang oleh kinerja ekspor komoditas CPO dan hilirisasi nikel, meskipun harga minyak mentah Brent bertengger di USD {brent:.1f}/barel yang berpotensi menambah beban kompensasi energi APBN. Inflasi domestik berada pada rentang terkendali 1.71% YoY, memberikan ruang manuver fiskal yang sehat bagi akselerasi belanja infrastruktur dan perlindungan sosial.
        """.strip()
        
        summary_global = f"""
1. **Dinamika Kebijakan The Fed & Dollar Index**:
   Indeks Dolar AS (DXY) bertahan di level {dxy:.2f}, mencerminkan sikap pasar yang mencermati retorika pejabat Federal Reserve terkait batas akhir siklus pelonggaran suku bunga. Kekhawatiran divergensi moneter antara AS dan kawasan Eropa (ECB) menahan penguatan mata uang pasar berkembang (Emerging Markets).
2. **Pasar Komoditas & Aset Lindung Nilai**:
   Emas internasional bergerak di level rekor sekitar USD {gold:,.1f}/troy ounce, didorong oleh akumulasi cadangan emas oleh bank-bank sentral global serta lindung nilai terhadap risiko fragmentasi geopolitik dan volatilitas tarif perdagangan global.
        """.strip()
        
        key_risks = "Volatilitas harga energi global, ketegangan geopolitik Timur Tengah & Selat Taiwan, potensi tarif proteksionisme dagang baru, serta pergeseran likuiditas global ke aset berdenominasi Dolar AS."
        market_sentiment = "Cautious Neutral / Selective Defensive"
        
        cursor.execute("""
        INSERT INTO macro.macro_briefing (id, headline, summary_indo, summary_global, key_risks, market_sentiment, updated_at)
        VALUES (1, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            headline = EXCLUDED.headline,
            summary_indo = EXCLUDED.summary_indo,
            summary_global = EXCLUDED.summary_global,
            key_risks = EXCLUDED.key_risks,
            market_sentiment = EXCLUDED.market_sentiment,
            updated_at = EXCLUDED.updated_at
        """, (headline, summary_indo, summary_global, key_risks, market_sentiment, now_iso))
        
    logger.info("Macro briefing updated in PostgreSQL.")

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    sync_calendar()
    update_macro_briefing()
    print("Calendar and briefing synchronized successfully.")
