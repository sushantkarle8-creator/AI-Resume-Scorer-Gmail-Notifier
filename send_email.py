import os
import base64
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request  # ✅ FIXED: Missing import
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("")

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Authenticate and build Gmail service
def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # ✅ Now properly imported
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

# Gemini Email Generation
def generate_email_content(candidate_name, job_title="Software Engineer"):
    prompt = f"""
    Compose a professional email to inform {candidate_name} that they have been shortlisted for the position of {job_title}.
    Keep it polite, clear, and inviting. Mention that their resume was impressive and they will receive further details shortly.
    """
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text.strip()

# Build MIME Email
def create_message(sender, to, subject, body_text, attachment_file=None):
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject

    message.attach(MIMEText(body_text, "plain"))

    if attachment_file:
        with open(attachment_file, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment_file))
            message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw_message}

# Send Gmail API Message
def send_email_with_gmail(to, subject, body, attachment_path=None):
    service = get_gmail_service()
    sender = "me"
    message = create_message(sender, to, subject, body, attachment_path)
    sent_message = service.users().messages().send(userId=sender, body=message).execute()
    return sent_message

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Gmail API Email Sender", layout="centered")
st.title("📧 Gemini + Gmail API Email Sender")

uploaded_file = st.file_uploader("Upload Top Resume (PDF)", type=["pdf"])
email = st.text_input("Enter Candidate's Email")
job_title = st.text_input("Job Title", value="Software Engineer")

if uploaded_file and st.button("✍️ Generate Email Content"):
    candidate_name = uploaded_file.name.split('.')[0]
    try:
        email_content = generate_email_content(candidate_name, job_title)
        st.session_state['email_body'] = email_content
        st.markdown("### ✉️ Email Preview")
        st.text_area("Generated Email", value=email_content, height=200)
    except Exception as e:
        st.error(f"Gemini API error: {e}")

if email and 'email_body' in st.session_state and uploaded_file and st.button("📤 Send Email"):
    try:
        temp_path = "temp_resume.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        result = send_email_with_gmail(
            email,
            f"Interview Opportunity for {job_title}",
            st.session_state['email_body'],
            temp_path
        )
        st.success(f"✅ Email sent! Message ID: {result['id']}")
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
