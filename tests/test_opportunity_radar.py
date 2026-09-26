"""
QA Verification Test Suite — Opportunity & Action Radar Engine
Agent: QA-synt-wrkdr-1
Target: TASK-003 (Macro Regime, Asset Impact Matrix, Winners & Losers, Actionable Decisions)
Framework: Python unittest + FastAPI TestClient
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database import DBContext, init_db
from app.security import create_session
from app.collectors.opportunity_radar import (
    build_opportunity_radar,
    get_opportunity_radar_data,
    evaluate_macro_regime,
    calculate_asset_impact_matrix,
    identify_winners_and_losers,
    generate_actionable_decisions
)
from app.collectors.cross_asset import get_latest_indicators

class TestOpportunityRadar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Inisialisasi database dan TestClient."""
        init_db()
        cls.client = TestClient(app)
        cls.token = create_session("syant")
        cls.client.cookies.set("macro_session", cls.token)

    def test_01_regime_evaluation(self):
        """Uji algoritma deteksi rezim makroekonomi."""
        indicators = get_latest_indicators()
        regime = evaluate_macro_regime(indicators)
        
        self.assertIn("regime_id", regime)
        self.assertIn(regime["regime_id"], ["EXPANSIVE", "STAGNANT", "INFLATIONARY_SHOCK", "TIGHTENING"])
        self.assertIn("name", regime)
        self.assertIn("description", regime)
        self.assertIn("primary_recommendation", regime)
        self.assertIn("metrics", regime)

    def test_02_asset_impact_matrix(self):
        """Uji kalkulasi matriks dampak aset makroekonomi."""
        indicators = get_latest_indicators()
        matrix = calculate_asset_impact_matrix("TIGHTENING", indicators)
        
        self.assertGreaterEqual(len(matrix), 5)
        for item in matrix:
            self.assertIn("asset", item)
            self.assertIn("category", item)
            self.assertTrue(-100 <= item["score"] <= 100)
            self.assertIn(item["stance"], ["OVERWEIGHT", "SELECTIVE_BUY", "MODERATE_BUY", "NEUTRAL", "HOLD", "UNDERWEIGHT"])
            self.assertIn("driver", item)

    def test_03_winners_and_losers(self):
        """Uji identifikasi sektor winners vs losers."""
        indicators = get_latest_indicators()
        entities = identify_winners_and_losers("TIGHTENING", indicators)
        
        self.assertIn("winners", entities)
        self.assertIn("losers", entities)
        self.assertGreaterEqual(len(entities["winners"]), 2)
        self.assertGreaterEqual(len(entities["losers"]), 2)
        
        for w in entities["winners"]:
            self.assertIn("sector", w)
            self.assertIn("reason", w)
            self.assertIn("impact_tag", w)

    def test_04_actionable_decisions(self):
        """Uji perumusan keputusan praktis finansial, trading, dan bisnis riil."""
        indicators = get_latest_indicators()
        actions = generate_actionable_decisions("TIGHTENING", indicators)
        
        self.assertIn("financial_living", actions)
        self.assertIn("trading_investment", actions)
        self.assertIn("real_business", actions)
        
        self.assertGreaterEqual(len(actions["financial_living"]), 2)
        self.assertGreaterEqual(len(actions["trading_investment"]), 2)
        self.assertGreaterEqual(len(actions["real_business"]), 2)

    def test_05_build_and_persist_radar(self):
        """Uji build menyeluruh dan persistensi ke PostgreSQL."""
        radar = build_opportunity_radar()
        self.assertEqual(radar["status"], "active")
        self.assertIn("regime", radar)
        self.assertIn("asset_impact_matrix", radar)
        self.assertIn("winners_and_losers", radar)
        self.assertIn("actionable_decisions", radar)
        
        # Ambil kembali dari storage
        stored = get_opportunity_radar_data()
        self.assertEqual(stored["regime"]["regime_id"], radar["regime"]["regime_id"])

    def test_06_api_opportunity_radar_endpoint(self):
        """Uji HTTP GET /api/opportunity-radar."""
        res = self.client.get("/api/opportunity-radar")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("radar", data)
        self.assertIn("regime", data["radar"])
        self.assertIn("asset_impact_matrix", data["radar"])

    def test_07_api_indicators_includes_radar(self):
        """Uji HTTP GET /api/indicators nexus payload menyertakan opportunity_radar."""
        res = self.client.get("/api/indicators")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("nexus", data)
        self.assertIn("opportunity_radar", data["nexus"])
        self.assertIn("regime", data["nexus"]["opportunity_radar"])

if __name__ == "__main__":
    unittest.main()
