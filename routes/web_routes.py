from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app
from utils.web_utils import is_session_valid, login_required, render_error_page
from services.audit_logger import audit_ephi_access
import random
import datetime
import json
import uuid
import os

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    if is_session_valid():
        return redirect(url_for('web.main_page'))
    return redirect(url_for('web.standalone_launch_page'))

@web_bp.route('/standalone')
def standalone_launch_page():
    return render_template('standalone_launch.html')

@web_bp.route('/initiate-launch', methods=['POST'])
def initiate_launch():
    iss = request.form.get('iss')
    if not iss:
        return render_error_page("Launch Error", "'iss' (FHIR Server URL) is missing.")
    return redirect(url_for('auth.launch', iss=iss))

@web_bp.route('/docs')
def docs_page():
    """Renders the documentation page."""
    return render_template('docs.html')

@web_bp.route('/main')
@login_required
@audit_ephi_access(action='view_risk_calculator', resource_type='Patient')
def main_page():
    patient_id = session.get('patient_id', 'N/A')
    return render_template('main.html', patient_id=patient_id)

@web_bp.route('/report-issue')
def report_issue_page():
    """Display the complaint/issue reporting form."""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session['captcha_answer'] = num1 + num2
    return render_template('report_issue.html', captcha_question=f"{num1} + {num2} = ?")

@web_bp.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    """Handle complaint submission and storage."""
    user_answer = request.form.get('captcha_answer')
    expected_answer = session.pop('captcha_answer', None)
    
    if not expected_answer or not user_answer or str(expected_answer) != str(user_answer).strip():
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        session['captcha_answer'] = num1 + num2
        
        return render_template('report_issue.html', 
                             error="Security check failed. Please solve the math problem correctly.",
                             captcha_question=f"{num1} + {num2} = ?",
                             prev_data=request.form), 400

    reference_id = f"COMP-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    complaint_data = {
        'reference_id': reference_id,
        'timestamp': datetime.datetime.now().isoformat(),
        'complainant_type': request.form.get('complainant_type', 'unknown'),
        'category': request.form.get('category', 'other'),
        'severity': request.form.get('severity', 'medium'),
        'subject': request.form.get('subject', '').strip(),
        'description': request.form.get('description', '').strip(),
        'contact_email': request.form.get('contact_email', '').strip(),
        'user_agent': request.headers.get('User-Agent', 'unknown'),
        'ip_address': request.remote_addr,
        'session_patient_id': session.get('patient_id', 'N/A')
    }
    
    if not all([complaint_data['complainant_type'], complaint_data['category'], 
                complaint_data['severity'], complaint_data['subject'], 
                complaint_data['description']]):
        return render_template('report_issue.html', 
                             error="Please fill in all required fields."), 400
    
    # Save to file
    # We use current_app.instance_path or just os.getcwd()/instance
    # APP.py used os.getcwd()/instance/complaints
    complaints_dir = os.path.join(os.getcwd(), 'instance', 'complaints')
    os.makedirs(complaints_dir, exist_ok=True)
    
    complaints_file = os.path.join(complaints_dir, 'complaints.jsonl')
    
    try:
        with open(complaints_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(complaint_data, ensure_ascii=False) + '\n')
        
        current_app.logger.info(f"Complaint submitted: {reference_id} - Category: {complaint_data['category']} - Severity: {complaint_data['severity']}")
        
        if complaint_data['severity'] == 'critical':
            current_app.logger.warning(f"CRITICAL COMPLAINT RECEIVED: {reference_id} - {complaint_data['subject']}")
        
        return render_template('report_issue.html', 
                             success=True, 
                             reference_id=reference_id)
    
    except Exception as e:
        current_app.logger.error(f"Error saving complaint: {e}")
        return render_template('report_issue.html', 
                             error="An error occurred while submitting your complaint. Please try again."), 500
