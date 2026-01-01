from flask import Flask, Response, jsonify
from flask_session import Session
from flask_cors import CORS
from flask_talisman import Talisman
import logging
import os
import datetime

# Internal imports
from services.app_config import Config
from extensions import limiter, csrf
from utils.logging_filter import setup_ephi_logging_filter

# Import blueprints
from routes.auth_routes import auth_bp
from routes.web_routes import web_bp
from routes.api_routes import api_bp
from routes.tradeoff_routes import tradeoff_bp
from routes.hooks import hooks_bp

def create_app():
    # Load env vars first via Config imports
    app = Flask(__name__)
    
    # Initialize Configuration
    Config.init_app(app)
    app.config.from_object(Config)
    
    # Initialize Extensions
    limiter.init_app(app)
    csrf.init_app(app)
    Session(app)
    
    # Logging Setup
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.DEBUG)
    setup_ephi_logging_filter(app)
    
    # Security Headers & CSP
    csp = {
        'default-src': '\'self\'',
        'script-src': [
            '\'self\'',
            'cdn.jsdelivr.net',
            'cdnjs.cloudflare.com',
        ],
        'style-src': [
            '\'self\'',
            'cdn.jsdelivr.net',
            'cdnjs.cloudflare.com',
            'fonts.googleapis.com',
            '\'unsafe-inline\''
        ],
        'font-src': [
            '\'self\'',
            'cdnjs.cloudflare.com',
            'cdn.jsdelivr.net',
            'fonts.gstatic.com'
        ],
        'img-src': ['\'self\'', 'data:'],
        'connect-src': [
            '\'self\'',
            'cdn.jsdelivr.net',
            'cdnjs.cloudflare.com'
        ]
    }
    Talisman(app, content_security_policy=csp, content_security_policy_nonce_in=['script-src'])
    
    # Register Blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(tradeoff_bp)
    app.register_blueprint(hooks_bp)
    
    # Additional CSRF Exemptions (if any not handled in blueprints)
    csrf.exempt(hooks_bp)
    
    # CORS for CDS Hooks
    CORS(app, resources={
        r"/cds-services/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    })
    
    # Health Check Endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint for monitoring and load balancers.
        Returns the application health status.
        """
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'service': 'PRECISE-HBR SMART on FHIR',
                'version': '1.0.0'
            }
            return jsonify(health_status), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.datetime.utcnow().isoformat()
            }), 503

    # Security Headers
    @app.after_request
    def add_security_headers(response: Response):
        """Add security and cache control headers to all responses."""
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response
        
    return app

# Main entry point
app = create_app()

if __name__ == '__main__':
    # R-08 Risk Mitigation: Enhanced production environment checks
    is_production = (
        os.environ.get('FLASK_ENV') == 'production' or 
        os.environ.get('PRODUCTION') == 'true' or
        os.environ.get('GAE_ENV') == 'standard'
    )
    
    if is_production:
        if os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']:
            app.logger.error("SECURITY VIOLATION: Debug mode attempted in production environment!")
            raise ValueError("Debug mode is not allowed in production environments.")
        
        if not app.config.get('SESSION_COOKIE_SECURE'):
            app.logger.warning("SESSION_COOKIE_SECURE should be True in production with HTTPS")
        
        app.logger.info("Starting application in PRODUCTION mode with enhanced security")
        debug_mode = False
    else:
        debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']
        if debug_mode:
            app.logger.warning("Running in DEBUG mode - only use in development!")
        app.logger.info("Starting application in DEVELOPMENT mode")
    
    if is_production:
        host = os.environ.get("HOST", "0.0.0.0")  # nosec B104
    else:
        host = os.environ.get("HOST", "127.0.0.1")
    
    port = int(os.environ.get("PORT", 8080))
    app.logger.info(f"Server starting on {host}:{port}")
    app.run(host=host, port=port, debug=debug_mode)
