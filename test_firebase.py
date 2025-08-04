#!/usr/bin/env python3

import firebase_admin
from firebase_admin import credentials, firestore
import os

def test_firebase():
    try:
        # Initialize Firebase
        cred = credentials.Certificate('firebase-service-account.json')
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully")
        print("📁 Using project: scout4me-acf2b")
        
        # Get Firestore database
        db = firestore.client()
        print("✅ Firestore client created")
        
        # Test writing data
        test_data = {
            'test': 'Hello Firebase!',
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('test').add(test_data)
        print(f"✅ Test data written with ID: {doc_ref[1].id}")
        
        # Test reading data
        docs = db.collection('test').stream()
        for doc in docs:
            print(f"✅ Read data: {doc.to_dict()}")
        
        print("🎉 Firebase Firestore is working perfectly!")
        return True
        
    except Exception as e:
        print(f"❌ Firebase test failed: {e}")
        print("🔧 Please enable Firestore API for: scout4me-acf2b")
        print("🔗 Visit: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=scout4me-acf2b")
        return False

if __name__ == "__main__":
    test_firebase() 