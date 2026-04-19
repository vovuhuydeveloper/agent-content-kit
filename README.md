# 🚀 Agent Content Kit

**Open-source AI video content pipeline.** Automatically generate and publish short-form videos from any URL or document — powered by multi-agent AI.

[![CI](https://github.com/vovuhuydeveloper/agent-content-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/vovuhuydeveloper/agent-content-kit/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## ✨ What It Does

Give it a URL or document → it creates short videos → sends to Telegram for approval → publishes them automatically.

```
URL / Document
     ↓
🤖 10-Agent Pipeline
     ↓
Fetch → Analyze → Script → A/B Test → Voice → Video → Thumbnail → Review
     ↓
📱 Telegram Preview (video + approve/reject buttons)
     ↓
✅ Approve → Auto Upload to YouTube · TikTok · Facebook
```

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-Agent Pipeline** | 10 specialized AI agents work together end-to-end |
| 🧠 **Multi-LLM Support** | OpenAI, Claude, or Gemini — switch anytime |
| 📄 **Document Upload** | PDF, DOCX, TXT as content source |
| 📱 **Auto-Publish** | YouTube, TikTok, Facebook via browser automation |
| 💬 **Telegram Approval** | Preview video in Telegram → approve → auto upload |
| 📅 **Content Calendar** | Schedule automated content creation |
| 📊 **Analytics Dashboard** | Track views, likes, engagement across platforms |
| 🧪 **A/B Testing** | Auto-generate script variants |
| 🎨 **Modern Dashboard** | Clean, professional UI with real-time status |

---

## 🏃 Quick Start (5 minutes)

### Prerequisites

- **Python 3.9+**
- **Node.js 18+** (for dashboard)
- **FFmpeg** — required for video composition
- **yt-dlp** — required for content fetching
- **Google Chrome** — required for auto-publishing

#### Install System Dependencies

**macOS (Homebrew):**
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

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure
cp .env.example .env
# Edit .env — minimum: OPENAI_API_KEY + PEXELS_API_KEY
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

Open **http://localhost:8000** → Setup Wizard guides you through everything.

---

## 🔑 Required API Keys

| Key | Required? | Cost | How to Get |
|-----|:---------:|------|-----------| 
| **OpenAI** | ✅ Yes | Pay-per-use | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **Pexels** | ✅ Yes | **Free** | [pexels.com/api](https://www.pexels.com/api/) |
| **Telegram Bot** | Recommended | Free | [@BotFather](https://t.me/BotFather) → `/newbot` |
| **ElevenLabs** | Optional | Freemium | [elevenlabs.io](https://elevenlabs.io/) — or use free edge-tts |

> **Minimum setup:** Just `OPENAI_API_KEY` + `PEXELS_API_KEY` and you can create videos.

---

## 📱 Auto-Publishing Setup (Browser Session)

Auto-publishing uses **Playwright browser automation** with real Chrome. No API keys or developer apps needed — just login once.

### Connect Platforms

```bash
# Login to each platform (one-time, opens Chrome)
python -m backend.core.browser_session login youtube
python -m backend.core.browser_session login tiktok
python -m backend.core.browser_session login facebook
```

Each command opens Chrome → login to your account → close the browser. Session is saved permanently.

### Or via Dashboard

Go to **http://localhost:8000/connections** → click **Connect** button for each platform.

### Check Status

```bash
curl http://localhost:8000/api/v1/browser-session/status
```

### How It Works

| Platform | Upload Method | Notes |
|----------|--------------|-------|
| **YouTube** | YouTube Studio → Private video | Shorts 9:16, max 60s |
| **TikTok** | tiktok.com/upload → Post | Short video 9:16, max 10 min |
| **Facebook** | facebook.com/reels/create → Reel | Reels 9:16, max 90s |

> **No OAuth, no API keys, no developer apps.** Just login with your browser.

---

## 💬 Telegram Bot Setup

The Telegram bot sends video previews and lets you approve/reject directly from chat.

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → name your bot → get the token
3. Paste in `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456789:AABBccDDeeFFggHH
   ```
4. Open your bot → send `/start`
5. Go to **Setup Wizard → Telegram step** → click **"Detect my Chat ID"**
6. ✅ Done!

### Approval Flow

```
Pipeline completes
     ↓
📱 Telegram sends: message + video file + thumbnail
     ↓
[✅ Duyệt & Upload]  [❌ Từ chối]
     ↓
✅ → Auto upload to YouTube, TikTok, Facebook
❌ → Job marked as rejected
```

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
│   │   └── uploaders/           # Platform-specific uploaders
│   │       ├── youtube_playwright.py   # YouTube Studio automation
│   │       ├── tiktok_playwright.py    # TikTok upload automation
│   │       └── facebook_playwright.py  # Facebook Reel automation
│   ├── api/v1/              # FastAPI REST endpoints
│   ├── core/                # Config, DB, LLM manager, browser session
│   ├── models/              # SQLAlchemy models
│   ├── tasks/               # Background task runners
│   └── telegram_bot.py      # Telegram callback handler (approve/reject)
├── dashboard/               # React + MUI + Vite frontend
│   ├── src/pages/           # Dashboard, Setup, Calendar, Analytics, Connect
│   └── src/components/      # Reusable UI components
├── data/
│   ├── jobs/                # Generated videos, scripts, thumbnails
│   └── sessions/            # Browser login sessions (git-ignored)
├── tests/                   # pytest test suite
├── .env.example             # Configuration template
└── requirements.txt         # Python dependencies
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

Interactive API docs: **http://localhost:8000/docs**

---

## 🐳 Docker (Optional)

```bash
# Full stack
docker compose up -d

# Just the API (without Redis/Celery)
docker compose up api -d
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📝 License

MIT License — free for personal and commercial use.

---

## 📬 Contact & Support

<table>
  <tr>
    <td align="center">
      <img src="docs/images/telegram-qr.png" width="200" /><br />
      <b>💬 Telegram</b><br />
      Chat with me for support
    </td>
    <td align="center">
      <img src="docs/images/momo-qr.png" width="200" /><br />
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

Made with ❤️ by [vovuhuydeveloper](https://github.com/vovuhuydeveloper)
