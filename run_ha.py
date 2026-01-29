#!/usr/bin/env python3
"""Run Home Assistant for development/testing."""
import sys
import os

# Add current directory to path for custom_components
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Install Home Assistant if not already installed
try:
    import homeassistant
except ImportError:
    print("Installing Home Assistant...")
    os.system(f"{sys.executable} -m pip install homeassistant --quiet")
    print("Home Assistant installed!")

# Run Home Assistant
from homeassistant import __main__ as ha_main

if __name__ == "__main__":
    sys.argv = ["hass", "-c", "./config", "--debug"]
    ha_main.main()
