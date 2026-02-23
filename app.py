"""
VoiceFlow (Sarvam Powered) - Streamlit app.
Record audio → Sarvam Saaras v3 STT → Groq cleaning → raw + cleaned transcript.
"""

import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

# Load API keys: .env (local) or Streamlit Cloud secrets (injected as env vars / st.secrets)
_app_dir = Path(__file__).resolve().parent
for env_file in (_app_dir / ".env", _app_dir / "env"):
    if env_file.exists():
        try:
            load_dotenv(env_file)
        except Exception:
            pass


def _secret(key: str) -> str | None:
    """Get secret from env (local or Streamlit Cloud) or st.secrets."""
    val = os.getenv(key)
    if val:
        return val
    try:
        return st.secrets.get(key)
    except Exception:
        return None


SARVAM_API_KEY = _secret("SARVAM_API_KEY")
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

GROQ_API_KEY = _secret("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL") or _secret("GROQ_MODEL") or "llama-3.3-70b-versatile"

# Comprehensive speech-to-text refinement prompt (same language & script, no translation)
# Style addons only when user explicitly chooses bullet/email
CLEANING_SYSTEM_PROMPT = """You are an expert speech-to-text refinement engine.

CRITICAL: Do NOT translate. Keep the exact same language and the exact same script (native or roman) as the input. Output in the same script the transcript is in.

Your task is to convert raw voice transcripts into clean written text while preserving the speaker's original meaning, tone, writing style, and language mix.

Core Principles:
1. Preserve intent exactly.
2. Preserve personality and tone.
3. Preserve all action verbs and intent-carrying words.
4. Do not add new information.
5. Do not summarize.
6. Only remove speech artifacts and resolve corrections.
7. Do not over-polish into corporate or formal language.
8. Keep the emotional texture (casual, excited, unsure, direct, etc.).
9. Replace only the corrected element in a sentence, not the full phrase.
10. When refinement happens, keep the most specific version of an idea.

Preserve Verbs and Action Phrases:
Do not remove essential verbs or action phrases, especially in informal or code-mixed Hindi/English speech (e.g., "milte hain", "karte hain", "chalte hain", "bhejte hain").
If a correction occurs, replace only the corrected element while keeping the rest of the sentence structure intact.
Example:
"So bhai aisa karte hain 13 ko actually 14 ko milte hain Papa George pe."
→ "So bhai, aisa karte hain, 14 ko milte hain Papa George pe."
Do not reduce "14 ko milte hain" to "14 ko Papa George pe."

Self-Corrections:
If the speaker corrects themselves, keep only the final corrected version.
Replace only the corrected element (date, time, number, word), and preserve surrounding words and verbs.
Examples:
"Let's meet on the 13th — sorry, 14th." → "Let's meet on the 14th."
"I'll send it at 5 — no, 6 PM." → "I'll send it at 6 PM."
"13 ko actually 14 ko milte hain" → Replace only "13" with "14"; keep "milte hain".
Always assume the last stated correction is correct unless explicitly negated.

Filler Words:
Remove meaningless fillers such as: um, uh, hmm, like (when filler), you know, basically, actually (if filler), kind of, sort of.
Do not remove words like "actually" if they change meaning.

False Starts:
If the speaker begins a phrase and abandons it, remove only the abandoned fragment.
Example: "Let's schedule it for next — actually let's do Friday." → "Let's schedule it for Friday."

Repetitions:
Remove accidental repeated words.
If a phrase is repeated with increasing specificity, keep only the most specific and complete version.
If two adjacent phrases express the same action or intent, and the second adds clarity or detail, remove the earlier vague version.
Examples:
"vo kharid lunga, vo suit kharid lunga" → "vo suit kharid lunga"
"I'll buy it, I'll buy the blue one" → "I'll buy the blue one"
"we should do something, we should do onboarding properly" → "we should do onboarding properly"
Do not keep both versions of the same idea unless they express different meaning.

Mid-Sentence Restarts:
If a sentence restarts midway, keep the most complete and coherent version without unnecessary restructuring.
"So what we need is — what we really need is better onboarding." → "What we really need is better onboarding."

Proper Punctuation Rules:
1. Break long run-on speech into proper sentences.
2. Add commas where natural pauses occur.
3. Use periods to separate complete thoughts.
4. Preserve informal tone.
5. Use question marks for questions.
6. Use exclamation marks only if strong emphasis is clearly intended.
7. Do not add excessive punctuation.
8. Do not restructure sentences purely to improve grammar.
9. Maintain the original flow of ideas.

Spoken Punctuation:
Convert spoken punctuation into actual punctuation.
"comma", "full stop", "new paragraph"
→ Apply proper formatting.

Numbers and Dates:
Standardize clearly spoken numbers and dates while preserving meaning.
"fourteen" → 14
"next Friday" → next Friday
Do not invent missing context or assume specific calendar dates.

Thought Switching:
If the speaker switches thoughts mid-sentence, separate into clean sentences without losing content. Do not merge or compress ideas.

Trailing Fragments:
Remove incomplete trailing fragments that clearly result from interruption.
"Yeah so that's basically what I—" → "Yeah, that's basically what I think."
Only complete a sentence if the intended ending is extremely obvious. Otherwise, keep original wording.

Code-Mixed Speech Handling:
If the transcript contains Hindi-English (Hinglish) or other code-mixed language:
- Preserve natural spoken structure.
- Do not simplify grammar into fully formal Hindi or fully formal English.
- Preserve conversational framing words unless they are clear fillers.
- Preserve mixed-language flow.
- Apply punctuation naturally within the mixed language.

Do Not:
- Summarize.
- Rephrase heavily.
- Change first-person to third-person.
- Remove verbs that carry meaning.
- Convert casual tone into formal tone.
- Add bullet points.
- Add commentary or explanations.
- Output metadata.

Output Requirements:
Return only the cleaned text.
Do not explain changes.
Do not include commentary.
Do not include metadata.
Do not wrap in quotes.

Now clean the following transcript:"""

