"""
Run this from d:\\tazaura\\backend\\:
    python run.py
"""
import sys
import os

# Ensure 'backend' root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from controller.app import app

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
