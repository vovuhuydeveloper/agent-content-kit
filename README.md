<p align="center">
  <img src="docs/images/ph-banner.png" alt="Agent Content Kit" width="100%" />
</p>

<p align="center">
  <strong>Open-source AI pipeline that turns any URL or document into a published short-form video — fully automated.</strong>
</p>

<p align="center">
  <a href="https://github.com/vovuhuydeveloper/agent-content-kit/actions"><img src="https://github.com/vovuhuydeveloper/agent-content-kit/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Playwright-enabled-45ba4b?logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <a href="https://github.com/vovuhuydeveloper/agent-content-kit/stargazers"><img src="https://img.shields.io/github/stars/vovuhuydeveloper/agent-content-kit?style=social" alt="Stars"></a>
</p>

---

## 🧠 How It Works

<p align="center">
  <img src="docs/images/pipeline-diagram.png" alt="Agent Content Kit Pipeline" width="100%" />
</p>

> Give it **any URL or document** → 10 AI agents generate a script, record a voiceover, compose a video, and auto-publish to YouTube, TikTok and Facebook — with a Telegram approval step in between.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **10-Agent Pipeline** | Fetch → Analyze → Script → A/B Test → Voice → Video → Thumbnail → Review → Notify → Publish |
| 🧠 **Multi-LLM** | Swap between OpenAI GPT-4, Claude, or Gemini with one config change |
| 📄 **Any Source** | URL, YouTube link, PDF, DOCX, or plain text as input |
| 📱 **Telegram Approval** | Receive video preview + approve/reject buttons directly in Telegram |
| 🚀 **Auto-Publish** | Upload to YouTube, TikTok and Facebook via browser automation — no OAuth needed |
| 📅 **Content Calendar** | Schedule recurring content creation jobs |
| 📊 **Analytics Dashboard** | Track views, likes, engagement across all platforms |
| 🧪 **A/B Testing** | Auto-generate multiple script variants to pick the best one |
| 🎨 **Modern Dashboard** | React + Material UI frontend with real-time pipeline status |
| 🐳 **Docker Ready** | One-command deploy with Docker Compose |

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

- **Python 3.9+**
- **Node.js 18+** (for dashboard)
- **FFmpeg** — required for video composition
- **yt-dlp** — required for content fetching
- **Google Chrome** — required for auto-publishing

**macOS:**
```bash
brew install ffmpeg yt-dlp
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
pip install yt-dlp
```

> ⚠️ **FFmpeg is required** — without it, videos will not render. Verify with `ffmpeg -version`

### 1. Clone & Install

```bash
git clone https://github.com/vovuhuydeveloper/agent-content-kit.git
cd agent-content-kit

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env — minimum required: OPENAI_API_KEY + PEXELS_API_KEY
```

### 2. Build Dashboard

```bash
cd dashboard
npm install
npm run build
cd ..
```

### 3. Start

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** → the Setup Wizard guides you through everything.

---

## 🔑 Required API Keys

