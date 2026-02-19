"""
PythonAnywhere WSGI entry point.
This file is referenced in the PythonAnywhere web app configuration.
"""
import sys
import os
from pathlib import Path

# Add the web directory to the path
project_home = Path(__file__).resolve().parent
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(project_home.parent / ".env")

from app import app as application
