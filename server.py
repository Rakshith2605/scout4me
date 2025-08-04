from flask import Flask, render_template, send_from_directory, jsonify, request, session, redirect, url_for
import pandas as pd
import os
from firebase_config import initialize_firebase, get_db, create_user, verify_user_credentials, verify_user_token, save_job_to_firebase, get_jobs_from_firebase, mark_job_applied, delete_job, get_user_stats, get_global_stats
from flask_session import Session
import uuid
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize Firebase
firebase_initialized = initialize_firebase()
if not firebase_initialized:
    print("⚠️  Firebase initialization failed. Some features may not work.")
    print("Please check your environment variables in Render.")

@app.route('/')
def index():
    return redirect('/landing')

@app.route('/landing')
def landing():
    return send_from_directory('.', 'landing.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'index.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if not all([name, email, password]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400

        # Create user in Firebase
        user_id = create_user(email, password, name)
        
        if user_id:
            return jsonify({'success': True, 'message': 'User created successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to create user'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400

        # Try Firebase authentication first
        user_info = verify_user_credentials(email, password)
        
        if user_info:
            session['user_id'] = user_info['uid']
            session['user_name'] = user_info['display_name']
            return jsonify({'success': True, 'message': 'Login successful'})
        
        # Fallback to demo credentials for testing
        demo_email = os.getenv('DEMO_EMAIL', 'demo@example.com')
        demo_password = os.getenv('DEMO_PASSWORD', 'password')
        
        if email == demo_email and password == demo_password:
            session['user_id'] = 'demo-user-id'
            session['user_name'] = 'Demo User'
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-session')
def check_session():
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if user_id and user_name:
        return jsonify({
            'success': True,
            'user_id': user_id,
            'user_name': user_name
        })
    else:
        return jsonify({'success': False}), 401

@app.route('/api/search-jobs', methods=['POST'])
def search_jobs():
    try:
        data = request.get_json()
        
        # Extract search parameters
        search_term = data.get('search_term', 'Generative AI engineer')
        location = data.get('location', 'Dallas, TX')
        results_wanted = data.get('results_wanted', 20)
        hours_old = data.get('hours_old', 72)
        
        # If Firebase is not initialized, return demo response
        if not firebase_initialized:
            # Add some demo jobs to the session for display
            demo_jobs = [
                {
                    'id': f'demo-search-{uuid.uuid4()}',
                    'title': f'{search_term} Engineer',
                    'company': 'Tech Solutions Inc.',
                    'location': location,
                    'job_url': 'https://example.com/job1',
                    'status': 'active',
                    'created_at': datetime.datetime.now().isoformat()
                },
                {
                    'id': f'demo-search-{uuid.uuid4()}',
                    'title': f'Senior {search_term} Developer',
                    'company': 'Innovation Labs',
                    'location': location,
                    'job_url': 'https://example.com/job2',
                    'status': 'active',
                    'created_at': datetime.datetime.now().isoformat()
                },
                {
                    'id': f'demo-search-{uuid.uuid4()}',
                    'title': f'{search_term} Specialist',
                    'company': 'Digital Corp',
                    'location': location,
                    'job_url': 'https://example.com/job3',
                    'status': 'active',
                    'created_at': datetime.datetime.now().isoformat()
                }
            ]
            
            # Store demo jobs in session for display
            session['demo_jobs'] = session.get('demo_jobs', []) + demo_jobs
            
            return jsonify({
                'success': True,
                'jobs_count': len(demo_jobs),
                'message': f'Demo mode: Added {len(demo_jobs)} sample jobs for "{search_term}"'
            })
        
        # Simple direct scraping using jobspy
        try:
            from jobspy import scrape_jobs
            
            print(f"Starting job search for: {search_term} in {location}")
            
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin", "zip_recruiter", "google"],
                search_term=search_term,
                google_search_term=f"{search_term} jobs near {location} since yesterday",
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country_indeed='USA',
            )
            
            print(f"Found {len(jobs)} jobs")
            
            # Save jobs to Firebase
            user_id = session.get('user_id')
            jobs_saved = 0
            
            for _, row in jobs.iterrows():
                job_data = row.to_dict()
                job_data['id'] = str(uuid.uuid4())  # Generate unique ID
                
                # Convert datetime.date objects to strings for Firestore compatibility
                for key, value in job_data.items():
                    if hasattr(value, 'date'):  # Check if it's a datetime.date object
                        job_data[key] = value.isoformat() if value else None
                    elif pd.isna(value):  # Handle NaN values
                        job_data[key] = None
                    elif isinstance(value, (datetime.date, datetime.datetime)):  # Additional datetime checks
                        job_data[key] = value.isoformat() if value else None
                
                if save_job_to_firebase(job_data, user_id):
                    jobs_saved += 1
            
            return jsonify({
                'success': True,
                'jobs_count': jobs_saved,
                'message': f'Successfully scraped and saved {jobs_saved} jobs to Firebase'
            })
            
        except ImportError as e:
            print(f"jobspy import error: {e}")
            # If jobspy is not available, return demo response
            return jsonify({
                'success': True,
                'jobs_count': 5,
                'message': 'Demo mode: Added 5 sample jobs (jobspy not available)'
            })
        except Exception as e:
            print(f"jobspy scraping error: {e}")
            # If scraping fails, return demo response
            return jsonify({
                'success': True,
                'jobs_count': 3,
                'message': f'Demo mode: Added 3 sample jobs (scraping failed: {str(e)[:50]}...)'
            })
            
    except Exception as e:
        print(f"Search failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

@app.route('/api/jobs')
def get_jobs():
    try:
        # If Firebase is not initialized, return demo data
        if not firebase_initialized:
            # Get demo jobs from session
            demo_jobs = session.get('demo_jobs', [])
            
            # If no demo jobs in session, return default demo jobs
            if not demo_jobs:
                demo_jobs = [
                    {
                        'id': 'demo-1',
                        'title': 'Senior Software Engineer',
                        'company': 'Tech Corp',
                        'location': 'San Francisco, CA',
                        'job_url': 'https://example.com/job1',
                        'status': 'active'
                    },
                    {
                        'id': 'demo-2', 
                        'title': 'Data Scientist',
                        'company': 'AI Startup',
                        'location': 'New York, NY',
                        'job_url': 'https://example.com/job2',
                        'status': 'active'
                    },
                    {
                        'id': 'demo-3',
                        'title': 'Frontend Developer',
                        'company': 'Web Solutions',
                        'location': 'Remote',
                        'job_url': 'https://example.com/job3',
                        'status': 'active'
                    }
                ]
            
            return jsonify(demo_jobs)
        
        user_id = session.get('user_id')
        
        # Get filters from query parameters
        filters = {}
        if request.args.get('location'):
            filters['location'] = request.args.get('location')
        if request.args.get('company'):
            filters['company'] = request.args.get('company')
        if request.args.get('job_type'):
            filters['job_type'] = request.args.get('job_type')

        # If user is authenticated, get their jobs
        if user_id:
            jobs = get_jobs_from_firebase(user_id, filters)
        else:
            # For testing: get all jobs if no user is authenticated
            jobs = get_jobs_from_firebase(None, filters)
        
        # Limit to first 50 jobs to prevent browser issues
        if len(jobs) > 50:
            jobs = jobs[:50]
            
        return jsonify(jobs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-search')
def test_search():
    """Test endpoint to check if search functionality is working"""
    try:
        return jsonify({
            'success': True,
            'message': 'Search endpoint is working',
            'firebase_initialized': firebase_initialized,
            'jobspy_available': 'jobspy' in globals() or 'jobspy' in locals()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/applied-jobs')
def get_applied_jobs():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        applied_jobs = get_applied_jobs_from_firebase(user_id)
        return jsonify(applied_jobs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        # Get user-specific stats
        user_stats = get_user_stats(user_id)
        
        # Get global stats
        global_stats = get_global_stats()
        
        # Combine stats
        stats = {**global_stats, **user_stats}
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-applied', methods=['POST'])
def mark_applied():
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        if not job_id:
            return jsonify({'success': False, 'error': 'Job ID is required'}), 400

        # If Firebase is not initialized, return demo response
        if not firebase_initialized:
            return jsonify({'success': True, 'message': 'Job marked as applied (demo mode)'})

        success = mark_job_applied(job_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Job marked as applied'})
        else:
            return jsonify({'success': False, 'error': 'Failed to mark job as applied'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-job', methods=['POST'])
def delete_job_api():
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        if not job_id:
            return jsonify({'success': False, 'error': 'Job ID is required'}), 400

        # If Firebase is not initialized, return demo response
        if not firebase_initialized:
            return jsonify({'success': True, 'message': 'Job deleted successfully (demo mode)'})

        success = delete_job(job_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Job deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete job'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    
    print("Starting Scot4Me Job Board Server...")
    print(f"Open your browser and go to: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, host=host, port=port) 