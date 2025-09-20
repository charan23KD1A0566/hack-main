import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# --- SMS (Twilio) ---
from twilio.rest import Client

# --- EMAIL CONFIGURATION (Set your SMTP credentials here) ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "charangottapu77@gmail.com"      # <-- Replace with your email
SMTP_PASSWORD = "ulhupqguvoboqbwk"     # <-- Replace with your app password

# --- TWILIO CONFIGURATION (Set your Twilio credentials here) ---
TWILIO_ACCOUNT_SID = ""  # <-- Replace with your Twilio Account SID
TWILIO_AUTH_TOKEN = ""   # <-- Replace with your Twilio Auth Token
TWILIO_PHONE_NUMBER = "" # <-- Replace with your Twilio phone number

def send_application_email(to_email, applicant_name, internship_title, company_name, application_id):
    """Send a real email to the applicant after successful application."""
    subject = f"Application Confirmation: {internship_title} at {company_name}"
    body = f"""
    Dear {applicant_name},

    Thank you for applying for the position of {internship_title} at {company_name}.

    Your application has been received successfully.
    Application ID: {application_id}
    Date: {datetime.now().strftime('%B %d, %Y')}

    We will review your application and get back to you soon.

    Best regards,
    PM Internship Team
    """

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send confirmation email: {e}")
        return False

