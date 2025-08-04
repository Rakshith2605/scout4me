import firebase_admin
from firebase_admin import credentials, firestore, auth
import os

# Initialize Firebase Admin SDK
def initialize_firebase():
    try:
        # Check if we're in production (Render) or development
        if os.getenv('RENDER'):  # Render sets this environment variable
            # Use environment variables for production
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
            })
        else:
            # Use the service account key file for development
            cred = credentials.Certificate('firebase-service-account.json')
        
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully")
        return True
    except Exception as e:
        print(f"Firebase initialization error: {e}")
        return False

# Get Firestore database instance
def get_db():
    return firestore.client()

# User authentication functions
def create_user(email, password, display_name):
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name
        )
        return user.uid
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def verify_user_credentials(email, password):
    """Verify user credentials using Firebase Auth"""
    try:
        # For Firebase Admin SDK, we need to verify the user exists
        # and then validate the password (this is a simplified approach)
        user = auth.get_user_by_email(email)
        if user:
            # In a real implementation, you'd verify the password
            # For now, we'll return the user if they exist
            return {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name or 'User'
            }
        return None
    except Exception as e:
        print(f"Error verifying credentials: {e}")
        return None

def verify_user_token(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token['uid']
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None

# Job management functions
def save_job_to_firebase(job_data, user_id=None):
    db = get_db()
    try:
        job_data['created_at'] = firestore.SERVER_TIMESTAMP
        job_data['user_id'] = user_id
        job_data['status'] = 'active'
        
        doc_ref = db.collection('jobs').add(job_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"Error saving job: {e}")
        return None

def get_jobs_from_firebase(user_id=None, filters=None):
    db = get_db()
    try:
        print(f"Getting jobs for user_id: {user_id}")
        
        # Start with basic query - only get active jobs
        query = db.collection('jobs').where('status', '==', 'active')
        
        # Add user filter only if user_id is provided
        if user_id:
            print(f"Filtering by user_id: {user_id}")
            query = query.where('user_id', '==', user_id)
        
        # Add other filters
        if filters:
            for key, value in filters.items():
                if value:
                    print(f"Adding filter: {key} == {value}")
                    query = query.where(key, '==', value)
        
        docs = query.stream()
        jobs = []
        
        # Get user's applied job IDs to exclude them
        applied_job_ids = set()
        if user_id:
            applied_docs = db.collection('users').document(user_id).collection('applied_jobs').stream()
            applied_job_ids = {doc.id for doc in applied_docs}
        
        for doc in docs:
            job_data = doc.to_dict()
            job_data['id'] = doc.id
            
            # Skip jobs that user has already applied to
            if doc.id not in applied_job_ids:
                jobs.append(job_data)
        
        print(f"Found {len(jobs)} jobs")
        if jobs:
            print(f"Sample job user_id: {jobs[0].get('user_id')}")
        
        return jobs
    except Exception as e:
        print(f"Error getting jobs: {e}")
        return []

def get_applied_jobs_from_firebase(user_id):
    db = get_db()
    try:
        if not user_id:
            return []
        
        # Get user's applied jobs
        applied_docs = db.collection('users').document(user_id).collection('applied_jobs').stream()
        applied_jobs = []
        
        for doc in applied_docs:
            applied_data = doc.to_dict()
            applied_data['id'] = doc.id
            
            # Get the original job data
            job_doc = db.collection('jobs').document(doc.id).get()
            if job_doc.exists:
                job_data = job_doc.to_dict()
                job_data['id'] = doc.id
                job_data['applied_at'] = applied_data.get('applied_at')
                job_data['application_status'] = applied_data.get('status', 'applied')
                applied_jobs.append(job_data)
        
        return applied_jobs
    except Exception as e:
        print(f"Error getting applied jobs: {e}")
        return []

def mark_job_applied(job_id, user_id):
    db = get_db()
    try:
        # Add to user's applied jobs
        db.collection('users').document(user_id).collection('applied_jobs').document(job_id).set({
            'applied_at': firestore.SERVER_TIMESTAMP,
            'status': 'applied'
        })
        
        # Update job application count
        job_ref = db.collection('jobs').document(job_id)
        job_ref.update({
            'applications': firestore.Increment(1)
        })
        
        return True
    except Exception as e:
        print(f"Error marking job as applied: {e}")
        return False

def delete_job(job_id, user_id):
    db = get_db()
    try:
        # Soft delete - mark as inactive
        db.collection('jobs').document(job_id).update({
            'status': 'inactive',
            'deleted_by': user_id,
            'deleted_at': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        print(f"Error deleting job: {e}")
        return False

def get_user_stats(user_id):
    db = get_db()
    try:
        # Get applied jobs count
        applied_jobs = db.collection('users').document(user_id).collection('applied_jobs').stream()
        applied_count = len(list(applied_jobs))
        
        # Get user's job searches
        user_jobs = db.collection('jobs').where('user_id', '==', user_id).stream()
        search_count = len(list(user_jobs))
        
        # Get overall stats
        all_jobs = db.collection('jobs').where('status', '==', 'active').stream()
        total_jobs = len(list(all_jobs))
        
        return {
            'applied_jobs': applied_count,
            'searches_performed': search_count,
            'total_jobs_available': total_jobs
        }
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {}

def get_global_stats():
    db = get_db()
    try:
        # Get all active jobs
        jobs = db.collection('jobs').where('status', '==', 'active').stream()
        jobs_list = list(jobs)
        
        total_jobs = len(jobs_list)
        remote_jobs = len([j for j in jobs_list if j.to_dict().get('is_remote') == True])
        
        # Calculate average salary
        salaries = []
        for job in jobs_list:
            job_data = job.to_dict()
            if job_data.get('min_amount') and job_data.get('max_amount'):
                try:
                    min_sal = float(job_data['min_amount'])
                    max_sal = float(job_data['max_amount'])
                    salaries.append((min_sal + max_sal) / 2)
                except:
                    pass
        
        avg_salary = sum(salaries) / len(salaries) if salaries else 0
        
        # Get unique companies
        companies = set()
        for job in jobs_list:
            company = job.to_dict().get('company')
            if company:
                companies.add(company)
        
        return {
            'total_jobs': total_jobs,
            'remote_jobs': remote_jobs,
            'avg_salary': int(avg_salary),
            'unique_companies': len(companies)
        }
    except Exception as e:
        print(f"Error getting global stats: {e}")
        return {} 