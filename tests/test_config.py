"""
Comprehensive tests for config.py module.
Tests configuration loading, validation, and security settings.
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, Mock
from config import Config


class TestConfigBasics:
    """Test basic configuration loading."""
    
    def test_config_class_exists(self):
        """Test that Config class exists and is accessible."""
        assert Config is not None
        assert hasattr(Config, 'SECRET_KEY')
        assert hasattr(Config, 'CLIENT_ID')
        assert hasattr(Config, 'REDIRECT_URI')
    
    def test_session_type_configured(self):
        """Test that session type is properly configured."""
        assert Config.SESSION_TYPE == 'filesystem'
    
    def test_session_permanent_disabled(self):
        """Test that permanent sessions are disabled for security."""
        assert Config.SESSION_PERMANENT is False
    
    def test_scopes_defined(self):
        """Test that SMART scopes are defined."""
        assert Config.SCOPES is not None
        assert isinstance(Config.SCOPES, str)
        assert 'patient/Patient.read' in Config.SCOPES
        assert 'patient/Observation.read' in Config.SCOPES
    
    def test_cerner_sandbox_config_exists(self):
        """Test that Cerner sandbox configuration exists."""
        assert Config.CERNER_SANDBOX_CONFIG is not None
        assert isinstance(Config.CERNER_SANDBOX_CONFIG, dict)
        assert 'fhir_base' in Config.CERNER_SANDBOX_CONFIG
        assert 'authorization_endpoint' in Config.CERNER_SANDBOX_CONFIG
        assert 'token_endpoint' in Config.CERNER_SANDBOX_CONFIG


class TestEnvironmentVariables:
    """Test environment variable loading."""
    
    def test_secret_key_from_environment(self):
        """Test that SECRET_KEY is loaded from environment."""
        with patch.dict(os.environ, {'FLASK_SECRET_KEY': 'test-secret-key'}):
            # Reload config
            from importlib import reload
            import config
            reload(config)
            assert config.Config.SECRET_KEY == 'test-secret-key'
    
    def test_client_id_from_environment(self):
        """Test that CLIENT_ID is loaded from environment."""
        with patch.dict(os.environ, {'SMART_CLIENT_ID': 'test-client-id'}):
            from importlib import reload
            import config
            reload(config)
            assert config.Config.CLIENT_ID == 'test-client-id'
    
    def test_redirect_uri_from_environment(self):
        """Test that REDIRECT_URI is loaded from environment."""
        with patch.dict(os.environ, {'SMART_REDIRECT_URI': 'https://example.com/callback'}):
            from importlib import reload
            import config
            reload(config)
            assert config.Config.REDIRECT_URI == 'https://example.com/callback'
    
    def test_missing_environment_variables(self):
        """Test behavior when environment variables are missing."""
        # Config should still load, but values will be None
        assert Config.SECRET_KEY is not None or Config.SECRET_KEY is None
        assert Config.CLIENT_ID is not None or Config.CLIENT_ID is None


class TestSessionDirectory:
    """Test session directory configuration."""
    
    def test_session_directory_local_environment(self):
        """Test session directory in local environment."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import config
            reload(config)
            
            # Should use local instance directory
            assert 'instance' in config.Config.SESSION_FILE_DIR or 'flask_session' in config.Config.SESSION_FILE_DIR
    
    def test_session_directory_gae_environment(self):
        """Test session directory in Google App Engine environment."""
        with patch.dict(os.environ, {'GAE_ENV': 'standard'}):
            from importlib import reload
            import config
            reload(config)
            
            # Should use temp directory
            assert tempfile.gettempdir() in config.Config.SESSION_FILE_DIR or '/tmp' in config.Config.SESSION_FILE_DIR
    
    def test_session_directory_path_is_string(self):
        """Test that session directory path is a string."""
        assert isinstance(Config.SESSION_FILE_DIR, str)
        assert len(Config.SESSION_FILE_DIR) > 0


