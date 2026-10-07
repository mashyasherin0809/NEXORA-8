#!/usr/bin/env python
"""
Launcher for NEXORA-8 CLI.
"""
import sys
import os

# Add parent directory to sys.path so nexora package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexora.cli import main

if __name__ == "__main__":
    main()
