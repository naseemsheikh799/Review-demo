import os
from flask import Flask, render_template, request, jsonify
from google import genai

app = Flask(__name__)

# Keep the Gemini key on the server. Never place it in HTML/JavaScript.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Demo Business")
GOOGLE_REVIEW_URL = os.getenv(
    "GOOGLE_REVIEW_URL",
    "https://g.page/r/CcXBFrsnVB3sECE/review"
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

@app.get("/")
def home():
    return render_template(
        "index.html",
        hospital_name=BUSINESS_NAME,
        google_review_url=GOOGLE_REVIEW_URL
    )

@app.post("/api/draft")
def draft_review():
    if client is None:
        return jsonify(error="Gemini API key is not configured on the server."), 503

    data = request.get_json(force=True)
    answers = {
        "visit_reason": (data.get("visit_reason") or "").strip(),
        "experience": (data.get("experience") or "").strip(),
        "staff_doctor": (data.get("staff_doctor") or "").strip(),
        "improvement": (data.get("improvement") or "").strip(),
    }
    if not answers["experience"] or not answers["visit_reason"]:
        return jsonify(error="Please answer at least the first two questions."), 400

    prompt = f"""
Create a concise, natural Google review draft using ONLY the customer's answers below.
Do not invent experiences, diagnoses, treatment outcomes, medical claims, staff names,
or details. Do not exaggerate or make it promotional. Omit blank answers.
Write in the same language as the answers. Return only the draft.
The customer must be able to edit it before deciding whether to post.

Reason for visit: {answers['visit_reason']}
Their experience: {answers['experience']}
Doctor/staff mention (optional): {answers['staff_doctor']}
Suggestion for improvement (optional): {answers['improvement']}
"""
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        draft = (response.text or "").strip()
        if not draft:
            raise ValueError("Gemini returned an empty draft")
        return jsonify(draft=draft)
    except Exception:
        app.logger.exception("Gemini review drafting failed")
        return jsonify(error="AI drafting is temporarily unavailable. Please try again."), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)
