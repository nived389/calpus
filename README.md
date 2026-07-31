# Calpus — AI Study Companion for Calicut University

**Calpus** (Calicut + campus) is the AI agent for your 3D-animated education site. It's scoped to
**Calicut University students**. Students ask a topic by **text or voice** and Calpus answers *only*
from **your uploaded database** (notes + 5–6 years of past papers), explains the topic **with 2/5/10-mark
questions**, builds **editable AI presentations**, and predicts the **next exam** from past-paper patterns.

---

## Files
| File | What it is |
|------|-----------|
| `index.html` | **Working front-end prototype** — open in Chrome/Edge. Self-contained (Three.js + GSAP via CDN). |

**Run it** (voice + downloads work best when served):
```bash
cd vidya && python3 -m http.server 8000
```
Open `http://localhost:8000`. Voice input needs Chrome or Edge.

Demo entry points: **Try the demo** (chat) · **Admin login** in the footer (`admin@calpus` / `123456`).

---

## What's live in the demo
- ✅ **Cute animated Calpus** — glowing orb with a graduation cap, sparkly eyes, rosy cheeks, and a
  periodic playful **roll**. A **mini Calpus** also sits in the chat header.
- ✅ **More exciting scroll** — scroll progress bar, hero that lifts/fades as you scroll, parallax section
  titles, and a 3D particle field that **speeds up and zooms the deeper you scroll**.
- ✅ **Topic → explanation + marks-wise questions** — every topic answer appends 2-mark, 5-mark and
  10-mark questions in the Calicut University pattern.
- ✅ **Exam Radar** — analyses past-paper patterns and predicts the **next exam's** likely questions.
- ✅ **Presentation builder** — pick **Gemini / ChatGPT / Claude**, generate slides, **edit any text
  inline**, add/delete slides, and **export**.
- ✅ **Voice input** + **translate** (Malayalam first, 12 languages).
- ✅ **Normal email signup** (no college mail needed) capturing name, phone, email, college, course,
  subject, semester.
- ✅ **2-day free trial for everyone**, then ₹10/month via UPI (`niveddevan389-1@okicici`).
- ✅ **One login per device** — a single active session is locked to the device; a second tab/device
  logging in signs the first one out. "Log out" frees the device.
- ✅ **Gated admin console** — ID + login code, upload new data, **all student logins table with
  Export CSV** (real download), free-access rules, price/trial/UPI/offer settings.

Everything AI-related is a **stub** (`generateAnswer()`, `slidesFor()`). Below is how to make it real.

---

## Making it real — backend

Recommended low-cost stack:
```
Next.js  →  Supabase (Auth + Postgres + Storage)  →  RAG API  →  AI (Gemini/ChatGPT/Claude)  →  Razorpay UPI Autopay
```

1. **Auth + one-session lock** → Supabase Auth. Enforce single active session server-side by storing one
   `session_token` per user and rejecting others (the client lock in the demo is the UX layer of this).
2. **Upload → "AI reads everything" (RAG)** → extract PDF text → chunk → embeddings → **vector DB**
   (`pgvector`), tagged by course/semester. On a question: retrieve top chunks → send to the LLM →
   grounded answer with citations. Replace `generateAnswer()` with `fetch('/api/ask')`.
3. **Presentations** → send retrieved chunks + "make slide JSON" to the **selected engine**
   (Gemini / OpenAI / Claude). Return editable slide data; export real `.pptx` with `pptxgenjs`.
   Swap `slidesFor()` and `exportPPT()` for these calls.
4. **Exam Radar** → parse each year's paper → tag topics → score by frequency × recency → predict.
5. **Translation** → **Bhashini** (free, great for Indian languages) or Google Translate.
6. **Admin data export** → the CSV button works client-side now; back it with a `/api/admin/logins`
   query behind the admin auth. Keep the admin code server-verified, never in client JS.

### ⚠️ Payments — the one hard constraint
A plain GPay/PhonePe/`upi://` link is **one-time only** — it cannot auto-charge ₹10 monthly. Real monthly
auto-debit needs **UPI Autopay (e-mandate)** via **Razorpay / Cashfree / PhonePe PG**, which requires a
**registered business + KYC**. Flow: student approves a mandate once → gateway debits ₹10/month → your
webhook keeps `plan = active`. The demo keeps the one-tap ₹10 link as the manual fallback; money settles
to the bank linked to `niveddevan389-1@okicici`.

**Trial logic:** on signup, set `trial_ends = now + 2 days`. Until then everyone has full access; after,
the app requires an active Pro subscription (or a free-access rule from the admin console).

---

## Build order
1. Next.js + Supabase auth + onboarding (+ single-session enforcement).
2. Upload → RAG pipeline (unlocks the whole product).
3. Presentation generation via Gemini/ChatGPT/Claude with real `.pptx` export.
4. Razorpay UPI Autopay + 2-day trial gating.
5. Exam Radar analytics + Bhashini translation.

Want me to scaffold the **Next.js + Supabase + RAG** project next, wired to this same design?
