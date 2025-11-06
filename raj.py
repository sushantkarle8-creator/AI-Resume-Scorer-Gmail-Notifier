import os
import fitz  # PyMuPDF
import base64
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.generativeai import GenerativeModel, configure
from email.mime.text import MIMEText
import pickle

# ---------------- Gemini API Setup ---------------- #
configure(api_key="")  # Replace with your valid Gemini API Key
gemini_model = GenerativeModel("models/gemini-2.5-pro")

# ---------------- Gmail API Setup ---------------- #
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

# ---------------- Resume Processing ---------------- #
def extract_text_from_pdf(uploaded_file):
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        return " ".join(page.get_text() for page in doc)

def skill_match_score(text, required_skills):
    text = text.lower()
    return sum(1 for skill in required_skills if skill in text)

def gemini_analysis(text, role):
    prompt = f"""
    You are an AI recruiter. Analyze this resume and provide:
    1. Strengths
    2. Weaknesses
    3. Fit for the role of {role}
    4. Final score out of 10

    Resume Text:
    {text}
    """
    return gemini_model.generate_content(prompt).text.strip()

def send_email(service, to, subject, body):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_body = {'raw': raw}
    return service.users().messages().send(userId="me", body=message_body).execute()

# ---------------- Streamlit UI ---------------- #
st.set_page_config(page_title="Resume Screener AI", layout="wide")
st.title("📊 Multi-Resume Ranker + AI Shortlister + Gmail Notifier")

# Upload resumes
uploaded_files = st.file_uploader("📎 Upload Multiple PDF Resumes", type=["pdf"], accept_multiple_files=True)

# Select role
role = st.selectbox("🎯 Select Job Role", [
    "Software Developer",
    "Data Scientist",
    "Frontend Engineer",
    "Backend Developer",
    "AI/ML Engineer",
    "DevOps Engineer",
    "Custom"
])
custom_role = st.text_input("✍️ Enter Custom Role (if 'Custom' selected):")
selected_role = custom_role if role == "Custom" else role

# Required skills
required_skills = st.text_input(f"🛠️ Enter required skills for '{selected_role}' (comma-separated):").lower().split(',')

# Candidate emails
candidate_emails = st.text_area("📧 Enter candidate emails (in order of resume upload, comma-separated):").split(',')

# Process resumes
if uploaded_files and required_skills and candidate_emails and selected_role:
    all_resumes = []
    st.info("🔍 Analyzing resumes for skill matching...")

    for i, file in enumerate(uploaded_files):
        resume_text = extract_text_from_pdf(file)
        score = skill_match_score(resume_text, required_skills)
        all_resumes.append({
            'name': file.name,
            'text': resume_text,
            'score': score,
            'file': file,
            'email': candidate_emails[i].strip() if i < len(candidate_emails) else "N/A"
        })

    # Rank resumes
    sorted_resumes = sorted(all_resumes, key=lambda x: x['score'], reverse=True)
    top_3 = sorted_resumes[:3]

    st.subheader("🏆 Top 3 Candidates by Skill Match")
    analysis_results = []

    for idx, candidate in enumerate(top_3):
        with st.expander(f"Candidate {idx+1}: {candidate['name']} (Score: {candidate['score']})"):
            report = gemini_analysis(candidate['text'], selected_role)
            candidate['analysis'] = report
            st.text_area("🧠 Gemini Feedback", report, height=200)
            analysis_results.append(candidate)

    if st.button("📨 Send Emails to Top 3 Candidates"):
        try:
            service = get_gmail_service()
            for candidate in analysis_results:
                email_body = f"""
Dear {candidate['name'].split('.')[0]},

Congratulations! After a detailed review of your resume, we are pleased to inform you that you have been shortlisted for the next stage of our hiring process for the **{selected_role}** position.

Gemini AI's feedback on your resume:
{candidate['analysis']}

We’ll be in touch soon with the next steps.

Warm regards,  
HR Team
"""
                send_email(service, candidate['email'], f"You've been shortlisted for {selected_role} role!", email_body)
            st.success("✅ Emails sent to top 3 candidates successfully!")
        except Exception as e:
            st.error(f"❌ Failed to send emails: {e}")
