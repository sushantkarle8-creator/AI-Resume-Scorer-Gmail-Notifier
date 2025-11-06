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

# Gemini API setup
configure(api_key="")  # Replace with your API key
gemini_model = GenerativeModel("models/gemini-2.5-pro")

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Authenticate and build Gmail API service
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

    service = build('gmail', 'v1', credentials=creds)
    return service

# Extract text from uploaded PDF resume
def extract_text_from_pdf(uploaded_file):
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        return " ".join(page.get_text() for page in doc)

# Score the resume using Gemini
def score_resume(text):
    prompt = f"""
    You are an AI resume reviewer. Score the following resume text out of 10 based on its structure, skills, experience, and relevance for a software developer role. Explain the score briefly.

    Resume Text:
    {text}
    """
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

# Send email using Gmail API
def send_email(service, to, subject, body):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_body = {'raw': raw}
    sent_message = service.users().messages().send(userId="me", body=message_body).execute()
    return sent_message

# Streamlit UI
st.title("🤖 Resume Scorer + Gmail Notifier (Gemini + Gmail API)")

uploaded_file = st.file_uploader("Upload a PDF Resume", type=["pdf"])
email = st.text_input("Enter recipient email address")

if uploaded_file and email:
    st.write("📄 Extracting resume text...")
    resume_text = extract_text_from_pdf(uploaded_file)

    st.write("💡 Scoring resume using Gemini...")
    feedback = score_resume(resume_text)
    st.write("🔍 Gemini Feedback:")
    st.success(feedback)

    if st.button("📧 Send Email with Feedback"):
        try:
            service = get_gmail_service()
            subject = "Your Resume Feedback"
            body = f"Hi,\n\nHere is your resume feedback:\n\n{feedback}\n\nBest regards,\nAI Resume Screener"
            send_email(service, email, subject, body)
            st.success("Email sent successfully!")
        except Exception as e:
            st.error(f"Failed to send email: {e}")
