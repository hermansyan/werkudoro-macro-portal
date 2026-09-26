"""
QA Verification Test Suite — Cross-Asset Collector & Analytics Engine
Agent: QA-synt-wrkdr-1
Target: TASK-002 (Gold & Real Yields, Crypto Liquidity, Commodity & Indo Export Engine)
Framework: Python unittest (Stdlib native) + FastAPI TestClient
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database import DBContext, init_db
from app.security import create_session
from app.collectors.cross_asset import (
    sync_cross_asset,
    get_cross_asset_summary,
    analyze_gold_real_yields,
    analyze_crypto_macro_liquidity,
    analyze_commodity_export_ri
)

class TestCrossAssetCollector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Inisialisasi database dan TestClient."""
        init_db()
        cls.client = TestClient(app)
        cls.token = create_session("syant")
        cls.client.cookies.set("macro_session", cls.token)

    def test_01_cross_asset_calculation_and_sync(self):
        """Verifikasi eksekusi kalkulasi indikator lintas aset dan persistensi ke DB."""
        analyses = sync_cross_asset()
        self.assertEqual(len(analyses), 3, f"Harus ada 3 domain analisis cross-asset, ditemukan {len(analyses)}")
        
        ids = {item["id"] for item in analyses}
        self.assertIn("gold_real_yields", ids)
        self.assertIn("crypto_macro_liquidity", ids)
        self.assertIn("commodity_export_ri", ids)

    def test_02_cross_asset_database_retrieval(self):
        """Verifikasi pembacaan dari tabel macro.cross_asset_analytics di PostgreSQL."""
        data = get_cross_asset_summary()
        self.assertIn("gold_real_yields", data)
        self.assertIn("crypto_macro_liquidity", data)
        self.assertIn("commodity_export_ri", data)
        
        # 1. Gold & Real Yields
        gold = data["gold_real_yields"]
        self.assertGreater(gold["metrics"]["gold_price_usd"], 1000.0)
        self.assertIn("us_10y_real_yield", gold["metrics"])
        self.assertGreaterEqual(len(gold["insights"]), 3)
        self.assertIn(gold["signal"], ["STRUCTURAL_DEBASEMENT_ACCUMULATION", "BEARISH_REAL_RATE_DRAG", "BULLISH_SAFE_HAVEN"])
        
        # 2. Crypto Macro Liquidity
        crypto = data["crypto_macro_liquidity"]
        self.assertGreater(crypto["metrics"]["btc_price_usd"], 10000.0)
        self.assertGreater(crypto["metrics"]["eth_price_usd"], 500.0)
        self.assertGreater(crypto["metrics"]["eth_btc_ratio"], 0.0)
        self.assertTrue(0 <= crypto["metrics"]["global_liquidity_score"] <= 100)
        self.assertIn(crypto["signal"], ["EXPANSIVE_RISK_ON", "BITCOIN_DOMINANCE_DEFENSIVE", "LIQUIDITY_CONTRACTION", "NEUTRAL_CONSOLIDATION"])
        
        # 3. Commodity Export RI
        comm = data["commodity_export_ri"]
        self.assertGreater(comm["metrics"]["brent_oil_usd"], 30.0)
        self.assertGreater(comm["metrics"]["coal_newcastle_usd"], 50.0)
        self.assertGreater(comm["metrics"]["cpo_price_myr"], 1000.0)
        self.assertIn("oil_subsidy_delta_usd", comm["metrics"])
        self.assertTrue(0 <= comm["metrics"]["terms_of_trade_score"] <= 100)
        self.assertGreaterEqual(len(comm["insights"]), 4)

    def test_03_api_cross_asset_endpoint(self):
        """Verifikasi GET /api/cross-asset mengembalikan respons 200 OK dengan payload valid."""
        res = self.client.get("/api/cross-asset")
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertEqual(json_data["status"], "ok")
        self.assertIn("gold_real_yields", json_data["data"])
        self.assertIn("crypto_macro_liquidity", json_data["data"])
        self.assertIn("commodity_export_ri", json_data["data"])

    def test_04_api_indicators_includes_cross_asset(self):
        """Verifikasi GET /api/indicators menyertakan cross_asset dalam blok nexus."""
        res = self.client.get("/api/indicators")
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertIn("nexus", json_data)
        nexus = json_data["nexus"]
        self.assertIn("cross_asset", nexus)
        self.assertIn("gold_real_yields", nexus["cross_asset"])
        self.assertIn("crypto_macro_liquidity", nexus["cross_asset"])
        self.assertIn("commodity_export_ri", nexus["cross_asset"])

if __name__ == "__main__":
    unittest.main()