| Key | Required? | Cost | How to Get |
|-----|:---------:|------|-----------| 
| **OpenAI** | ✅ Yes | Pay-per-use | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **Pexels** | ✅ Yes | **Free** | [pexels.com/api](https://www.pexels.com/api/) |
| **Telegram Bot** | Recommended | Free | [@BotFather](https://t.me/BotFather) → `/newbot` |
| **ElevenLabs** | Optional | Freemium | [elevenlabs.io](https://elevenlabs.io/) — or use free `edge-tts` |

> **Minimum setup:** Just `OPENAI_API_KEY` + `PEXELS_API_KEY` and you can create videos right away.

---

## 📱 Auto-Publishing (No OAuth Required)

Auto-publishing uses **Playwright browser automation** with a real Chrome session. No developer apps, no API keys — just login once.

### Connect Platforms

```bash
# One-time login (opens Chrome window)
python -m backend.core.browser_session login youtube
python -m backend.core.browser_session login tiktok
python -m backend.core.browser_session login facebook
```

Or go to **http://localhost:8000/connections** → click **Connect** for each platform.

| Platform | Method | Format |
|----------|--------|--------|
| **YouTube** | YouTube Studio automation | Shorts 9:16, max 60s |
| **TikTok** | tiktok.com/upload automation | 9:16, max 10 min |
| **Facebook** | Reels creator automation | 9:16, max 90s |

---

## 💬 Telegram Approval Flow

```
Pipeline completes
     ↓
📱 Telegram sends: preview message + video file + thumbnail
     ↓
[✅ Approve & Upload]   [❌ Reject]
     ↓
✅ → Auto uploads to YouTube, TikTok, Facebook
❌ → Job marked as rejected, no upload
```

**Setup (2 minutes):**
1. Open Telegram → search **@BotFather** → send `/newbot`
2. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`
3. Open your bot → send `/start`
4. Go to **Setup Wizard → Telegram** → click **"Detect my Chat ID"**
5. ✅ Done!

---

## 📁 Project Structure

```
agent-content-kit/
├── backend/
│   ├── agents/              # 10 pipeline agents
│   │   ├── fetcher.py           # Content fetching (URL, YouTube, docs)
│   │   ├── analyzer.py          # Competitor analysis
│   │   ├── scriptwriter.py      # AI script generation
│   │   ├── ab_testing.py        # A/B variant generation
│   │   ├── voice.py             # Text-to-speech (ElevenLabs / edge-tts)
│   │   ├── composer/            # Video composition (FFmpeg + PIL)
│   │   ├── thumbnail.py         # Thumbnail generation
│   │   ├── reviewer.py          # AI quality review
│   │   ├── publisher.py         # Multi-platform publish orchestrator
│   │   ├── notifier.py          # Telegram notifications
│   │   └── uploaders/
│   │       ├── youtube_playwright.py
│   │       ├── tiktok_playwright.py
│   │       └── facebook_playwright.py
│   ├── api/v1/              # FastAPI REST endpoints
│   ├── core/                # Config, DB, LLM manager, browser session
│   ├── models/              # SQLAlchemy models
│   ├── tasks/               # Background task runners
│   └── telegram_bot.py      # Telegram callback handler
├── dashboard/               # React + MUI + Vite frontend
│   ├── src/pages/           # Dashboard, Setup, Calendar, Analytics, Connect
│   └── src/components/      # Reusable UI components
├── data/
│   ├── jobs/                # Generated videos, scripts, thumbnails
│   └── sessions/            # Browser login sessions (git-ignored)
├── tests/                   # pytest test suite
├── .env.example             # Configuration template
└── requirements.txt
```

---

## 🧪 API Reference

| Group | Endpoints |
|-------|-----------|
| **Content Jobs** | `POST /api/v1/content-jobs/` · `GET /api/v1/content-jobs/` · `GET /api/v1/content-jobs/{id}` |
| **Config** | `GET /api/v1/config/keys` · `POST /api/v1/config/keys` · `POST /api/v1/config/keys/validate` |
| **Browser Sessions** | `GET /api/v1/browser-session/status` · `POST /api/v1/browser-session/{platform}/connect` |
| **Telegram** | `POST /api/v1/config/telegram/test` · `POST /api/v1/config/telegram/detect-chat` |
| **Calendar** | `GET /api/v1/schedules/` · `POST /api/v1/schedules/` |
| **Analytics** | `GET /api/v1/analytics/overview` · `GET /api/v1/analytics/top-videos` |

Interactive docs: **http://localhost:8000/docs**

---

## 🐳 Docker

```bash
# Full stack
docker compose up -d

# API only
docker compose up api -d
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/amazing`
3. Commit your changes
4. Push: `git push origin feature/amazing`
5. Open a Pull Request

All contributions welcome — bug fixes, new uploaders, new LLM providers, UI improvements.

---

## 📬 Contact & Support

<table>
  <tr>
    <td align="center">
      <img src="docs/images/telegram-qr.png" width="180" /><br />
      <b>💬 Telegram</b><br />
      Chat with me for support
    </td>
    <td align="center">
      <img src="docs/images/momo-qr.png" width="180" /><br />
      <b>☕ Buy me a coffee</b><br />
      Support via MoMo
    </td>
  </tr>
</table>

---

## 🙏 Credits

- [OpenAI](https://openai.com) / [Anthropic](https://anthropic.com) / [Google](https://ai.google.dev) — LLM providers
- [Pexels](https://pexels.com) — Free stock videos
- [Playwright](https://playwright.dev) — Browser automation
- [FFmpeg](https://ffmpeg.org) — Video processing
- [edge-tts](https://github.com/rany2/edge-tts) — Free text-to-speech
- [Material UI](https://mui.com) — Dashboard components

---

## 📝 License

MIT License — free for personal and commercial use.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/vovuhuydeveloper">vovuhuydeveloper</a>
  <br/><br/>
  If this project saved you time, <a href="https://github.com/vovuhuydeveloper/agent-content-kit/stargazers">⭐ give it a star!</a>
</p>
