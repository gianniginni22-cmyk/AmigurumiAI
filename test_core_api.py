import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestCoreAPI(unittest.TestCase):
    def test_generate_endpoint_exists(self):
        routes={r.path for r in app.routes}
        self.assertIn('/api/generate', routes)

    def test_generate_endpoint_returns_compiled_pattern_in_local_mode(self):
        import app.main as main_mod
        original = main_mod.get_api_key
        main_mod.get_api_key = lambda: ''
        try:
            client = TestClient(main_mod.app)
            response = client.post('/api/generate', data={'description':'castoro antropomorfo','height_cm':'15','hook_mm':'2.5'})
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload.get('stage'), 'compiled')
            result = payload.get('result') or {}
            self.assertTrue(result.get('pattern', '').strip())
            self.assertTrue(result.get('assembly', '').strip())
            self.assertGreater((result.get('generation_trace') or {}).get('pattern_chars', 0), 0)
        finally:
            main_mod.get_api_key = original

    def test_ui_exposes_pipeline_diagnostic_and_build_fingerprint(self):
        from pathlib import Path
        import app.main as main_mod
        html = (main_mod.STATIC / 'index.html').read_text(encoding='utf-8')
        self.assertIn('pipelineDiag', html)
        self.assertIn('build 0.7.4-DIAG', html)
        self.assertIn('r.dimensions||r.global_dimensions||{}', html)
        self.assertIn('Pattern non disponibile: la compilazione non ha prodotto istruzioni.', html)

if __name__ == '__main__': unittest.main()


class TestUIDataContract(unittest.TestCase):
    def test_compile_design_exposes_displayable_part_names(self):
        from app.crochet_engine.design_model import fallback_design
        from app.crochet_engine.pipeline import compile_design
        design = fallback_design('castoro antropomorfo', 15, 'fedele alla foto')
        out = compile_design(design, 15, 2.5)
        self.assertIsInstance(out.get('parts'), list)
        self.assertTrue(all(isinstance(x, str) for x in out['parts']))
        self.assertTrue(out.get('pattern', '').strip())
        self.assertTrue(out.get('assembly', '').strip())
