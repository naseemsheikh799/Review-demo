import os
import logging
from flask import Flask, render_template, request, jsonify
from google import genai

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Sky High English School")
GOOGLE_REVIEW_URL = os.getenv("GOOGLE_REVIEW_URL", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

@app.get("/")
def home():
    return render_template(
        "index.html",
        school_name=BUSINESS_NAME,
        google_review_url=GOOGLE_REVIEW_URL
    )

@app.post("/api/draft")
def draft_review():
    if client is None:
        return jsonify(error="The AI service is not configured yet. Please contact the school."), 503

    data = request.get_json(silent=True) or {}
    language = data.get("language", "en")
    language = "hi" if language == "hi" else "en"

    answers = {
        "admission": (data.get("admission") or "").strip(),
        "teaching": (data.get("teaching") or "").strip(),
        "overall": (data.get("overall") or "").strip(),
    }

    if not all(answers.values()):
        return jsonify(error="Please answer all three questions before creating your draft."), 400

    if any(len(value) > 1500 for value in answers.values()):
        return jsonify(error="Please keep each answer under 1,500 characters."), 400

    output_language = "Hindi" if language == "hi" else "English"
    prompt = f"""
You help a parent write a truthful review draft about {BUSINESS_NAME}.
Write in {output_language}, using only the parent's own statements below.
Do not invent facts, outcomes, facilities, achievements, names, or claims.
Do not turn neutral or negative feedback into praise. Keep the tone natural,
balanced, concise, and in the first person. Do not add a rating.
Return only the review draft, ready for the parent to edit.

Admission experience: {answers['admission']}
Teaching and learning experience: {answers['teaching']}
Overall school experience: {answers['overall']}
"""
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        draft = (response.text or "").strip()
        if not draft:
            app.logger.error("Gemini returned an empty review draft.")
            return jsonify(error="The AI returned an empty response. Please try again."), 502
        return jsonify(draft=draft)
    except Exception:
        app.logger.exception("Gemini review drafting failed")
        return jsonify(
            error="AI drafting is temporarily unavailable. Please try again later."
        ), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)
