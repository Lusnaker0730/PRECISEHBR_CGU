from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
# Note: storage_uri and other settings can be configured via app.config later
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
csrf = CSRFProtect()