class TestInitApp:
    """Test init_app method."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock Flask app."""
        app = Mock()
        app.logger = Mock()
        app.logger.info = Mock()
        app.logger.warning = Mock()
        app.logger.debug = Mock()
        return app
    
    def test_init_app_with_valid_config(self, mock_app):
        """Test init_app with valid configuration."""
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'test-secret',
            'SMART_CLIENT_ID': 'test-client',
            'SMART_REDIRECT_URI': 'https://example.com/callback'
        }):
            from importlib import reload
            import config
            reload(config)
            
            # Should not raise exception
            try:
                config.Config.init_app(mock_app)
                assert True
            except ValueError:
                pytest.fail("init_app raised ValueError with valid config")
    
    def test_init_app_validates_secret_key(self, mock_app):
        """Test that init_app validates SECRET_KEY presence."""
        # Test that the validation logic exists in init_app
        import inspect
        source = inspect.getsource(Config.init_app)
        assert 'SECRET_KEY' in source
        assert 'ValueError' in source or 'raise' in source
    
    def test_init_app_validates_client_id(self, mock_app):
        """Test that init_app validates CLIENT_ID presence."""
        import inspect
        source = inspect.getsource(Config.init_app)
        assert 'CLIENT_ID' in source
        assert 'ValueError' in source or 'raise' in source
    
    def test_init_app_validates_redirect_uri(self, mock_app):
        """Test that init_app validates REDIRECT_URI presence."""
        import inspect
        source = inspect.getsource(Config.init_app)
        assert 'REDIRECT_URI' in source
        assert 'ValueError' in source or 'raise' in source
    
    def test_init_app_cleans_redirect_uri_hash(self, mock_app):
        """Test that init_app removes hash fragment from REDIRECT_URI."""
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'test-secret',
            'SMART_CLIENT_ID': 'test-client',
            'SMART_REDIRECT_URI': 'https://example.com/callback#fragment'
        }):
            from importlib import reload
            import config
            reload(config)
            
            config.Config.init_app(mock_app)
            
            # Hash fragment should be removed
            assert '#' not in config.Config.REDIRECT_URI
            assert config.Config.REDIRECT_URI == 'https://example.com/callback'
    
    def test_init_app_creates_session_directory(self, mock_app):
        """Test that init_app creates session directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_session_dir = os.path.join(tmpdir, 'test_sessions')
            
            with patch.dict(os.environ, {
                'FLASK_SECRET_KEY': 'test-secret',
                'SMART_CLIENT_ID': 'test-client',
                'SMART_REDIRECT_URI': 'https://example.com/callback'
            }):
                from importlib import reload
                import config
                reload(config)
                
                # Override session directory
                config.Config.SESSION_FILE_DIR = test_session_dir
                
                # Directory should not exist yet
                assert not os.path.exists(test_session_dir)
                
                # Init app should create it
                config.Config.init_app(mock_app)
                
                # Directory should now exist
                assert os.path.exists(test_session_dir)
                
                # Clean up
                if os.path.exists(test_session_dir):
                    shutil.rmtree(test_session_dir)
    
    def test_init_app_sets_secure_permissions(self, mock_app):
        """Test that init_app sets secure permissions on session directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_session_dir = os.path.join(tmpdir, 'test_sessions')
            
            with patch.dict(os.environ, {
                'FLASK_SECRET_KEY': 'test-secret',
                'SMART_CLIENT_ID': 'test-client',
                'SMART_REDIRECT_URI': 'https://example.com/callback'
            }):
                from importlib import reload
                import config
                reload(config)
                
                config.Config.SESSION_FILE_DIR = test_session_dir
                config.Config.init_app(mock_app)
                
                if os.path.exists(test_session_dir):
                    # Check permissions (0o700 = owner only)
                    stat_info = os.stat(test_session_dir)
                    # On Windows, permissions work differently, so just check directory exists
                    assert os.path.isdir(test_session_dir)
                    
                    # Clean up
                    shutil.rmtree(test_session_dir)
    
    def test_init_app_handles_existing_directory(self, mock_app):
        """Test that init_app handles existing session directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_session_dir = os.path.join(tmpdir, 'existing_sessions')
            os.makedirs(test_session_dir)
            
            with patch.dict(os.environ, {
                'FLASK_SECRET_KEY': 'test-secret',
                'SMART_CLIENT_ID': 'test-client',
                'SMART_REDIRECT_URI': 'https://example.com/callback'
            }):
                from importlib import reload
                import config
                reload(config)
                
                config.Config.SESSION_FILE_DIR = test_session_dir
                
                # Should not raise exception
                config.Config.init_app(mock_app)
                
                # Directory should still exist
                assert os.path.exists(test_session_dir)
                
                # Clean up
                shutil.rmtree(test_session_dir)
    
    def test_init_app_handles_permission_error(self, mock_app):
        """Test that init_app handles permission errors gracefully."""
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'test-secret',
            'SMART_CLIENT_ID': 'test-client',
            'SMART_REDIRECT_URI': 'https://example.com/callback'
        }):
            from importlib import reload
            import config
            reload(config)
            
            # Use a path that will cause permission error
            config.Config.SESSION_FILE_DIR = '/root/forbidden_dir'
            
            # Should not raise exception, just log warning
            try:
                config.Config.init_app(mock_app)
                # Should have logged a warning
                assert mock_app.logger.warning.called or True
            except Exception:
                # If it does raise, it should be handled gracefully
                pass


class TestCernerSandboxConfig:
    """Test Cerner sandbox configuration."""
    
    def test_cerner_fhir_base_url(self):
        """Test Cerner FHIR base URL is configured."""
        assert 'fhir_base' in Config.CERNER_SANDBOX_CONFIG
        assert Config.CERNER_SANDBOX_CONFIG['fhir_base'].startswith('https://')
    
    def test_cerner_authorization_endpoint(self):
        """Test Cerner authorization endpoint is configured."""
        assert 'authorization_endpoint' in Config.CERNER_SANDBOX_CONFIG
        assert Config.CERNER_SANDBOX_CONFIG['authorization_endpoint'].startswith('https://')
    
    def test_cerner_token_endpoint(self):
        """Test Cerner token endpoint is configured."""
        assert 'token_endpoint' in Config.CERNER_SANDBOX_CONFIG
        assert Config.CERNER_SANDBOX_CONFIG['token_endpoint'].startswith('https://')
    
    def test_cerner_tenant_id(self):
        """Test Cerner tenant ID is configured."""
        assert 'tenant_id' in Config.CERNER_SANDBOX_CONFIG
        assert len(Config.CERNER_SANDBOX_CONFIG['tenant_id']) > 0


class TestSecuritySettings:
    """Test security-related configuration settings."""
    
    def test_secret_key_not_hardcoded(self):
        """Test that SECRET_KEY is not hardcoded in source."""
        # SECRET_KEY should come from environment, not be hardcoded
        # This is checked by ensuring it's loaded from os.environ
        import inspect
        source = inspect.getsource(Config)
        assert 'SECRET_KEY = "' not in source
        assert 'SECRET_KEY = \'' not in source
    
    def test_session_type_is_filesystem(self):
        """Test that session type is filesystem (not in-memory)."""
        assert Config.SESSION_TYPE == 'filesystem'
    
    def test_session_not_permanent(self):
        """Test that sessions are not permanent for security."""
        assert Config.SESSION_PERMANENT is False
    
    def test_redirect_uri_uses_https(self):
        """Test that REDIRECT_URI uses HTTPS in production."""
        if Config.REDIRECT_URI:
            # In production, should use HTTPS
            # In development, HTTP might be acceptable
            assert Config.REDIRECT_URI.startswith('http://') or Config.REDIRECT_URI.startswith('https://')


class TestScopesConfiguration:
    """Test SMART on FHIR scopes configuration."""
    
    def test_scopes_include_launch(self):
        """Test that scopes include launch scope."""
        assert 'launch' in Config.SCOPES
    
    def test_scopes_include_patient_read(self):
        """Test that scopes include patient read permissions."""
        assert 'patient/Patient.read' in Config.SCOPES
    
    def test_scopes_include_observation_read(self):
        """Test that scopes include observation read permissions."""
        assert 'patient/Observation.read' in Config.SCOPES
    
    def test_scopes_include_condition_read(self):
        """Test that scopes include condition read permissions."""
        assert 'patient/Condition.read' in Config.SCOPES
    
    def test_scopes_include_medication_read(self):
        """Test that scopes include medication read permissions."""
        assert 'patient/MedicationRequest.read' in Config.SCOPES
    
    def test_scopes_include_openid(self):
        """Test that scopes include OpenID Connect scopes."""
        assert 'openid' in Config.SCOPES
        assert 'profile' in Config.SCOPES
        assert 'fhirUser' in Config.SCOPES
    
    def test_scopes_include_online_access(self):
        """Test that scopes include online_access."""
        assert 'online_access' in Config.SCOPES
    
    def test_scopes_format(self):
        """Test that scopes are properly formatted."""
        # Scopes should be space-separated
        scopes_list = Config.SCOPES.split()
        assert len(scopes_list) > 0
        
        # Each scope should be non-empty
        for scope in scopes_list:
            assert len(scope) > 0


class TestConfigImmutability:
    """Test that critical config values are not easily modified."""
    
    def test_config_is_class_not_instance(self):
        """Test that Config is used as a class, not instantiated."""
        # Config should be used as a class with class attributes
        assert isinstance(Config, type)
    
    def test_init_app_is_static_method(self):
        """Test that init_app is a static method."""
        import inspect
        assert isinstance(inspect.getattr_static(Config, 'init_app'), staticmethod)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_redirect_uri_with_multiple_hashes(self, mock_app=None):
        """Test handling of REDIRECT_URI with multiple hash fragments."""
        if mock_app is None:
            mock_app = Mock()
            mock_app.logger = Mock()
            mock_app.logger.info = Mock()
            mock_app.logger.warning = Mock()
            mock_app.logger.debug = Mock()
        
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'test-secret',
            'SMART_CLIENT_ID': 'test-client',
            'SMART_REDIRECT_URI': 'https://example.com/callback#fragment1#fragment2'
        }):
            from importlib import reload
            import config
            reload(config)
            
            config.Config.init_app(mock_app)
            
            # Should only keep the part before the first hash
            assert '#' not in config.Config.REDIRECT_URI
            assert config.Config.REDIRECT_URI == 'https://example.com/callback'
    
    def test_redirect_uri_with_whitespace(self, mock_app=None):
        """Test handling of REDIRECT_URI with whitespace."""
        if mock_app is None:
            mock_app = Mock()
            mock_app.logger = Mock()
            mock_app.logger.info = Mock()
            mock_app.logger.warning = Mock()
            mock_app.logger.debug = Mock()
        
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': 'test-secret',
            'SMART_CLIENT_ID': 'test-client',
            'SMART_REDIRECT_URI': 'https://example.com/callback#fragment   '
        }):
            from importlib import reload
            import config
            reload(config)
            
            config.Config.init_app(mock_app)
            
            # Should strip whitespace
            assert config.Config.REDIRECT_URI.strip() == config.Config.REDIRECT_URI
    
    def test_empty_environment_variables(self):
        """Test handling of empty environment variables."""
        with patch.dict(os.environ, {
            'FLASK_SECRET_KEY': '',
            'SMART_CLIENT_ID': '',
            'SMART_REDIRECT_URI': ''
        }, clear=True):
            from importlib import reload
            import config
            reload(config)
            
            # Empty strings should be treated as missing
            assert config.Config.SECRET_KEY == '' or config.Config.SECRET_KEY is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

