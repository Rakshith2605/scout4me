from flask import Flask, render_template, send_from_directory, jsonify, request
import pandas as pd
import os
import subprocess
import sys

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/jobs.csv')
def jobs_csv():
    return send_from_directory('.', 'jobs.csv')

@app.route('/api/jobs')
def get_jobs():
    try:
        # Read the CSV file
        df = pd.read_csv('jobs.csv')
        
        # Convert to list of dictionaries
        jobs = df.to_dict('records')
        
        # Clean up the data
        for job in jobs:
            # Handle NaN values
            for key, value in job.items():
                if pd.isna(value):
                    job[key] = ''
                else:
                    job[key] = str(value)
        
        return jsonify(jobs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    try:
        df = pd.read_csv('jobs.csv')
        
        stats = {
            'total_jobs': len(df),
            'remote_jobs': len(df[df['is_remote'] == True]),
            'unique_companies': df['company'].nunique(),
            'avg_salary': 0
        }
        
        # Calculate average salary
        salary_jobs = df[(df['min_amount'].notna()) & (df['max_amount'].notna())]
        if len(salary_jobs) > 0:
            avg_salary = ((salary_jobs['min_amount'] + salary_jobs['max_amount']) / 2).mean()
            stats['avg_salary'] = int(avg_salary)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-jobs', methods=['POST'])
def search_jobs():
    try:
        data = request.get_json()
        
        # Extract search parameters
        search_term = data.get('search_term', 'Generative AI engineer')
        location = data.get('location', 'Dallas, TX')
        results_wanted = data.get('results_wanted', 20)
        hours_old = data.get('hours_old', 72)
        
        # Create a temporary Python script for job scraping
        script_content = f'''
import csv
from jobspy import scrape_jobs

try:
    jobs = scrape_jobs(
        site_name=["indeed", "linkedin", "zip_recruiter", "google"],
        search_term="{search_term}",
        google_search_term="{search_term} jobs near {location} since yesterday",
        location="{location}",
        results_wanted={results_wanted},
        hours_old={hours_old},
        country_indeed='USA',
    )
    
    print(f"Found {{len(jobs)}} jobs")
    jobs.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\\\", index=False)
    print("Jobs saved to jobs.csv")
    
except Exception as e:
    print(f"Error: {{e}}")
    exit(1)
'''
        
        # Write the script to a temporary file
        with open('temp_scraper.py', 'w') as f:
            f.write(script_content)
        
        # Run the scraper
        result = subprocess.run([sys.executable, 'temp_scraper.py'], 
                              capture_output=True, text=True, timeout=300)
        
        # Clean up the temporary file
        os.remove('temp_scraper.py')
        
        if result.returncode == 0:
            # Read the updated CSV to get job count
            df = pd.read_csv('jobs.csv')
            jobs_count = len(df)
            
            return jsonify({
                'success': True,
                'jobs_count': jobs_count,
                'message': f'Successfully scraped {jobs_count} jobs'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Scraping failed: {result.stderr}'
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Search timed out. Please try with fewer results.'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("Starting Scot4Me Job Board Server...")
    print("Open your browser and go to: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, host='0.0.0.0', port=8000) 