CLEANING_STYLE_ADDONS = {
    "casual": "",
    "bullet_points": "\n\nAdditional instruction: Format the cleaned output as concise bullet points.",
    "email_format": "\n\nAdditional instruction: Make the cleaned output suitable for an email (clear, professional).",
}


def sarvam_speech_to_text(audio_bytes: bytes, filename: str, mode: str) -> str:
    """Call Sarvam Saaras v3 speech-to-text. Returns transcript text.
    Native script → codemix (code-mixed transcription); Roman script → translit."""
    headers = {"api-subscription-key": SARVAM_API_KEY}
    files = {"file": (filename, audio_bytes)}
    sarvam_mode = "codemix" if mode == "transcribe" else "translit"
    data = {"model": "saaras:v3", "mode": sarvam_mode}

    with httpx.Client(timeout=60.0) as client:
        response = client.post(SARVAM_STT_URL, headers=headers, files=files, data=data)

    if response.status_code != 200:
        err = response.text
        try:
            j = response.json()
            err = j.get("detail", j.get("message", err))
        except Exception:
            pass
        raise RuntimeError(f"Sarvam STT failed: {err}")

    result = response.json()
    transcript = (
        result.get("text")
        or result.get("transcript")
        or result.get("transcription")
        or (result.get("results") and result["results"][0].get("transcript"))
        or ""
    )
    if isinstance(transcript, list):
        transcript = " ".join(
            t.get("text", t) if isinstance(t, dict) else str(t) for t in transcript
        )
    return (transcript or "").strip()


def _call_groq(system_prompt: str, user_content: str) -> str:
    """Call Groq chat completions (OpenAI-compatible). Returns cleaned text or raises."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(GROQ_URL, headers=headers, json=payload)

    if response.status_code != 200:
        err = response.text
        try:
            j = response.json()
            e = j.get("error") or {}
            msg = e.get("message") or e.get("code") or j.get("detail") or err
        except Exception:
            msg = err
        raise RuntimeError(f"Groq failed: {msg}")

    result = response.json()
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("Groq: No response from model")
    content = (choices[0].get("message") or {}).get("content") or ""
    return (content or "").strip()


def clean_transcript(
    transcript: str,
    cleaning_style: str,
    script_mode: str,
) -> str:
    """Call Groq to clean transcript. Same refinement rules, same language & script."""
    script_instruction = (
        " Output in native script (same script as input)."
        if script_mode == "transcribe"
        else " Output in Roman/romanized script (same script as input)."
    )
    system_prompt = (
        CLEANING_SYSTEM_PROMPT
        + script_instruction
        + CLEANING_STYLE_ADDONS.get(cleaning_style, "")
    )
    return _call_groq(system_prompt, transcript) or transcript


def main():
    st.set_page_config(
        page_title="VoiceFlow (Sarvam Powered)",
        page_icon="🎙️",
        layout="centered",
    )
    st.title("VoiceFlow (Sarvam Powered)")
    st.caption("Record → Transcribe → Clean. Native or Roman script.")

    if not SARVAM_API_KEY:
        st.error(
            "**SARVAM_API_KEY not set.** Add it to your `env` file (used for transcription)."
        )
        st.stop()
    if not GROQ_API_KEY:
        st.error(
            "**GROQ_API_KEY not set.** Add it to your `env` file (used for cleaning). "
            "Free key at https://console.groq.com/keys (no card required)"
        )
        st.stop()

    mode = st.radio(
        "Script",
        options=["transcribe", "translit"],
        format_func=lambda x: "Native script" if x == "transcribe" else "Roman script",
        horizontal=True,
    )
    cleaning_style = st.selectbox(
        "Cleaning style",
        options=list(CLEANING_STYLE_ADDONS.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
    )

    st.caption(f"Cleaning: **Groq** ({GROQ_MODEL})")

    audio = st.audio_input("Record audio")

    if audio is not None:
        audio_bytes = audio.read()
        if not audio_bytes:
            st.warning("Recording is empty.")
        else:
            with st.spinner("Transcribing and cleaning…"):
                try:
                    raw = sarvam_speech_to_text(
                        audio_bytes,
                        filename=audio.name or "recording.wav",
                        mode=mode,
                    )
                    cleaned = (
                        clean_transcript(raw, cleaning_style, mode)
                        if raw
                        else ""
                    )
                    st.subheader("Raw transcript")
                    st.write(raw or "—")
                    st.subheader("Cleaned transcript")
                    st.write(cleaned or "—")
                except Exception as e:
                    st.error(str(e))


if __name__ == "__main__":
    main()
