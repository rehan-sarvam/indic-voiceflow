# VoiceFlow (Sarvam Powered) – Streamlit

Record audio in the browser, transcribe with **Sarvam Saaras v3**, clean with **Groq** (free, fast), and see raw + cleaned text. Built with Streamlit (single app, no separate backend).

## API keys (both required)

**Local run:** In the **voiceflow** folder, duplicate **`env.example`** and rename the copy to **`env`** (no dot). Add:
```
SARVAM_API_KEY=your_sarvam_key_here
GROQ_API_KEY=your_groq_key_here
```
- **Sarvam**: https://www.sarvam.ai/ (transcription).
- **Groq**: https://console.groq.com/keys (free, no card; cleaning).

**Streamlit Cloud:** Use [Secrets](#deploy-on-streamlit-cloud) (see below). Do not commit `env` or any file containing keys.

## How to run

1. Open Terminal and go to the voiceflow folder:
   ```bash
   cd ~/Downloads/voiceflow
   ```
2. Install dependencies (first time only):
   ```bash
   pip install -r requirements.txt
   ```
   Or with venv: `source ~/Downloads/venv/bin/activate` then `pip install -r requirements.txt`.

3. Start the app:
   ```bash
   streamlit run app.py
   ```

4. Your browser will open (or go to the URL shown, usually **http://localhost:8501**). Use the mic to record, choose Native or Roman script and cleaning style, then view raw and cleaned transcripts.

## Deploy on Streamlit Cloud

1. Push this repo to **GitHub** (do not commit `env` or any file with real keys; they are in `.gitignore`).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and click **New app**. Select your repo and set **Main file path** to `app.py`.
3. Before or after deploying, open your app → **Settings** (⚙️) → **Secrets**.
4. Add your keys in **TOML** format, for example:
   ```toml
   SARVAM_API_KEY = "your_sarvam_key_here"
   GROQ_API_KEY = "your_groq_key_here"
   ```
   Optional (e.g. to change cleaning model):
   ```toml
   GROQ_MODEL = "llama-3.1-8b-instant"
   ```
5. Save. Streamlit Cloud will redeploy if needed; the app will read these secrets automatically.

The app reads from **environment variables** (set by Streamlit Cloud from your Secrets) and from **st.secrets**, so the same code works locally (using `env`) and on Streamlit Cloud (using the dashboard Secrets).

## Project layout

```
voiceflow/
├── app.py           # Streamlit app
├── requirements.txt
├── env.example      # copy to "env" for local; use Streamlit Secrets for cloud
├── .gitignore       # ignores env, .env, .streamlit/secrets.toml
└── README.md
```

## Optional: change Groq cleaning model

Default is **llama-3.3-70b-versatile** (best quality for Indic/roman cleaning, Hindi support). Set `GROQ_MODEL` in `env` to override:

| Model | Best for |
|-------|----------|
| `llama-3.3-70b-versatile` | Default; best quality, Hindi/Indic |
| `llama-3.1-8b-instant` | Faster, lighter |
| `qwen/qwen3-32b` | Qwen 3 32B; 100+ languages |

## Usage

- **Script**: Native script (transcribe) or Roman script (translit).
- **Cleaning style**: Professional, Casual, Bullet points, Email format.
- **Record** with the audio input; after recording, the app transcribes and cleans automatically.
