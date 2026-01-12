"""
Pytest configuration and fixtures for PRECISE-HBR tests
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def app():
    """Create and configure a Flask app instance for testing."""
    # Set testing environment variables
    os.environ['TESTING'] = 'True'
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['SMART_CLIENT_ID'] = 'test-client-id'
    os.environ['SMART_CLIENT_SECRET'] = 'test-client-secret'
    os.environ['SMART_REDIRECT_URI'] = 'http://localhost:8080/callback'
    os.environ['SMART_EHR_BASE_URL'] = 'https://fhir.example.com'
    
    # Mock Google Cloud Secret Manager
    with patch('services.app_config.HAS_SECRET_MANAGER', False):
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


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment after each test."""
    yield
    # Cleanup after test
    for key in ['TESTING', 'FLASK_ENV', 'SECRET_KEY']:
        if key in os.environ:
            del os.environ[key]

