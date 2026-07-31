// Calpus — local AI server.
// Holds the API keys server-side and powers BOTH the presentation builder and the chat answers
// with Gemini, ChatGPT (OpenAI) or Claude (Anthropic).
// The website (index.html) calls http://localhost:8787 and NEVER sees the keys.
//
//   Node 18+ required (built-in fetch).  Run:  node server.mjs
//
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));

// --- tiny key loader (no dependencies) ---
// Reads from BOTH ".env" (hidden) and "API-KEYS.txt" (visible, easy to edit).
// Whatever is in API-KEYS.txt wins, so you can paste keys into that plain file.
function loadKeys() {
  for (const name of ['.env', 'API-KEYS.txt']) {
    try {
      const txt = readFileSync(join(HERE, name), 'utf8');
      for (const line of txt.split('\n')) {
        if (line.trim().startsWith('#')) continue;
        const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
        if (m && m[2].trim()) process.env[m[1]] = m[2].trim();
      }
    } catch { /* file not present — skip */ }
  }
}
loadKeys();
const OPENAI_KEY = process.env.OPENAI_API_KEY || '';
const GEMINI_KEY = process.env.GEMINI_API_KEY || '';
const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY || '';
const PORT = process.env.PORT || 8787;

// ---------- server-side OTP store (email -> {code, exp, attempts}) ----------
const OTPS = new Map();
const OTP_TTL = 10 * 60 * 1000; // 10 minutes
function newCode() { return String(Math.floor(100000 + Math.random() * 900000)); }

// ---------- model calls: each takes a prompt, returns plain text ----------
async function askOpenAI(prompt, json) {
  if (!OPENAI_KEY) throw new Error('OPENAI_API_KEY missing');
  const body = {
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.5,
  };
  if (json) body.response_format = { type: 'json_object' };
  const r = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${OPENAI_KEY}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('OpenAI ' + r.status + ' ' + (await r.text()).slice(0, 200));
  const j = await r.json();
  return j.choices?.[0]?.message?.content || '';
}
async function askGemini(prompt) {
  if (!GEMINI_KEY) throw new Error('GEMINI_API_KEY missing');
  const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + encodeURIComponent(GEMINI_KEY);
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
  });
  if (!r.ok) throw new Error('Gemini ' + r.status + ' ' + (await r.text()).slice(0, 200));
  const j = await r.json();
  return j.candidates?.[0]?.content?.parts?.[0]?.text || '';
}
async function askClaude(prompt) {
  if (!ANTHROPIC_KEY) throw new Error('ANTHROPIC_API_KEY missing (add it to .env to use Claude)');
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': ANTHROPIC_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 1400,
      messages: [{ role: 'user', content: prompt }],
    }),
  });
  if (!r.ok) throw new Error('Anthropic ' + r.status + ' ' + (await r.text()).slice(0, 200));
  const j = await r.json();
  return j.content?.[0]?.text || '';
}
function askModel(engine, prompt, json) {
  if (engine === 'ChatGPT') return askOpenAI(prompt, json);
  if (engine === 'Claude') return askClaude(prompt);
  return askGemini(prompt); // default Gemini
}

