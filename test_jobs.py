#!/usr/bin/env python3

import firebase_admin
from firebase_admin import credentials, firestore
import os

def test_jobs():
    try:
        # Initialize Firebase
        cred = credentials.Certificate('firebase-service-account.json')
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully")
        
        # Get Firestore database
        db = firestore.client()
        print("✅ Firestore client created")
        
        # Check jobs collection
        jobs_ref = db.collection('jobs')
        jobs = list(jobs_ref.stream())
        
        print(f"📊 Found {len(jobs)} jobs in database")
        
        if jobs:
            print("\n📋 Sample job data:")
            for i, job in enumerate(jobs[:3]):  # Show first 3 jobs
                job_data = job.to_dict()
                print(f"\nJob {i+1}:")
                print(f"  ID: {job.id}")
                print(f"  Title: {job_data.get('title', 'N/A')}")
                print(f"  Company: {job_data.get('company', 'N/A')}")
                print(f"  Location: {job_data.get('location', 'N/A')}")
                print(f"  User ID: {job_data.get('user_id', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_jobs() 