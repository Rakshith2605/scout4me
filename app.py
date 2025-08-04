from flask import Flask, render_template, request, jsonify, send_file
import csv
import os
from jobspy import scrape_jobs
import threading
import time
from datetime import datetime
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variable to store scraping status
scraping_status = {
    'is_running': False,
    'progress': 0,
    'message': '',
    'jobs_count': 0,
    'errors': [],
    'current_site': ''
}

def scrape_jobs_background(search_params):
    """Background job scraping function with robust error handling"""
    global scraping_status
    
    try:
        scraping_status['is_running'] = True
        scraping_status['progress'] = 0
        scraping_status['message'] = 'Initializing job search...'
        scraping_status['errors'] = []
        scraping_status['current_site'] = ''
        
        # Extract parameters - exactly like scrap.py
        search_term = search_params.get('search_term', 'software engineer').strip()
        location = search_params.get('location', 'San Francisco, CA').strip()
        
        # Validate inputs
        if not search_term or not location:
            raise ValueError("Job title and location are required")
        
        scraping_status['message'] = f'Searching for {search_term} jobs in {location}...'
        scraping_status['progress'] = 10
        
        # Exact configuration from working scrap.py
        scraping_config = {
            'site_name': ["indeed", "linkedin", "zip_recruiter", "google"],
            'search_term': search_term,
            'google_search_term': f"{search_term} jobs near {location} since yesterday",
            'location': location,
            'results_wanted': 20,
            'hours_old': 72,
            'country_indeed': 'USA',
        }
        
        scraping_status['message'] = f'Starting search across 4 job boards...'
        scraping_status['progress'] = 20
        
        # Perform the job scraping with error handling
        try:
            logger.info(f"Starting job scraping with config: {scraping_config}")
            jobs = scrape_jobs(**scraping_config)
            
            if jobs is None or jobs.empty:
                scraping_status['message'] = 'No jobs found. Try adjusting your search parameters.'
                scraping_status['progress'] = 100
                scraping_status['jobs_count'] = 0
                return
            
            scraping_status['progress'] = 80
            scraping_status['message'] = f'Found {len(jobs)} jobs. Processing results...'
            
            # Clean and validate job data
            jobs = clean_job_data(jobs)
            
            # Save results with error handling
            try:
                jobs.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False, encoding='utf-8')
                scraping_status['progress'] = 100
                scraping_status['message'] = f'Successfully found and saved {len(jobs)} jobs!'
                scraping_status['jobs_count'] = len(jobs)
            except Exception as e:
                logger.error(f"Error saving jobs to CSV: {str(e)}")
                scraping_status['errors'].append(f"Failed to save results: {str(e)}")
                scraping_status['message'] = f'Found {len(jobs)} jobs but failed to save. Please try again.'
                scraping_status['progress'] = 90
                
        except Exception as e:
            error_msg = f"Error during job scraping: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            scraping_status['errors'].append(error_msg)
            scraping_status['message'] = f'Job search failed: {str(e)}'
            scraping_status['progress'] = 0
            
    except Exception as e:
        error_msg = f"Critical error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        scraping_status['message'] = error_msg
        scraping_status['progress'] = 0
        scraping_status['errors'].append(error_msg)
    finally:
        scraping_status['is_running'] = False

def clean_job_data(jobs_df):
    """Clean and validate job data"""
    try:
        # Remove duplicate jobs based on title and company
        jobs_df = jobs_df.drop_duplicates(subset=['title', 'company'], keep='first')
        
        # Fill missing values
        jobs_df['title'] = jobs_df['title'].fillna('Job Title')
        jobs_df['company'] = jobs_df['company'].fillna('Company')
        jobs_df['location'] = jobs_df['location'].fillna('Location')
        jobs_df['description'] = jobs_df['description'].fillna('No description available')
        
        # Clean salary information
        if 'salary' in jobs_df.columns:
            jobs_df['salary'] = jobs_df['salary'].fillna('Salary not specified')
        
        # Add job URL if missing
        if 'job_url' not in jobs_df.columns:
            jobs_df['job_url'] = ''
        
        # Add posting date if missing
        if 'posted_date' not in jobs_df.columns:
            jobs_df['posted_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Add job type if missing
        if 'job_type' not in jobs_df.columns:
            jobs_df['job_type'] = 'Full Time'
        
        # Truncate long descriptions
        jobs_df['description'] = jobs_df['description'].astype(str).apply(
            lambda x: x[:500] + '...' if len(x) > 500 else x
        )
        
        return jobs_df
        
    except Exception as e:
        logger.error(f"Error cleaning job data: {str(e)}")
        return jobs_df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    if scraping_status['is_running']:
        return jsonify({'error': 'A job search is already in progress. Please wait for it to complete.'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No search parameters provided'})
        
        # Validate required parameters
        required_fields = ['search_term', 'location']
        for field in required_fields:
            if not data.get(field, '').strip():
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'})
        
        # Start scraping in background thread
        thread = threading.Thread(target=scrape_jobs_background, args=(data,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'Job search started successfully'})
        
    except Exception as e:
        logger.error(f"Error starting scraping: {str(e)}")
        return jsonify({'error': f'Failed to start job search: {str(e)}'})

@app.route('/api/scraping-status')
def get_scraping_status():
    return jsonify(scraping_status)

@app.route('/api/download-jobs')
def download_jobs():
    if os.path.exists('jobs.csv'):
        try:
            return send_file(
                'jobs.csv', 
                as_attachment=True, 
                download_name=f'scout4me_jobs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mimetype='text/csv'
            )
        except Exception as e:
            logger.error(f"Error downloading jobs: {str(e)}")
            return jsonify({'error': f'Download failed: {str(e)}'})
    else:
        return jsonify({'error': 'No jobs file found. Please run a job search first.'})

@app.route('/api/jobs')
def get_jobs():
    if os.path.exists('jobs.csv'):
        try:
            with open('jobs.csv', 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading jobs file: {str(e)}")
            return jsonify({'error': f'Error reading jobs file: {str(e)}'})
    else:
        return jsonify({'error': 'No jobs file found'})

@app.route('/api/clear-jobs')
def clear_jobs():
    """Clear the jobs file"""
    try:
        if os.path.exists('jobs.csv'):
            os.remove('jobs.csv')
        return jsonify({'message': 'Jobs cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing jobs: {str(e)}")
        return jsonify({'error': f'Failed to clear jobs: {str(e)}'})

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'scraping_status': scraping_status['is_running']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 