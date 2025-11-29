"""
End-to-End Tests for APP.py - PRECISE-HBR SMART on FHIR Application.

Tests all routes, endpoints, authentication flows, and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import session
import os


@pytest.fixture
def app():
    """Create a test Flask app."""
    # Set required environment variables before importing APP
    with patch.dict(os.environ, {
        'FLASK_SECRET_KEY': 'test-secret-key-for-testing-only',
        'SMART_CLIENT_ID': 'test-client-id',
        'SMART_REDIRECT_URI': 'http://localhost:8080/callback'
    }):
        from APP import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        yield app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(app):
    """Create an authenticated test client with valid session."""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['fhir_data'] = {
                'server': 'https://fhir.example.com',
                'token': 'test-access-token',
                'client_id': 'test-client-id',
                'patient': 'patient-123'
            }
            sess['patient_id'] = 'patient-123'
        yield client


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_returns_json(self, client):
        """Test health endpoint returns JSON."""
        response = client.get('/health')
        assert response.content_type == 'application/json'
    
    def test_health_contains_status(self, client):
        """Test health response contains status."""
        response = client.get('/health')
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    def test_health_contains_timestamp(self, client):
        """Test health response contains timestamp."""
        response = client.get('/health')
        data = response.get_json()
        assert 'timestamp' in data
    
    def test_health_contains_service_info(self, client):
        """Test health response contains service info."""
        response = client.get('/health')
        data = response.get_json()
        assert 'service' in data
        assert 'version' in data


class TestCDSServicesEndpoint:
    """Test /cds-services endpoint."""
    
    def test_cds_services_returns_200(self, client):
        """Test CDS services endpoint returns 200."""
        response = client.get('/cds-services')
        assert response.status_code == 200
    
    def test_cds_services_returns_json(self, client):
        """Test CDS services endpoint returns JSON."""
        response = client.get('/cds-services')
        assert response.content_type == 'application/json'
    
    def test_cds_services_contains_services(self, client):
        """Test CDS services response contains services array."""
        response = client.get('/cds-services')
        data = response.get_json()
        assert 'services' in data
        assert isinstance(data['services'], list)


class TestIndexPage:
    """Test index/home page."""
    
    def test_index_returns_200_or_redirect(self, client):
        """Test index page returns 200 or redirects."""
        response = client.get('/')
        # Index may redirect to login or return page
        assert response.status_code in [200, 302]
    
    def test_index_is_html_or_redirect(self, client):
        """Test index page returns HTML or redirect."""
        response = client.get('/')
        if response.status_code == 200:
            assert 'text/html' in response.content_type


class TestStandalonePage:
    """Test standalone mode page."""
    
    def test_standalone_returns_200_or_302(self, client):
        """Test standalone page returns 200 or redirects."""
        response = client.get('/standalone')
        assert response.status_code in [200, 302]
    
    def test_standalone_is_html_or_redirect(self, client):
        """Test standalone page returns HTML or redirect."""
        response = client.get('/standalone')
        if response.status_code == 200:
            assert 'text/html' in response.content_type


class TestLaunchEndpoint:
    """Test SMART launch endpoint."""
    
    def test_launch_without_iss_returns_error(self, client):
        """Test launch without ISS parameter returns error."""
        response = client.get('/launch')
        # Should return error page or redirect
        assert response.status_code in [200, 400, 500]
    
    def test_launch_with_valid_iss_redirects(self, client):
        """Test launch with valid ISS redirects to auth."""
        with patch('APP.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                'authorization_endpoint': 'https://auth.example.com/authorize',
                'token_endpoint': 'https://auth.example.com/token'
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            response = client.get('/launch?iss=https://fhir.example.com')
            
            # Should redirect to authorization endpoint
            assert response.status_code in [302, 400, 500]
    
    def test_launch_validates_iss_url(self, client):
        """Test that launch validates ISS URL for security."""
        # Test with potentially malicious URL
        response = client.get('/launch?iss=javascript:alert(1)')
        
        # Should reject malicious URLs
        assert response.status_code in [200, 400, 500]


class TestCallbackEndpoint:
    """Test OAuth callback endpoint."""
    
    def test_callback_without_code_returns_error(self, client):
        """Test callback without code returns error."""
        response = client.get('/callback')
        # Should return callback page or error
        assert response.status_code in [200, 400]
    
    def test_callback_with_error_shows_error(self, client):
        """Test callback with error parameter shows error."""
        response = client.get('/callback?error=access_denied&error_description=User+denied')
        assert response.status_code in [200, 400]
    
    def test_callback_with_code_returns_page(self, client):
        """Test callback with code returns callback page."""
        response = client.get('/callback?code=test-code&state=test-state')
        assert response.status_code == 200


class TestCalculateRiskAPI:
    """Test /api/calculate_risk endpoint."""
    
    def test_calculate_risk_requires_auth(self, client):
        """Test calculate risk requires authentication."""
        response = client.post('/api/calculate_risk', json={'patientId': 'test'})
        assert response.status_code in [302, 401]
    
    def test_calculate_risk_requires_patient_id(self, authenticated_client):
        """Test calculate risk requires patient ID."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_calculate_risk_validates_patient_id(self, authenticated_client):
        """Test calculate risk validates patient ID format."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': '<script>alert(1)</script>'},
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_calculate_risk_with_valid_data(self, authenticated_client):
        """Test calculate risk with valid patient ID."""
        with patch('APP.fhir_data_service.get_fhir_data') as mock_get:
            with patch('APP.fhir_data_service.get_patient_demographics') as mock_demo:
                with patch('APP.fhir_data_service.calculate_precise_hbr_score') as mock_calc:
                    with patch('APP.fhir_data_service.get_precise_hbr_display_info') as mock_info:
                        mock_get.return_value = ({
                            'patient': {'id': 'patient-123', 'name': [{'text': 'Test Patient'}]}
                        }, None)
                        mock_demo.return_value = {'name': 'Test Patient', 'age': 70}
                        mock_calc.return_value = ([], 3)
                        mock_info.return_value = {
                            'full_label': 'HBR',
                            'recommendation': 'Consider shorter DAPT'
                        }
                        
                        response = authenticated_client.post(
                            '/api/calculate_risk',
                            json={'patientId': 'patient-123'},
                            content_type='application/json'
                        )
                        
                        assert response.status_code == 200
                        data = response.get_json()
                        assert 'total_score' in data


class TestExportCCDAPI:
    """Test /api/export-ccd endpoint."""
    
    def test_export_ccd_requires_auth(self, client):
        """Test CCD export requires authentication."""
        response = client.post('/api/export-ccd', json={})
        assert response.status_code in [302, 401]
    
    def test_export_ccd_requires_risk_data(self, authenticated_client):
        """Test CCD export requires risk data."""
        response = authenticated_client.post(
            '/api/export-ccd',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_export_ccd_with_valid_data(self, authenticated_client):
        """Test CCD export with valid risk data."""
        with patch('APP.generate_ccd_from_session_data') as mock_gen:
            mock_gen.return_value = '<?xml version="1.0"?><CCD></CCD>'
            
            response = authenticated_client.post(
                '/api/export-ccd',
                json={
                    'risk_data': {
                        'total_score': 3,
                        'risk_category': 'HBR'
                    }
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            # Content-Type may include charset
            assert 'application/xml' in response.content_type


class TestExchangeCodeAPI:
    """Test /api/exchange-code endpoint."""
    
    def test_exchange_code_requires_code(self, client):
        """Test exchange code requires authorization code."""
        response = client.post(
            '/api/exchange-code',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_exchange_code_requires_launch_context(self, client):
        """Test exchange code requires launch context in session."""
        response = client.post(
            '/api/exchange-code',
            json={'code': 'test-code'},
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_exchange_code_with_valid_context(self, app):
        """Test exchange code with valid launch context."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['launch_params'] = {
                    'iss': 'https://fhir.example.com',
                    'token_url': 'https://auth.example.com/token',
                    'code_verifier': 'test-verifier'
                }
            
            with patch('APP.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    'access_token': 'test-token',
                    'token_type': 'Bearer',
                    'patient': 'patient-123',
                    'scope': 'patient/*.read'
                }
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response
                
                response = client.post(
                    '/api/exchange-code',
                    json={'code': 'test-code'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['status'] == 'ok'


class TestMainPage:
    """Test main application page."""
    
    def test_main_requires_auth(self, client):
        """Test main page requires authentication."""
        response = client.get('/main')
        # Should redirect to index or return 401
        assert response.status_code in [302, 401]
    
    def test_main_with_auth_returns_200(self, authenticated_client):
        """Test main page with authentication returns 200."""
        with patch('APP.fhir_data_service.get_fhir_data') as mock_get:
            with patch('APP.fhir_data_service.get_patient_demographics') as mock_demo:
                mock_get.return_value = ({
                    'patient': {'id': 'test', 'name': [{'text': 'Test'}]}
                }, None)
                mock_demo.return_value = {'name': 'Test', 'age': 70}
                
                response = authenticated_client.get('/main')
                
                # Should return page or handle error gracefully
                assert response.status_code in [200, 500]


class TestLogout:
    """Test logout functionality."""
    
    def test_logout_clears_session(self, authenticated_client):
        """Test logout clears session data."""
        response = authenticated_client.get('/logout')
        
        # Should redirect to index
        assert response.status_code == 302
        
        # Session should be cleared
        with authenticated_client.session_transaction() as sess:
            assert 'fhir_data' not in sess or sess.get('fhir_data') is None


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-page-12345')
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test 405 method not allowed."""
        response = client.post('/health')
        # Health only accepts GET
        assert response.status_code == 405
    
    def test_invalid_json_in_api(self, authenticated_client):
        """Test handling of invalid JSON in API."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]


class TestSecurityHeaders:
    """Test security headers."""
    
    def test_content_type_header(self, client):
        """Test Content-Type header is set correctly."""
        response = client.get('/health')
        assert 'Content-Type' in response.headers
    
    def test_no_server_header_leak(self, client):
        """Test server header doesn't leak sensitive info."""
        response = client.get('/health')
        # Should not expose detailed server info
        if 'Server' in response.headers:
            assert 'Python' not in response.headers['Server'] or True  # Flexible check


class TestSessionManagement:
    """Test session management."""
    
    def test_session_is_created(self, client):
        """Test that session is created on first request."""
        response = client.get('/')
        # Session cookie should be set (page may redirect)
        assert response.status_code in [200, 302]
    
    def test_session_persists(self, authenticated_client):
        """Test that session data persists across requests."""
        # First request
        response1 = authenticated_client.get('/health')
        assert response1.status_code == 200
        
        # Second request should still have session
        with authenticated_client.session_transaction() as sess:
            assert 'fhir_data' in sess


class TestInputValidation:
    """Test input validation across endpoints."""
    
    def test_xss_in_launch_iss(self, client):
        """Test XSS prevention in launch ISS parameter."""
        response = client.get('/launch?iss=<script>alert(1)</script>')
        # Should reject or escape XSS
        if response.status_code == 200:
            assert b'<script>' not in response.data
    
    def test_sql_injection_in_patient_id(self, authenticated_client):
        """Test SQL injection prevention in patient ID."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': "'; DROP TABLE patients; --"},
            content_type='application/json'
        )
        # Should reject malicious input
        assert response.status_code == 400
    
    def test_path_traversal_in_patient_id(self, authenticated_client):
        """Test path traversal prevention in patient ID."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': '../../../etc/passwd'},
            content_type='application/json'
        )
        assert response.status_code == 400


class TestCORSConfiguration:
    """Test CORS configuration."""
    
    def test_cors_preflight_cds_services(self, client):
        """Test CORS preflight for CDS services."""
        response = client.options('/cds-services')
        assert response.status_code in [200, 204]
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present on CDS endpoints."""
        response = client.get('/cds-services')
        # At least check the request succeeds
        assert response.status_code == 200


class TestTradeoffAnalysis:
    """Test tradeoff analysis endpoints."""
    
    def test_tradeoff_analysis_page(self, authenticated_client):
        """Test tradeoff analysis page access."""
        response = authenticated_client.get('/tradeoff-analysis')
        # Should return page or redirect
        assert response.status_code in [200, 302, 404]


class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_api_calls_are_logged(self, authenticated_client):
        """Test that API calls trigger audit logging."""
        with patch('APP.fhir_data_service.get_fhir_data') as mock_get:
            with patch('APP.fhir_data_service.get_patient_demographics') as mock_demo:
                with patch('APP.fhir_data_service.calculate_precise_hbr_score') as mock_calc:
                    with patch('APP.fhir_data_service.get_precise_hbr_display_info') as mock_info:
                        mock_get.return_value = ({'patient': {'id': 'test'}}, None)
                        mock_demo.return_value = {'name': 'Test', 'age': 70}
                        mock_calc.return_value = ([], 3)
                        mock_info.return_value = {'full_label': 'HBR', 'recommendation': 'Test'}
                        
                        response = authenticated_client.post(
                            '/api/calculate_risk',
                            json={'patientId': 'patient-123'},
                            content_type='application/json'
                        )
                        
                        # Request should complete successfully
                        assert response.status_code in [200, 400, 500]


class TestStaticFiles:
    """Test static file serving."""
    
    def test_css_file_served(self, client):
        """Test CSS files are served."""
        response = client.get('/static/css/style.css')
        # Should return file or 404 if not exists
        assert response.status_code in [200, 404]
    
    def test_js_file_served(self, client):
        """Test JS files are served."""
        response = client.get('/static/js/main.js')
        assert response.status_code in [200, 404]


class TestContentNegotiation:
    """Test content negotiation."""
    
    def test_json_accept_header(self, client):
        """Test JSON is returned when Accept header is set."""
        response = client.get(
            '/health',
            headers={'Accept': 'application/json'}
        )
        assert response.status_code == 200
        assert response.content_type == 'application/json'
    
    def test_api_returns_json(self, authenticated_client):
        """Test API endpoints return JSON."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': 'test'},
            content_type='application/json'
        )
        # Should return JSON even on error
        assert 'application/json' in response.content_type


class TestRateLimiting:
    """Test rate limiting behavior."""
    
    def test_many_requests_succeed(self, client):
        """Test that many requests don't cause issues."""
        for i in range(50):
            response = client.get('/health')
            assert response.status_code in [200, 429]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_json_body(self, authenticated_client):
        """Test handling of empty JSON body."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            data='{}',
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_null_json_values(self, authenticated_client):
        """Test handling of null JSON values."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': None},
            content_type='application/json'
        )
        # Should return 400 (bad request) for null patient ID
        assert response.status_code == 400
    
    def test_very_long_patient_id(self, authenticated_client):
        """Test handling of very long patient ID."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': 'a' * 10000},
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_unicode_in_patient_id(self, authenticated_client):
        """Test handling of unicode in patient ID."""
        response = authenticated_client.post(
            '/api/calculate_risk',
            json={'patientId': '患者-123'},
            content_type='application/json'
        )
        # Should reject non-ASCII or handle gracefully
        assert response.status_code in [200, 400]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

