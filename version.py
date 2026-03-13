"""
Single source of truth for PRECISE-HBR application version.

This file is read by APP.py, regulatory workflows, and Docker builds.
Update this file when releasing a new version.

Versioning follows Semantic Versioning (https://semver.org/):
  MAJOR.MINOR.PATCH
  - MAJOR: Breaking API/clinical algorithm changes
  - MINOR: New features, backward-compatible
  - PATCH: Bug fixes, security patches
"""

__version__ = "1.1.0"
