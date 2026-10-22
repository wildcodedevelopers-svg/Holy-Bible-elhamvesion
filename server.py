import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Configure these as environment variables on your backend host.
# Never put secret keys in index.html or commit them to GitHub.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
TTS_API_URL = os.getenv("TTS_API_URL", "")
TTS_API_KEY = os.getenv("TTS_API_KEY", "")


def ai_configured():
    return bool(LLM_BASE_URL and LLM_API_KEY and LLM_MODEL)


def chat_completion(messages, max_tokens=2400, temperature=0.65):
    if not ai_configured():
        raise RuntimeError(
            "AI model is not configured. Set LLM_BASE_URL, "
            "LLM_API_KEY, and LLM_MODEL."
        )

    url = LLM_BASE_URL + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    response = requests.post(
        url, headers=headers, json=payload, timeout=180
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def verse_context(payload):
    book = str(payload.get("book", "Unknown"))[:80]
    chapter = int(payload.get("chapter", 1))
    translation = str(payload.get("translation", "kjv")).lower()
    verses = payload.get("verses") or []
    safe_verses = []

    for item in verses[:200]:
        try:
            number = int(item.get("verse", 0))
            text = str(item.get("text", ""))[:1800]
            safe_verses.append(
                f"{book} {chapter}:{number} — {text}"
            )
        except (TypeError, ValueError, AttributeError):
            continue

    return book, chapter, translation, "\n".join(safe_verses)


@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "ai_configured": ai_configured(),
        "voice_configured": bool(TTS_API_URL)
    })


@app.post("/api/sermon")
def sermon():
    payload = request.get_json(silent=True) or {}

    try:
        book, chapter, translation, context = verse_context(payload)

        if not context:
            return jsonify({
                "error": "Load the Bible chapter in the reader before requesting a sermon."
            }), 400

        focus = str(payload.get("focus", "prayer"))[:80]
        profile = str(payload.get("profile", "mitchell"))[:40]

        profile_guidance = {
            "mitchell": (
                "Use passionate, Scripture-centred exposition, strong rhetorical "
                "emphasis, clear structure, and practical challenge. Do not imitate "
                "or claim to reproduce any real preacher's voice, identity, "
                "catchphrases, or exact mannerisms."
            ),
            "billy": (
                "Use clear, accessible evangelistic communication, hope, Gospel "
                "focus, and a compassionate invitation. Do not imitate or claim "
                "to reproduce any real preacher's voice, identity, catchphrases, "
                "or exact mannerisms."
            ),
            "elham": (
                "Use gentle, reflective, Scripture-centred teaching and a prayerful tone."
            )
        }.get(profile, "Use a clear, compassionate, Scripture-centred teaching style.")

        system = (
            "You are the sermon-writing component of ELHAM STUDIOS. Write original "
            "Christian teaching grounded in the supplied Bible chapter. Respect "
            "the text's context. Do not invent quotations, historical facts, or "
            "verse citations. Distinguish direct biblical statements from "
            "interpretation. If the supplied excerpt is incomplete, say so and "
            "avoid unsupported claims. Never present yourself as a pastor or as "
            "God speaking directly."
        )

        user = f"""Write a manuscript intended to take about 15 minutes to preach
(roughly 1,700–2,000 words; if output limits prevent this, be transparent).

Passage: {book} {chapter} ({translation.upper()})
Primary focus: {focus}
Delivery guidance: {profile_guidance}

Required structure:
1. Title and central biblical message
2. Opening that connects the listener to the passage
3. Brief context and careful explanation of the actual chapter
4. Three substantial sermon movements, each anchored to specific supplied verses
5. Prayer and spiritual-growth application for the week
6. Reflection questions
7. A closing prayer
8. A short note naming any interpretive uncertainty

Use the supplied passage as the primary source. Do not make every chapter
into a sermon about prayer if the text does not support that emphasis. Use
verse references only when present in the supplied chapter; do not fabricate
citations. This must be an original sermon, not a rewrite of a named preacher's
existing sermon.

SUPPLIED CHAPTER TEXT:
{context}
"""

        result = chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=3800
        )

        title = (
            result.splitlines()[0].replace("#", "").strip()[:120]
            or f"{book} {chapter}: Prayer and Growth"
        )

        return jsonify({
            "sermon": result,
            "title": title,
            "source": f"{book} {chapter}",
            "minutes": 15
        })

    except requests.HTTPError as exc:
        detail = (
            exc.response.text[:500]
            if exc.response is not None else str(exc)
        )
        return jsonify({
            "error": "The configured AI provider returned an error.",
            "detail": detail
        }), 502

    except Exception as exc:
        return jsonify({"error": str(exc)}), 503


@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()[:1200]

    if not question:
        return jsonify({"error": "Question is required."}), 400

    try:
        book, chapter, translation, context = verse_context(payload)

        if not context:
            return jsonify({"error": "Load a chapter first."}), 400

        system = (
            "You are ELHAM STUDIOS' Bible study assistant. Answer with humility, "
            "distinguish text from interpretation, consider the immediate context, "
            "and cite only verses included in the supplied chapter text. Do not "
            "invent citations. If the chapter does not answer the question, say "
            "so and suggest what context would be needed."
        )

        user = f"""Passage: {book} {chapter} ({translation.upper()})
Chapter text:
{context}

Question: {question}

Answer clearly and concisely, with verse references from the supplied text only.
"""

        answer = chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=900,
            temperature=0.3
        )

        return jsonify({"answer": answer})

    except requests.HTTPError as exc:
        detail = (
            exc.response.text[:500]
            if exc.response is not None else str(exc)
        )
        return jsonify({
            "error": "The configured AI provider returned an error.",
            "detail": detail
        }), 502

    except Exception as exc:
        return jsonify({"error": str(exc)}), 503


@app.post("/api/voice")
def voice():
    if not TTS_API_URL:
        return jsonify({
            "error": (
                "No non-Google TTS provider is configured. Set TTS_API_URL "
                "to a licensed service endpoint that accepts JSON {text, voice} "
                "and returns audio bytes."
            )
        }), 503

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    voice = str(payload.get("voice", "elham"))[:80]

    if not text:
        return jsonify({"error": "Text is required."}), 400

    headers = {"Content-Type": "application/json"}
    if TTS_API_KEY:
        headers["Authorization"] = f"Bearer {TTS_API_KEY}"

    try:
        response = requests.post(
            TTS_API_URL,
            headers=headers,
            json={"text": text, "voice": voice},
            timeout=240
        )
        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", "audio/mpeg"
        )

        if "audio" not in content_type and "octet-stream" not in content_type:
            return jsonify({
                "error": (
                    "TTS endpoint did not return audio. Configure an endpoint "
                    "that returns audio bytes."
                )
            }), 502

        return Response(response.content, content_type=content_type)

    except requests.RequestException as exc:
        return jsonify({"error": f"TTS request failed: {exc}"}), 502


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
