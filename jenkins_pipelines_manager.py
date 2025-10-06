from flask import Flask, render_template, request, jsonify, url_for, session, make_response
import jenkins
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'jenkins_manager_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # Session lasts for 24 hours

# Jenkins connection configuration
JENKINS_URL = 'http://localhost:8080'
JENKINS_USERNAME = 'Poojitha8642'
JENKINS_PASSWORD = 'Devops@2004'

class JenkinsConnection:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            try:
                server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USERNAME, password=JENKINS_PASSWORD)
                server.get_whoami()  # Test connection
                cls._instance = server
                print('Connected to Jenkins as:', server.get_whoami()['fullName'])
            except Exception as e:
                print('Failed to connect to Jenkins:', str(e))
                cls._instance = None
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

jenkins_server = JenkinsConnection.get_instance()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.cookies.get('auth_token')
        if not auth_token or 'logged_in' not in session:
            return jsonify({"status": "error", "message": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function
from feature_modules import *

def check_auth():
    return 'logged_in' in session and session['logged_in']

@app.before_request
def before_request():
    if not request.path.startswith('/static/'):
        if request.path != '/' and not request.path.startswith('/login'):
            if not check_auth():
                return jsonify({"status": "error", "message": "Please login first"}), 401

@app.route('/api/job-stats')
def job_stats():
    server = JenkinsConnection.get_instance()
    if not server:
        return jsonify({
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "queued_jobs": 0
        })
    
    try:
        jobs = jenkins_server.get_all_jobs()
        queued_items = jenkins_server.get_queue_info()
        
        total_jobs = len(jobs)
        successful_jobs = 0
        failed_jobs = 0
        
        for job in jobs:
            job_info = jenkins_server.get_job_info(job['name'])
            if job_info.get('lastBuild'):
                last_build = jenkins_server.get_build_info(job['name'], job_info['lastBuild']['number'])
                if last_build['result'] == 'SUCCESS':
                    successful_jobs += 1
                elif last_build['result'] == 'FAILURE':
                    failed_jobs += 1
        
        return jsonify({
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "queued_jobs": len(queued_items)
        })
    except Exception as e:
        return jsonify({
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "queued_jobs": 0,
            "error": str(e)
        })

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Validate credentials
    if username != JENKINS_USERNAME or password != JENKINS_PASSWORD:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    
    try:
        # Validate against predefined Jenkins credentials
        if username == JENKINS_USERNAME and password == JENKINS_PASSWORD:
            if jenkins_server and jenkins_server.get_whoami():  # Test existing connection
                session.permanent = True
                session['logged_in'] = True
                session['username'] = username
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"status": "error", "message": "Jenkins server connection failed"}), 500
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
        
        # Set session
        session.permanent = True
        session['logged_in'] = True
        session['username'] = username
        
        return jsonify({"status": "success"}), 200
        
    except jenkins.JenkinsException as e:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": "Server error occurred"}), 500

@app.route('/logout', methods=['POST'])
def logout():
    # Clear session data
    session.clear()
    
    # Create response that clears the auth cookie
    response = make_response(jsonify({"status": "success", "message": "Logged out successfully"}))
    response.set_cookie('auth_token', '', expires=0)  # Expire the cookie immediately
    
    return response, 200

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/pipelines')
@login_required
def pipelines():
    server = JenkinsConnection.get_instance()
    if not server:
        return jsonify({"error": "Not connected to Jenkins"}), 500
    return render_template('pipelines.html')

@app.route('/api/pipelines')
@login_required
def get_pipelines():
    try:
        server = JenkinsConnection.get_instance()
        if not server:
            return jsonify({"error": "Not connected to Jenkins"}), 500
            
        jobs = server.get_jobs()
        pipeline_jobs = []
        
        for job in jobs:
            if is_pipeline_job(job['name']):
                info = {
                    'name': job['name'],
                    'url': job['url'],
                    'status': 'UNKNOWN'
                }
                
                try:
                    job_info = jenkins_server.get_job_info(job['name'])
                    if job_info.get('lastBuild'):
                        last_build = jenkins_server.get_build_info(job['name'], job_info['lastBuild']['number'])
                        info['status'] = last_build.get('result', 'UNKNOWN')
                        info['lastRun'] = last_build.get('timestamp')
                    pipeline_jobs.append(info)
                except:
                    pipeline_jobs.append(info)
        
        return jsonify(pipeline_jobs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def is_pipeline_job(job_name):
    try:
        server = JenkinsConnection.get_instance()
        if not server:
            return False
        job_info = server.get_job_info(job_name)
        return job_info.get('_class', '').endswith('WorkflowJob')
    except:
        return False

def get_last_build_time(job_name):
    try:
        server = JenkinsConnection.get_instance()
        if not server:
            return None
        job_info = server.get_job_info(job_name)
        if job_info.get('lastBuild'):
            build_info = server.get_build_info(job_name, job_info['lastBuild']['number'])
            return build_info.get('timestamp', None)
    except:
        return None

def get_job_status(job_name):
    try:
        job_info = jenkins_server.get_job_info(job_name)
        if job_info.get('lastBuild'):
            build_info = jenkins_server.get_build_info(job_name, job_info['lastBuild']['number'])
            return build_info.get('result', 'UNKNOWN')
    except:
        return 'UNKNOWN'

# System routes
@app.route('/system')
def system_page():
    return render_template('system.html')

@app.route('/tools')
def tools():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('tools.html', partial=True)
    return render_template('tools.html')

@app.route('/plugins')
def plugins():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('plugins.html', partial=True)
    return render_template('plugins.html')

@app.route('/appearance')
def appearance():
    return render_template('appearance.html')

@app.route('/nodes')
def nodes():
    return render_template('nodes.html')

@app.route('/clouds')
def clouds():
    return render_template('clouds.html')

@app.route('/security')
def security():
    return render_template('security.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/credentials')
def credentials():
    return render_template('credentials.html')

@app.route('/credential-providers')
def credential_providers():
    return render_template('credential_providers.html')

@app.route('/system-information')
def system_information():
    return render_template('system_information.html')

@app.route('/system-log')
def system_log():
    return render_template('system_log.html')

@app.route('/load-statistics')
def load_statistics():
    return render_template('load_statistics.html')

@app.route('/manage-old-data')
def manage_old_data():
    return render_template('manage_old_data.html')

@app.route('/reload-config')
def reload_config():
    return render_template('reload_config.html')

if __name__ == '__main__':
    print("Starting Jenkins UI server...")
    print("Access the application at: http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=True)
