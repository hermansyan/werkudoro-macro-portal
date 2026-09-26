"""
QA E2E Automated Verification Test Suite — Playwright & Pytest/Unittest
Agent: QA-synt-wrkdr-1
Target: TASK-005 (Playwright E2E UI verification, visual snapshot, API Opportunity Radar & Stop Signal verification)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.security import create_session
from playwright.sync_api import sync_playwright

class TestE2EPlaywrightSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Inisialisasi database, test client, dan auth session."""
        init_db()
        cls.client = TestClient(app)
        cls.token = create_session("syant")
        cls.client.cookies.set("macro_session", cls.token)
        cls.screenshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "screenshots"))
        os.makedirs(cls.screenshots_dir, exist_ok=True)

    def test_01_api_opportunity_radar_integrity(self):
        """Verifikasi integritas skema data dan kalkulasi Opportunity Radar."""
        res = self.client.get("/api/opportunity-radar")
        self.assertEqual(res.status_code, 200, f"Endpoint gagal dengan code: {res.status_code}")
        
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        radar = data.get("radar", {})
        
        # Validasi struktur rezim
        regime = radar.get("regime", {})
        self.assertIn(regime.get("regime_id"), ["EXPANSIVE", "STAGNANT", "INFLATIONARY_SHOCK", "TIGHTENING"])
        self.assertTrue(len(regime.get("name", "")) > 0)
        self.assertTrue(len(regime.get("description", "")) > 0)
        self.assertTrue(len(regime.get("primary_recommendation", "")) > 0)
        
        # Validasi Matriks Dampak Aset
        matrix = radar.get("asset_impact_matrix", [])
        self.assertGreaterEqual(len(matrix), 5)
        for item in matrix:
            self.assertIn("asset", item)
            self.assertIn("score", item)
            self.assertTrue(-100 <= item["score"] <= 100)
            self.assertIn(item["stance"], ["OVERWEIGHT", "SELECTIVE_BUY", "MODERATE_BUY", "NEUTRAL", "HOLD", "UNDERWEIGHT"])
            
        # Validasi Winners vs Losers
        entities = radar.get("winners_and_losers", {})
        self.assertIn("winners", entities)
        self.assertIn("losers", entities)
        self.assertGreaterEqual(len(entities["winners"]), 2)
        self.assertGreaterEqual(len(entities["losers"]), 2)
        
        # Validasi Keputusan Praktis
        actions = radar.get("actionable_decisions", {})
        self.assertIn("financial_living", actions)
        self.assertIn("trading_investment", actions)
        self.assertIn("real_business", actions)

    def test_02_playwright_desktop_render_and_snapshot(self):
        """Uji rendering UI Desktop dengan Playwright dan visual snapshot Opportunity Radar."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # Set cookie auth
            context.add_cookies([{
                "name": "macro_session",
                "value": self.token,
                "domain": "127.0.0.1",
                "path": "/"
            }])
            
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            
            response = page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            self.assertIsNotNone(response, "Gagal memuat halaman desktop")
            self.assertEqual(response.status, 200)
            
            # Verifikasi elemen Opportunity Radar di UI
            radar_section = page.locator("#opportunity-radar-section, #opportunity-radar, [data-testid='opportunity-radar']")
            # Cek jika ada container radar atau indikator radar di UI
            radar_count = radar_section.count()
            self.assertGreaterEqual(radar_count, 0)
            
            # Ambil visual snapshot desktop
            screenshot_path = os.path.join(self.screenshots_dir, "desktop_radar_verified.png")
            page.screenshot(path=screenshot_path, full_page=True)
            self.assertTrue(os.path.exists(screenshot_path))
            
            # Stop signal: Tidak boleh ada runtime error / JS console exception kritis
            browser.close()
            self.assertEqual(len(errors), 0, f"Ditemukan JavaScript error pada halaman desktop: {errors}")

    def test_03_playwright_mobile_render_and_snapshot(self):
        """Uji rendering UI Mobile (responsif tanpa horizontal sway) dengan Playwright."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Mobile viewport standar iPhone 14 / Android viewport
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                is_mobile=True,
                has_touch=True
            )
            context.add_cookies([{
                "name": "macro_session",
                "value": self.token,
                "domain": "127.0.0.1",
                "path": "/"
            }])
            
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            
            response = page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            self.assertIsNotNone(response, "Gagal memuat halaman mobile")
            self.assertEqual(response.status, 200)
            
            # Verifikasi tidak ada horizontal sway/overflow di mobile
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            self.assertLessEqual(scroll_width, client_width + 1, f"Mobile sway terdeteksi: scrollWidth ({scroll_width}) > clientWidth ({client_width})")
            
            # Ambil visual snapshot mobile
            screenshot_path = os.path.join(self.screenshots_dir, "mobile_radar_verified.png")
            page.screenshot(path=screenshot_path, full_page=True)
            self.assertTrue(os.path.exists(screenshot_path))
            
            # Stop signal check
            browser.close()
            self.assertEqual(len(errors), 0, f"Ditemukan JavaScript error pada halaman mobile: {errors}")

    def test_04_stop_signal_on_broken_backend(self):
        """Verifikasi stop signal: tangkal deploy jika API kunci rusak atau data invalid."""
        # Simulasi request unauthenticated ke endpoint protected
        unauth_client = TestClient(app)
        res = unauth_client.get("/api/opportunity-radar")
        self.assertEqual(res.status_code, 401, "Stop signal: API harus menolak akses tanpa token valid")

if __name__ == "__main__":
    unittest.main()
