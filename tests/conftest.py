"""
Pytest configuration and fixtures for PRECISE-HBR tests
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Register IEC 62304 regulatory traceability plugin
pytest_plugins = ["tests.regulatory_plugin"]

# Exclude tests requiring optional dependencies (e.g., selenium)
collect_ignore_glob = ["verify_web_parallel.py"]

# Add parent directory to path
import os
import sys

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture
def app():
    """Create and configure a Flask app instance for testing."""
    # Set testing environment variables
    # Use patch.dict to set environment variables for the duration of the test
    with patch.dict(os.environ, {
        'TESTING': 'True',
        'FLASK_ENV': 'testing',
        'FLASK_SECRET_KEY': 'test-secret-key-for-testing-only',  # Fix: Set FLASK_SECRET_KEY
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'SMART_CLIENT_ID': 'test-client-id',
        'SMART_CLIENT_SECRET': 'test-client-secret',
        'SMART_REDIRECT_URI': 'http://localhost:8080/callback',
        'SMART_EHR_BASE_URL': 'https://fhir.example.com'
    }):
    
        # Mock Google Cloud Secret Manager
        with patch('services.app_config.HAS_SECRET_MANAGER', False):
            # Import APP here to ensure env vars are set before import
            from APP import app as flask_app
            
            flask_app.config.update({
                'TESTING': True,
                'WTF_CSRF_ENABLED': False,
                'SESSION_TYPE': 'filesystem',
            })
            
            yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_fhir_client():
    """Mock FHIR client for testing."""
    mock_client = MagicMock()
    mock_client.server = MagicMock()
    mock_client.server.base_uri = 'https://fhir.example.com'
    return mock_client


@pytest.fixture
def mock_patient_data():
    """Mock patient data for testing."""
    return {
        'resourceType': 'Patient',
        'id': 'test-patient-123',
        'name': [{'family': 'Test', 'given': ['Patient']}],
        'gender': 'male',
        'birthDate': '1970-01-01'
    }


@pytest.fixture
def mock_observation_data():
    """Mock observation data for testing."""
    return {
        'resourceType': 'Observation',
        'id': 'test-obs-123',
        'status': 'final',
        'code': {
            'coding': [{
                'system': 'http://loinc.org',
                'code': '718-7',
                'display': 'Hemoglobin'
            }]
        },
        'valueQuantity': {
            'value': 10.5,
            'unit': 'g/dL'
        }
    }


@pytest.fixture
def mock_hbr_criteria():
    """Mock HBR criteria for testing."""
    return {
        'major_criteria': [
            {
                'id': 'age',
                'name': 'Age ≥75 years',
                'met': True,
                'value': 76
            }
        ],
        'minor_criteria': [
            {
                'id': 'anemia',
                'name': 'Hemoglobin <11 g/dL',
                'met': True,
                'value': 10.5
            }
        ]
    }