# --- SMS Sending Function ---
def send_application_sms(to_mobile, applicant_name, internship_title, company_name, application_id):
    """Send an SMS to the applicant after successful application using Twilio."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
        st.warning("Twilio credentials not set. SMS not sent.")
        return False
    message_body = f"Hi {applicant_name}, your application for {internship_title} at {company_name} (ID: {application_id}) has been received. - PM Internship Team"
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_mobile
        )
        return True
    except Exception as e:
        st.error(f"Failed to send confirmation SMS: {e}")
        return False

# Load datasets
@st.cache_data
def load_data():
    try:
        students = pd.read_csv('student_profiles_dataset.csv')
        internships = pd.read_csv('pm_internship_opportunities.csv')
        applications = pd.read_csv('student_applications.csv')
        companies = pd.read_csv('companies_dataset.csv')
        skills_master = pd.read_csv('skills_master.csv')
        return students, internships, applications, companies, skills_master
    except FileNotFoundError as e:
        st.error(f"Dataset file not found: {e}")
        return None, None, None, None, None

class InternshipRecommender:
    def __init__(self, internships_df, companies_df):
        self.internships = internships_df
        self.companies = companies_df
        self.education_levels = {
            'High School': 1,
            'Diploma': 2,
            'Undergraduate': 3,
            'Postgraduate': 4,
            'Any': 1
        }

    def calculate_match_score(self, student_profile, internship):
        score = 0
        student_edu = self.education_levels.get(student_profile['education_level'], 5)
        required_edu = self.education_levels.get(internship['education_requirement'], 1)
        # Only allow exact education level match
        if student_edu != required_edu:
            return 0
        score += 3  # Education matches exactly
        if internship['sector'] == student_profile['preferred_sector']:
            score += 4
            preferred_location = student_profile['preferred_location']
            internship_location = internship['location']
            if preferred_location == 'Any':
                score += 2  # If user wants any location, allow all
            elif internship_location == preferred_location or internship_location == 'Any Location':
                score += 2
            else:
                return 0  # Do not show internships from other cities
        student_skills = set([skill.strip().lower() for skill in student_profile['skills'].split(',')])
        required_skills = set([skill.strip().lower() for skill in internship['required_skills'].split(',')])
        skill_overlap = len(student_skills.intersection(required_skills))
        max_possible = len(required_skills)
        if max_possible > 0:
            skill_score = (skill_overlap / max_possible) * 5
            score += skill_score
        return min(score, 10)

    def get_recommendations(self, student_profile, top_k=5):
        recommendations = []
        for _, internship in self.internships.iterrows():
            match_score = self.calculate_match_score(student_profile, internship)
            if match_score > 0:
                recommendations.append({
                    'internship': internship,
                    'match_score': match_score,
                    'match_percentage': int((match_score / 10) * 100)
                })
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        return recommendations[:top_k]

def show_application_form(internship_title, company_name, internship_id):
    st.markdown("---")
    st.subheader(f"📝 Apply for {internship_title}")
    st.markdown(f"Company: {company_name}")
    st.markdown("Please fill in your details to complete the application:")

    with st.form(key=f"application_form_{internship_id}"):
        col1, col2 = st.columns(2)
        with col1:
            applicant_name = st.text_input("Full Name *", placeholder="Enter your full name")
            email = st.text_input("Email Address *", placeholder="your.email@example.com")
        with col2:
            mobile = st.text_input("Mobile Number *", placeholder="+91 XXXXXXXXXX")
            current_location = st.text_input("Current Location", placeholder="City, State")
        cover_letter = st.text_area(
            "Why are you interested in this internship? (Optional)", 
            placeholder="Brief message about your interest...",
            height=100
        )
        resume_file = st.file_uploader(
            "Upload Resume (Optional)", 
            type=['pdf', 'doc', 'docx'],
            help="Upload your resume in PDF or Word format"
        )
        agree_terms = st.checkbox(
            "I agree to the Terms & Conditions and Privacy Policy *", 
            value=False
        )
        col_submit, col_cancel = st.columns([1, 1])
        with col_submit:
            submit_button = st.form_submit_button(
                "🚀 Submit Application", 
                type="primary",
                use_container_width=True
            )
        with col_cancel:
            cancel_button = st.form_submit_button(
                "❌ Cancel", 
                use_container_width=True
            )

    if submit_button:
        errors = []
        if not applicant_name or len(applicant_name.strip()) < 2:
            errors.append("Please enter a valid full name")
        if not email or "@" not in email or "." not in email:
            errors.append("Please enter a valid email address")
        if not mobile or len(mobile.replace(" ", "").replace("+", "").replace("-", "")) < 10:
            errors.append("Please enter a valid mobile number")
        if not agree_terms:
            errors.append("Please agree to Terms & Conditions")
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            with st.spinner("Processing your application..."):
                time.sleep(2)
            st.success("🎉 Application Submitted Successfully!")
            st.markdown("### 📋 Application Summary")
            application_id = f"APP{internship_id}{int(time.time())}"
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #4caf50;
                margin: 15px 0;
            ">
                <p><strong>👤 Name:</strong> {applicant_name}</p>
                <p><strong>📧 Email:</strong> {email}</p>
                <p><strong>📱 Mobile:</strong> {mobile}</p>
                <p><strong>🏢 Position:</strong> {internship_title}</p>
                <p><strong>🏭 Company:</strong> {company_name}</p>
                <p><strong>📅 Application Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                <p><strong>🆔 Application ID:</strong> {application_id}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("### 🚀 What's Next?")
            st.info("""
            📩 Confirmation Email: You'll receive a confirmation email shortly.  
            📲 Confirmation SMS: You'll receive an SMS confirmation on your mobile.  
            ⏱ Review Process: Applications are typically reviewed within 5-7 business days.  
            📱 Status Updates: Check your email and phone for updates from the company.  
            🔄 Follow Up: You can follow up after 1 week if you don't hear back.
            """)
            application_data = {
                'name': applicant_name,
                'email': email,
                'mobile': mobile,
                'internship_id': internship_id,
                'internship_title': internship_title,
                'company': company_name,
                'application_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Applied'
            }
            if 'applications' not in st.session_state:
                st.session_state.applications = []
            st.session_state.applications.append(application_data)
            st.balloons()
            # --- Send confirmation email and SMS ---
            send_application_email(email, applicant_name, internship_title, company_name, application_id)
            send_application_sms(mobile, applicant_name, internship_title, company_name, application_id)
            if st.button("🔍 Browse More Internships", type="secondary"):
                st.session_state.show_application_form = False
                st.rerun()
    if cancel_button:
        st.session_state.show_application_form = False
        st.rerun()

def main():
    st.set_page_config(
        page_title="PM Internship Recommendation Engine", 
        page_icon="🎯",
        layout="wide"
    )
    st.title("🎯 PM Internship Recommendation Engine")
    st.markdown("Find the perfect internship match based on your profile!")

    # --- Session state for unique recommendations ---
    if 'show_application_form' not in st.session_state:
        st.session_state.show_application_form = False
    if 'selected_internship' not in st.session_state:
        st.session_state.selected_internship = None
    if 'saved_jobs' not in st.session_state:
        st.session_state.saved_jobs = []
    if 'recommendations' not in st.session_state:
        st.session_state.recommendations = []
    if 'shown_internship_ids' not in st.session_state:
        st.session_state.shown_internship_ids = set()

    students, internships, applications, companies, skills_master = load_data()
    if internships is None:
        st.error("Failed to load datasets. Please ensure all CSV files are available.")
        return

    recommender = InternshipRecommender(internships, companies)

    # --- Sidebar for user input ---
    st.sidebar.header("📝 Your Profile")
    def update_recommendations():
        # Reset shown_internship_ids when education level changes
        st.session_state.shown_internship_ids = set()
        st.session_state.recommendations = get_unique_recommendations(recommender, st.session_state.student_profile, st.session_state.shown_internship_ids, top_k=4)

    def get_unique_recommendations(recommender, student_profile, shown_ids, top_k=5):
        all_recs = recommender.get_recommendations(student_profile, top_k=100)
        unique_recs = []
        for rec in all_recs:
            internship_id = rec['internship']['internship_id']
            if internship_id not in shown_ids:
                unique_recs.append(rec)
                shown_ids.add(internship_id)
            if len(unique_recs) >= top_k:
                break
        return unique_recs

    name = st.sidebar.text_input("Name", "Your Name")
    age = st.sidebar.slider("Age", 18, 30, 22)
    education_level = st.sidebar.selectbox(
        "Education Level (Only internships requiring this level will be shown)",
        ["High School", "Diploma", "Undergraduate", "post graduate"],
        key="education_level",
        on_change=update_recommendations
    )
    cgpa = st.sidebar.slider("CGPA/Percentage", 4.0, 10.0, 7.5, 0.1)
    available_skills = skills_master['skill_name'].tolist() if skills_master is not None else [
        'Python', 'Java', 'Excel', 'Communication', 'Leadership', 'Problem Solving',
        'Data Analysis', 'Social Media', 'Teaching', 'Research', 'MS Office'
    ]
    selected_skills = st.sidebar.multiselect(
        "Your Skills (Select multiple)",
        available_skills,
        default=['Communication', 'Problem Solving']
    )
    preferred_sector = st.sidebar.selectbox(
        "Preferred Sector",
        ['IT', 'Healthcare', 'Education', 'Finance', 'Marketing', 'Agriculture', 
         'Manufacturing', 'Government']
    )
    preferred_location = st.sidebar.selectbox(
        "Preferred Location",
        ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune', 
         'Rural', 'Any']
    )
    location_type = st.sidebar.selectbox("Current Location Type", ['Urban', 'Rural', 'Semi-Urban'])
    digital_literacy = st.sidebar.selectbox("Digital Literacy", ['Basic', 'Intermediate', 'Advanced'])

    st.session_state.student_profile = {
        'name': name,
        'age': age,
        'education_level': education_level,
        'cgpa': cgpa,
        'skills': ', '.join(selected_skills),
        'preferred_sector': preferred_sector,
        'preferred_location': preferred_location,
        'location_type': location_type,
        'digital_literacy': digital_literacy
    }

    # --- Main content area ---
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🔍 Get Personalized Recommendations", type="primary"):
            if not selected_skills:
                st.warning("⚠ Please select at least one skill to get better recommendations.")
                return
            # Get unique recommendations, update shown_internship_ids
            st.session_state.recommendations = get_unique_recommendations(recommender, st.session_state.student_profile, st.session_state.shown_internship_ids, top_k=5)

        recommendations = st.session_state.get('recommendations', [])
        if recommendations:
            st.success(f"✅ Found {len(recommendations)} matching internships for you!")
            for i, rec in enumerate(recommendations, 1):
                internship = rec['internship']
                match_score = rec['match_percentage']
                with st.container():
                    st.markdown(f"""
                    <div style="
                        border: 2px solid #e1f5fe; 
                        border-radius: 10px; 
                        padding: 20px; 
                        margin: 15px 0;
                        background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%);
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <h3 style="color: #1976d2; margin: 0 0 10px 0;">#{i} {internship['title']}</h3>
                                <p style="color: #424242; font-size: 16px; margin: 5px 0;">
                                    <strong>🏢 Company:</strong> {internship['company']}
                                </p>
                                <p style="color: #424242; margin: 5px 0;">
                                    <strong>🎓 Education Required:</strong> {internship['education_requirement']}
                                </p>
                                <p style="color: #424242; margin: 5px 0;">
                                    <strong>🎯 Sector:</strong> <span style="background: #e3f2fd; padding: 3px 8px; border-radius: 12px;">{internship['sector']}</span>
                                </p>
                                <p style="color: #424242; margin: 5px 0;">
                                    <strong>📍 Location:</strong> {internship['location']}
                                </p>
                                <p style="color: #424242; margin: 5px 0;">
                                    <strong>⏱ Duration:</strong> {internship['duration_months']} months
                                </p>
                                <p style="color: #424242; margin: 5px 0;">
                                    <strong>💰 Stipend:</strong> ₹{internship['stipend']:,}/month
                                </p>
                                <p style="color: #424242; margin: 5px 0;">
                                    <strong>🛠 Skills Required:</strong> {internship['required_skills']}
                                </p>
                                <p style="color: #666; font-size: 14px; margin: 10px 0 0 0;">
                                    {internship['description']}
                                </p>
                            </div>
                            <div style="text-align: center; min-width: 100px;">
                                <div style="
                                    background: {'#4caf50' if match_score >= 80 else '#ff9800' if match_score >= 60 else '#2196f3'};
                                    color: white;
                                    padding: 10px;
                                    border-radius: 50%;
                                    font-size: 18px;
                                    font-weight: bold;
                                    margin-bottom: 5px;
                                ">
                                    {match_score}%
                                </div>
                                <small style="color: #666;">Match</small>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    col_apply, col_save = st.columns([1, 1])
                    with col_apply:
                        if st.button(f"📝 Apply Now", key=f"apply_{i}_{internship['internship_id']}", type="primary"):
                            st.session_state.show_application_form = True
                            st.session_state.selected_internship = internship
                            st.rerun()
                    with col_save:
                        # Prevent duplicate saves
                        already_saved = any(
                            job['title'] == internship['title'] and job['company'] == internship['company']
                            for job in st.session_state.saved_jobs
                        )
                        if st.button(f"💾 Save", key=f"save_{i}_{internship['internship_id']}"):
                            if not already_saved:
                                saved_job = {
                                    'title': internship['title'],
                                    'company': internship['company'],
                                    'sector': internship['sector'],
                                    'location': internship['location'],
                                    'stipend': internship['stipend'],
                                    'saved_date': datetime.now().strftime('%Y-%m-%d')
                                }
                                st.session_state.saved_jobs.append(saved_job)
                                st.success(f"📌 {internship['title']} saved to your wishlist!")
                            else:
                                st.info("Already saved to your wishlist.")

        elif st.session_state.get('recommendations', None) is not None:
            st.warning("😔 No matching internships found for your education level. Try adjusting your preferences.")

    with col2:
        st.subheader("📊 Dashboard")
        if internships is not None:
            total_internships = len(internships)
            available_sectors = internships['sector'].nunique()
            avg_stipend = internships['stipend'].mean()
            st.metric("Total Internships", f"{total_internships:,}")
            st.metric("Available Sectors", available_sectors)
            st.metric("Avg. Stipend", f"₹{avg_stipend:,.0f}")
            if 'applications' in st.session_state and st.session_state.applications:
                st.subheader("📋 Your Applications")
                for app in st.session_state.applications[-3:]:
                    st.markdown(f"""
                    <div style="background: #f0f8f0; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #4caf50;">
                        <strong>{app['internship_title']}</strong><br>
                        <small>Applied on {app['application_date'][:10]}</small>
                    </div>
                    """, unsafe_allow_html=True)
            if st.session_state.saved_jobs:
                st.subheader("💾 Saved Jobs")
                for job in st.session_state.saved_jobs[-3:]:
                    st.markdown(f"""
                    <div style="background: #fff3e0; padding: 10px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #ff9800;">
                        <strong>{job['title']}</strong><br>
                        <small>{job['company']} | Saved on {job['saved_date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            st.subheader("🎯 Internships by Sector")
            sector_counts = internships['sector'].value_counts()
            st.bar_chart(sector_counts)

    # Show application form if triggered
    if st.session_state.show_application_form and st.session_state.selected_internship is not None:
        internship = st.session_state.selected_internship
        show_application_form(
            internship['title'], 
            internship['company'], 
            internship['internship_id']
        )
        return

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🚀 <strong>PM Internship Scheme - Empowering India's Youth</strong></p>
        <p><em>Making internship discovery simple for everyone!</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()