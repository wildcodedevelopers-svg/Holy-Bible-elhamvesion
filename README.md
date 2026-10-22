# ELHAM STUDIOS — Sermon Engine Prototype

## Files

- `index.html`: mobile-first Bible reader, local notes/bookmarks, 7-day plan, sermon UI and local outline fallback.
- `server.py`: optional backend for AI-written sermons, Bible Q&A, and a configurable non-Google voice endpoint.
- `requirements.txt`: Python dependencies.

## What works now?

- The Bible reader fetches KJV or WEB from bible-api.com and needs internet.
- Notes, bookmarks, and plan progress are saved in the browser on this device.
- Without a backend, the sermon button creates a clearly labelled local starter outline, not a complete AI-generated sermon.
- Full AI sermon writing and Q&A require an OpenAI-compatible chat-completions backend and credentials.
- Natural audio requires a separate licensed non-Google TTS endpoint that accepts POST JSON `{ "text": "...", "voice": "..." }` and returns audio bytes.
- Never put secret API keys in `index.html` or a public GitHub repository.

## Run the backend

1. Install Python 3.10+.
2. Run `pip install -r requirements.txt`.
3. Configure these environment variables on your backend host:
   - `LLM_BASE_URL`: provider base URL before `/chat/completions`.
   - `LLM_API_KEY`: secret API key.
   - `LLM_MODEL`: exact model identifier.
   - `TTS_API_URL`: optional licensed non-Google voice endpoint.
   - `TTS_API_KEY`: optional voice-service key.
4. Run `python server.py`.

## Deployment

GitHub Pages can host `index.html`, but it cannot run `server.py`.

Host the backend separately and configure the frontend's `API_BASE` value to the backend URL. Enable CORS on the backend if frontend and backend use different domains.

Free tiers and API quotas can change, sleep, or be rate-limited.

## Preacher profiles

The profiles describe broad communication qualities only. They do not clone or claim to reproduce Philip Anthony Mitchell or Billy Graham. Use authorised recordings or licensed voice models if you later add a real person's voice.