// ---------- prompts ----------
function langLine(lang) {
  return lang === 'ml' ? 'Write EVERYTHING in Malayalam.' : 'Write in clear, simple English.';
}
function slidePrompt(topic, n, lang, instructions) {
  const extra = instructions && instructions.trim()
    ? `\nFollow the student's own instructions for how the slides should be: "${instructions.trim()}".`
    : '';
  return `You are helping a Calicut University BBA student make a study presentation on "${topic}" for the subject Domestic Logistics Management.
Produce EXACTLY ${n} slides. ${langLine(lang)}${extra}
Return ONLY valid JSON, no markdown: {"slides":[{"t":"title","b":["short bullet","short bullet"]}]}
Slide 1 is a title slide; include an introduction/definition, 2-4 key-concept slides, one worked example, an "Exam focus" slide with 2/5/10-mark points, a summary, and a references slide. 3-6 short bullets per slide, max ~8 words each.`;
}
function askPrompt(question, lang) {
  return `You are Calpus, an AI study tutor for a Calicut University BBA student studying Domestic Logistics Management (BBA3CJ202). Answer accurately using syllabus-appropriate content.
Structure your answer as:
1) A short 3-4 line explanation of the topic.
2) Then "Questions & model answers" with three tiers sized to the marks:
   - 2 marks: a short definition (1-2 lines).
   - 5 marks: definition + 3-4 key points (use • bullets).
   - 10 marks (essay): Introduction, Body (developed points), an Example, and a Conclusion.
${langLine(lang)}
Return plain readable text (use • for bullets, no markdown headings).
Student question: ${question}`;
}
function webPrompt(question, lang) {
  return `You are Calpus in OPEN-INTERNET mode. Answer using your broad general knowledge — NOT limited to any syllabus. Be accurate, clear and concise. If the question needs very recent or live data you may not have, say so honestly and still give the best general answer. ${langLine(lang)}
Return plain readable text (use • for bullets, no markdown headings).
Question: ${question}`;
}
function extractJSON(text) {
  if (!text) return null;
  let t = text.trim().replace(/^```json/i, '').replace(/^```/, '').replace(/```$/, '').trim();
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a >= 0 && b > a) t = t.slice(a, b + 1);
  try { return JSON.parse(t); } catch { return null; }
}

// ---------- email OTP (real email if RESEND_API_KEY is set, else demo mode) ----------
async function sendEmailOTP(email, code) {
  const key = process.env.RESEND_API_KEY;
  if (!key) return false; // no email service configured -> client shows demo OTP
  const from = process.env.OTP_FROM || 'Calpus <onboarding@resend.dev>';
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key },
    body: JSON.stringify({
      from, to: [email], subject: 'Your Calpus verification code',
      html: `<div style="font-family:sans-serif"><h2 style="color:#0D9488">Calpus</h2><p>Your verification code is <b style="font-size:22px;letter-spacing:2px">${code}</b>.</p><p style="color:#666">It expires in 10 minutes. If you did not request this, ignore this email.</p></div>`,
    }),
  });
  return r.ok;
}

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
function readBody(req) {
  return new Promise(res => { let b = ''; req.on('data', c => (b += c)); req.on('end', () => res(b)); });
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, CORS); return res.end(); }
  const send = (code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json', ...CORS }); res.end(JSON.stringify(obj)); };

  if (req.method === 'POST' && req.url === '/api/slides') {
    try {
      const { engine = 'Gemini', topic = 'Topic', slides = 6, lang = 'en', instructions = '' } = JSON.parse((await readBody(req)) || '{}');
      const n = Math.max(3, Math.min(15, parseInt(slides) || 6));
      const out = extractJSON(await askModel(engine, slidePrompt(topic, n, lang, instructions), true));
      if (!out || !Array.isArray(out.slides)) throw new Error('model returned no slides');
      send(200, { slides: out.slides.slice(0, 15) });
    } catch (e) { send(500, { error: String(e.message || e) }); }
    return;
  }
  if (req.method === 'POST' && req.url === '/api/ask') {
    try {
      const { engine = 'Gemini', question = '', lang = 'en', web = false } = JSON.parse((await readBody(req)) || '{}');
      if (!question.trim()) throw new Error('empty question');
      const text = (await askModel(engine, web ? webPrompt(question, lang) : askPrompt(question, lang), false)).trim();
      if (!text) throw new Error('model returned empty answer');
      send(200, { text, src: (web ? 'Open internet · ' : 'Calpus AI · ') + engine });
    } catch (e) { send(500, { error: String(e.message || e) }); }
    return;
  }
  // Server GENERATES the code, stores it, and emails it. The browser never learns it
  // (except in demo mode, when no email service is configured, so the flow is testable).
  if (req.method === 'POST' && req.url === '/api/request-otp') {
    try {
      const { email = '' } = JSON.parse((await readBody(req)) || '{}');
      if (!email.includes('@')) throw new Error('invalid email');
      const code = newCode();
      OTPS.set(email.toLowerCase(), { code, exp: Date.now() + OTP_TTL, attempts: 0 });
      const sent = await sendEmailOTP(email, code);
      send(200, sent ? { sent: true } : { sent: false, demo: code }); // demo returns code for testing
    } catch (e) { send(500, { error: String(e.message || e) }); }
    return;
  }
  // Server CHECKS the code. Browser sends only what the user typed.
  if (req.method === 'POST' && req.url === '/api/verify-otp') {
    try {
      const { email = '', code = '' } = JSON.parse((await readBody(req)) || '{}');
      const rec = OTPS.get(email.toLowerCase());
      if (!rec) return send(200, { ok: false, error: 'No code requested. Tap resend.' });
      if (Date.now() > rec.exp) { OTPS.delete(email.toLowerCase()); return send(200, { ok: false, error: 'Code expired. Tap resend.' }); }
      rec.attempts++;
      if (rec.attempts > 5) { OTPS.delete(email.toLowerCase()); return send(200, { ok: false, error: 'Too many attempts. Tap resend.' }); }
      if (String(code) === rec.code) { OTPS.delete(email.toLowerCase()); return send(200, { ok: true }); }
      send(200, { ok: false, error: 'Wrong code.' });
    } catch (e) { send(500, { error: String(e.message || e) }); }
    return;
  }
  res.writeHead(404, CORS); res.end('Not found');
});

server.listen(PORT, () => {
  console.log('Calpus AI server on http://localhost:' + PORT);
  console.log('  OpenAI (ChatGPT):', OPENAI_KEY ? 'loaded' : 'MISSING');
  console.log('  Gemini:', GEMINI_KEY ? 'loaded' : 'MISSING');
  console.log('  Anthropic (Claude):', ANTHROPIC_KEY ? 'loaded' : 'MISSING (optional)');
  console.log('  Email OTP (Resend):', process.env.RESEND_API_KEY ? 'loaded' : 'not set (OTP shows in demo mode)');
});
