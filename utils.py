import fitz  # PyMuPDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def rank_resumes(jd_text, resumes_text, filenames):
    vectorizer = TfidfVectorizer(stop_words='english')
    vectors = vectorizer.fit_transform([jd_text] + resumes_text)
    jd_vector = vectors[0]
    resume_vectors = vectors[1:]
    scores = cosine_similarity(jd_vector, resume_vectors).flatten()

    ranked = sorted(zip(filenames, scores), key=lambda x: x[1], reverse=True)
    return ranked
