#!/usr/bin/env python3
"""
Simple test to verify the API works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from firebase_config import initialize_firebase
    print("✅ Firebase config imported successfully")
    
    initialize_firebase()
    print("✅ Firebase initialized successfully")
    
    from jobspy import scrape_jobs
    print("✅ Jobspy imported successfully")
    
    print("✅ All imports working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1) 