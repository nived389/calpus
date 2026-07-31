# Calpus — Presentation AI server

This tiny server lets the presentation builder draft slides with **Gemini** or **ChatGPT**.
The API keys live **here on your machine**, inside `.env` — the website never sees them.

## ⚠️ Security first
- **Never put API keys in `index.html`** (or any file served to browsers). Anyone who opens the
  page could read them and spend your money. That is why this server exists.
- `.env` is **git-ignored** and must never be uploaded or deployed.
- The two keys you pasted in chat should be treated as **exposed** — please **rotate them**:
  - OpenAI: https://platform.openai.com/api-keys → revoke old, create new → paste into `.env`
  - Gemini: https://aistudio.google.com/apikey → a real Gemini API key looks like `AIza...`
    (the `AQ.Ab8...` value you gave is not the usual key format, so Gemini may reject it —
    generate a fresh key in Google AI Studio and put it in `.env`).

## Run it
```bash
cd presentation-server
node server.mjs
```
You should see `Calpus presentation server on http://localhost:8787` and both keys `loaded`.

Then open the site **served over http** (not file://) so the browser can call the server:
```bash
cd ..            # the vidya folder
python3 -m http.server 8000
```
Open http://localhost:8000 → log in → **Make a presentation** → pick Gemini or ChatGPT →
**Generate slides**. Real AI slides appear; if the server is off, you get a template draft.

## How it works
- `index.html` → `POST http://localhost:8787/api/slides` with `{engine, topic, slides, lang}`
- `server.mjs` reads the key from `.env`, calls the chosen model, returns `{"slides":[{t,b:[]}]}`
- `lang: "ml"` makes the model write the slides in Malayalam.

## Notes
- Requires Node 18+ (built-in `fetch`).
- Claude is shown as an option but no Claude key is set — it falls back to a template draft.
  Add `ANTHROPIC_API_KEY` and an Anthropic branch to `server.mjs` if you want Claude too.
- Put API keys in `API-KEYS.txt` (git-ignored), never in this README or any file served to browsers.

