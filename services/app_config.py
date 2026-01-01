import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Google Secret Manager Helper ---
# Import the Secret Manager client library.
try:
    from google.cloud import secretmanager
    HAS_SECRET_MANAGER = True
except ImportError:
    HAS_SECRET_MANAGER = False

def get_secret(env_var: str, default: str = None) -> str:
    """
    Retrieves a secret from environment variables or Google Secret Manager.
    If the value of the env_var looks like a GCP secret path, it fetches it.
    Otherwise, it returns the environment variable's value directly.
    """
    value = os.environ.get(env_var)
    if not value:
        return default

    # Check if the value is a GCP secret resource name
    if HAS_SECRET_MANAGER and value.startswith('projects/'):
        resolved_value = value
        try:
            # Handle placeholder for project ID in GAE environment
            if '${PROJECT_ID}' in resolved_value:
                gcp_project = os.environ.get('GOOGLE_CLOUD_PROJECT')
                if not gcp_project:
                    logging.error("GOOGLE_CLOUD_PROJECT env var not set, cannot resolve secret path.")
                    return default
                resolved_value = resolved_value.replace('${PROJECT_ID}', gcp_project)

            secret_client = secretmanager.SecretManagerServiceClient()
            response = secret_client.access_secret_version(name=resolved_value)
            return response.payload.data.decode('UTF-8')
        except Exception as e:
            logging.error(f"Failed to access secret for {env_var} at path '{resolved_value}'. Error: {e}")
            return default
    
    return value

class Config:
    """Base Configuration"""
    SECRET_KEY = get_secret('FLASK_SECRET_KEY')
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Client Config
    CLIENT_ID = get_secret('SMART_CLIENT_ID')
    REDIRECT_URI = get_secret('SMART_REDIRECT_URI')
    CLIENT_SECRET = get_secret('SMART_CLIENT_SECRET')
    SMART_SCOPES = get_secret('SMART_SCOPES', 'launch openid fhirUser profile user/Patient.rs user/Observation.rs user/Condition.rs user/MedicationRequest.rs user/Procedure.rs')
    CERNER_DOMAIN = 'cerner.com'

    @staticmethod
    def init_app(app):
        if not Config.SECRET_KEY:
            app.logger.error("FATAL: FLASK_SECRET_KEY environment variable must be set for security.")
            raise ValueError("FLASK_SECRET_KEY environment variable is required but not set.")
        
        # Determine session directory based on environment
        if os.environ.get('GAE_ENV', '').startswith('standard'):
            import tempfile
            app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
            app.config['SESSION_COOKIE_SECURE'] = True
        else:
            app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'flask_session')
            app.config['SESSION_COOKIE_SECURE'] = False
