import io
import unittest
import zipfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.main import app, BusinessLead, render_landing_page, zip_site


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_presets(self):
        self.assertEqual(self.client.get('/').json()['status'], 'online')
        presets = self.client.get('/api/industries').json()
        self.assertEqual(len(presets), 8)
        self.assertIn('plumbers', [preset['id'] for preset in presets])

    @patch('backend.main.run_apify_scrape')
    def test_invalid_industries_do_not_call_provider(self, scrape):
        for ids in [[], ['unknown']]:
            self.assertEqual(self.client.post('/api/scrape', json={'industryIds': ids}).status_code, 400)
        scrape.assert_not_called()

    @patch('backend.main.deploy_to_netlify')
    def test_empty_deployment_does_not_call_provider(self, deploy):
        self.assertEqual(self.client.post('/api/deploy', json={'leads': []}).status_code, 400)
        deploy.assert_not_called()

    @patch('backend.main.run_apify_scrape', return_value=[])
    def test_scrape_passes_selected_location(self, scrape):
        response = self.client.post('/api/scrape', json={'industryIds': ['plumbers'], 'locationQuery': 'Cape Town'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['leads'], [])
        scrape.assert_called_once_with('plumbers', 'Cape Town')

    def test_clean_and_generate_content(self):
        cleaned = self.client.post('/api/leads/clean', json={
            'businessName': ' Sample ', 'email': 'INFO@example.com',
            'category': ' Plumbing ', 'location': ' Durban ', 'notes': ' Repairs '
        })
        self.assertEqual(cleaned.status_code, 200)
        self.assertEqual(cleaned.json()['businessName'], 'Sample')
        self.assertEqual(cleaned.json()['email'], 'info@example.com')
        generated = self.client.post('/api/content/generate', json=cleaned.json())
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(len(generated.json()['services']), 3)

    def test_generated_zip_escapes_business_text(self):
        lead = BusinessLead(id='test', sourceIndustryId='plumbers', industryLabel='Plumbers',
                            businessName='<script>alert(1)</script>', category='Plumbing')
        page = render_landing_page(lead, 'Test context')
        self.assertNotIn('<script>alert(1)</script>', page)
        with zipfile.ZipFile(io.BytesIO(zip_site(page))) as archive:
            self.assertEqual(archive.namelist(), ['index.html'])
            self.assertEqual(archive.read('index.html').decode(), page)


if __name__ == '__main__':
    unittest.main()
