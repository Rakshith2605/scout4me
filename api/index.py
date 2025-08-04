from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys
from datetime import datetime
import uuid
import pandas as pd
from firebase_config import initialize_firebase, get_db, create_user, verify_user_credentials, save_job_to_firebase, get_jobs_from_firebase, mark_job_applied, delete_job, get_user_stats, get_global_stats, get_applied_jobs_from_firebase
from jobspy import scrape_jobs
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Initialize Firebase
initialize_firebase()

# Simple session storage (in production, use a proper session store)
sessions = {}

class VercelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Serve static files
        if path == '/' or path == '/dashboard':
            self.serve_file('index.html')
        elif path == '/landing':
            self.serve_file('landing.html')
        elif path == '/api/jobs':
            self.handle_get_jobs()
        elif path == '/api/applied-jobs':
            self.handle_get_applied_jobs()
        elif path == '/api/stats':
            self.handle_get_stats()
        elif path == '/api/check-session':
            self.handle_check_session()
        else:
            self.send_response(404)
            self.end()
    
    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/api/signup':
            self.handle_signup()
        elif path == '/api/login':
            self.handle_login()
        elif path == '/api/logout':
            self.handle_logout()
        elif path == '/api/search-jobs':
            self.handle_search_jobs()
        elif path == '/api/mark-applied':
            self.handle_mark_applied()
        elif path == '/api/delete-job':
            self.handle_delete_job()
        else:
            self.send_response(404)
            self.end()
    
    def serve_file(self, filename):
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
        except FileNotFoundError:
            self.send_response(404)
            self.end()
    
    def handle_get_jobs(self):
        try:
            # Get session from headers
            session_id = self.headers.get('X-Session-ID')
            user_id = sessions.get(session_id, {}).get('user_id') if session_id else None
            
            # Get filters from query params
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            filters = {}
            if 'location' in query_params:
                filters['location'] = query_params['location'][0]
            if 'company' in query_params:
                filters['company'] = query_params['company'][0]
            if 'job_type' in query_params:
                filters['job_type'] = query_params['job_type'][0]
            
            # Get jobs
            jobs = get_jobs_from_firebase(user_id, filters)
            
            # Limit to 50 jobs for performance
            if len(jobs) > 50:
                jobs = jobs[:50]
            
            self.send_json_response(jobs)
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_get_applied_jobs(self):
        try:
            session_id = self.headers.get('X-Session-ID')
            user_id = sessions.get(session_id, {}).get('user_id') if session_id else None
            
            if not user_id:
                self.send_error_response('Not authenticated', 401)
                return
            
            applied_jobs = get_applied_jobs_from_firebase(user_id)
            self.send_json_response(applied_jobs)
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_get_stats(self):
        try:
            session_id = self.headers.get('X-Session-ID')
            user_id = sessions.get(session_id, {}).get('user_id') if session_id else None
            
            if not user_id:
                self.send_error_response('Not authenticated', 401)
                return
            
            user_stats = get_user_stats(user_id)
            global_stats = get_global_stats()
            stats = {**global_stats, **user_stats}
            
            self.send_json_response(stats)
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_check_session(self):
        try:
            session_id = self.headers.get('X-Session-ID')
            session_data = sessions.get(session_id, {})
            
            if session_data.get('user_id'):
                self.send_json_response({
                    'success': True,
                    'user_id': session_data['user_id'],
                    'user_name': session_data['user_name']
                })
            else:
                self.send_json_response({'success': False})
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_signup(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            email = data.get('email')
            password = data.get('password')
            name = data.get('name')
            
            if not all([email, password, name]):
                self.send_error_response('Missing required fields')
                return
            
            # Create user in Firebase
            user_id = create_user(email, password, name)
            
            if user_id:
                # Create session
                session_id = str(uuid.uuid4())
                sessions[session_id] = {
                    'user_id': user_id,
                    'user_name': name,
                    'created_at': datetime.now().isoformat()
                }
                
                self.send_json_response({
                    'success': True,
                    'message': 'User created successfully',
                    'session_id': session_id
                })
            else:
                self.send_error_response('Failed to create user')
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_login(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            email = data.get('email')
            password = data.get('password')
            
            if not all([email, password]):
                self.send_error_response('Missing credentials')
                return
            
            # Verify credentials
            user_data = verify_user_credentials(email, password)
            
            if user_data:
                # Create session
                session_id = str(uuid.uuid4())
                sessions[session_id] = {
                    'user_id': user_data['uid'],
                    'user_name': user_data.get('display_name', email),
                    'created_at': datetime.now().isoformat()
                }
                
                self.send_json_response({
                    'success': True,
                    'message': 'Login successful',
                    'session_id': session_id
                })
            else:
                self.send_error_response('Invalid credentials', 401)
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_logout(self):
        try:
            session_id = self.headers.get('X-Session-ID')
            if session_id in sessions:
                del sessions[session_id]
            
            self.send_json_response({'success': True})
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_search_jobs(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            session_id = self.headers.get('X-Session-ID')
            user_id = sessions.get(session_id, {}).get('user_id') if session_id else None
            
            # Extract search parameters
            search_term = data.get('search_term', 'Generative AI engineer')
            location = data.get('location', 'Dallas, TX')
            results_wanted = data.get('results_wanted', 20)
            hours_old = data.get('hours_old', 72)
            
            # Scrape jobs
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin", "zip_recruiter", "google"],
                search_term=search_term,
                google_search_term=f"{search_term} jobs near {location} since yesterday",
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed='USA',
            )
            
            # Save jobs to Firebase
            jobs_saved = 0
            for _, row in jobs.iterrows():
                job_data = row.to_dict()
                job_data['id'] = str(uuid.uuid4())
                
                # Convert datetime objects
                for key, value in job_data.items():
                    if hasattr(value, 'date'):
                        job_data[key] = value.isoformat() if value else None
                    elif pd.isna(value):
                        job_data[key] = None
                    elif isinstance(value, (datetime.date, datetime.datetime)):
                        job_data[key] = value.isoformat() if value else None
                
                if save_job_to_firebase(job_data, user_id):
                    jobs_saved += 1
            
            self.send_json_response({
                'success': True,
                'jobs_count': jobs_saved,
                'message': f'Successfully scraped and saved {jobs_saved} jobs to Firebase'
            })
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_mark_applied(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            job_id = data.get('job_id')
            session_id = self.headers.get('X-Session-ID')
            user_id = sessions.get(session_id, {}).get('user_id') if session_id else None
            
            if not user_id:
                self.send_error_response('Not authenticated', 401)
                return
            
            if not job_id:
                self.send_error_response('Job ID is required', 400)
                return
            
            success = mark_job_applied(job_id, user_id)
            
            if success:
                self.send_json_response({
                    'success': True,
                    'message': 'Job marked as applied'
                })
            else:
                self.send_error_response('Failed to mark job as applied')
        except Exception as e:
            self.send_error_response(str(e))
    
    def handle_delete_job(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            job_id = data.get('job_id')
            session_id = self.headers.get('X-Session-ID')
            user_id = sessions.get(session_id, {}).get('user_id') if session_id else None
            
            if not user_id:
                self.send_error_response('Not authenticated', 401)
                return
            
            if not job_id:
                self.send_error_response('Job ID is required', 400)
                return
            
            success = delete_job(job_id, user_id)
            
            if success:
                self.send_json_response({
                    'success': True,
                    'message': 'Job deleted successfully'
                })
            else:
                self.send_error_response('Failed to delete job')
        except Exception as e:
            self.send_error_response(str(e))
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Session-ID')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, message, status_code=500):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Session-ID')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Session-ID')
        self.end_headers()

def handler(request, context):
    return VercelHandler().handle_request(request, context) 