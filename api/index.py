from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys
from datetime import datetime
import uuid

# Simple session storage
sessions = {}

def read_static_file(filename):
    """Read static files from the root directory"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return None

class VercelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Serve static files
        if path == '/' or path == '/dashboard':
            content = read_static_file('index.html')
            if content:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.end_headers()
        elif path == '/landing':
            content = read_static_file('landing.html')
            if content:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.end_headers()
        elif path == '/api/health':
            self.handle_health_check()
        elif path == '/api/jobs':
            self.handle_get_jobs()
        elif path == '/api/check-session':
            self.handle_check_session()
        else:
            self.send_response(404)
            self.end_headers()
    
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
            self.end_headers()
    
    def handle_health_check(self):
        """Simple health check endpoint"""
        try:
            self.send_json_response({
                'status': 'healthy',
                'message': 'Scot4Me API is running',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error in handle_health_check: {e}")
            self.send_error_response(str(e))
    
    def handle_get_jobs(self):
        """Get jobs - simplified for now"""
        try:
            # Return sample jobs for testing
            sample_jobs = [
                {
                    'id': '1',
                    'title': 'Software Engineer',
                    'company': 'Tech Corp',
                    'location': 'San Francisco, CA',
                    'job_url': 'https://example.com',
                    'status': 'active'
                },
                {
                    'id': '2',
                    'title': 'Data Scientist',
                    'company': 'AI Startup',
                    'location': 'New York, NY',
                    'job_url': 'https://example.com',
                    'status': 'active'
                }
            ]
            
            self.send_json_response(sample_jobs)
        except Exception as e:
            print(f"Error in handle_get_jobs: {e}")
            self.send_error_response(str(e))
    
    def handle_check_session(self):
        """Check user session"""
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
            print(f"Error in handle_check_session: {e}")
            self.send_error_response(str(e))
    
    def handle_signup(self):
        """Handle user signup"""
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
            
            # Create session (simplified - no Firebase for now)
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'user_id': str(uuid.uuid4()),
                'user_name': name,
                'created_at': datetime.now().isoformat()
            }
            
            self.send_json_response({
                'success': True,
                'message': 'User created successfully',
                'session_id': session_id
            })
        except Exception as e:
            print(f"Error in handle_signup: {e}")
            self.send_error_response(str(e))
    
    def handle_login(self):
        """Handle user login"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            email = data.get('email')
            password = data.get('password')
            
            if not all([email, password]):
                self.send_error_response('Missing credentials')
                return
            
            # Simple login (simplified - no Firebase for now)
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'user_id': str(uuid.uuid4()),
                'user_name': email.split('@')[0],
                'created_at': datetime.now().isoformat()
            }
            
            self.send_json_response({
                'success': True,
                'message': 'Login successful',
                'session_id': session_id
            })
        except Exception as e:
            print(f"Error in handle_login: {e}")
            self.send_error_response(str(e))
    
    def handle_logout(self):
        """Handle user logout"""
        try:
            session_id = self.headers.get('X-Session-ID')
            if session_id in sessions:
                del sessions[session_id]
            
            self.send_json_response({'success': True})
        except Exception as e:
            print(f"Error in handle_logout: {e}")
            self.send_error_response(str(e))
    
    def handle_search_jobs(self):
        """Handle job search"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Return success for now
            self.send_json_response({
                'success': True,
                'jobs_count': 2,
                'message': 'Search completed successfully'
            })
        except Exception as e:
            print(f"Error in handle_search_jobs: {e}")
            self.send_error_response(str(e))
    
    def handle_mark_applied(self):
        """Handle marking job as applied"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            job_id = data.get('job_id')
            
            if not job_id:
                self.send_error_response('Job ID is required', 400)
                return
            
            self.send_json_response({
                'success': True,
                'message': 'Job marked as applied'
            })
        except Exception as e:
            print(f"Error in handle_mark_applied: {e}")
            self.send_error_response(str(e))
    
    def handle_delete_job(self):
        """Handle deleting job"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            job_id = data.get('job_id')
            
            if not job_id:
                self.send_error_response('Job ID is required', 400)
                return
            
            self.send_json_response({
                'success': True,
                'message': 'Job deleted successfully'
            })
        except Exception as e:
            print(f"Error in handle_delete_job: {e}")
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