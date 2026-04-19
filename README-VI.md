# 🚀 Agent Content Kit — AI Video Creation Pipeline

Open-source, fully automated multi-agent content pipeline:
**Web content → AI Script → Voiceover → Video → Telegram Approval → Social Media Upload**

[![Python](https://img.shields.io/badge/Python-3.11+-green?style=flat&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-blue?style=flat&logo=react)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![MUI](https://img.shields.io/badge/Material_UI-v6-blue?style=flat&logo=mui)](https://mui.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/vovuhuydeveloper/agent-content-kit?style=social)](https://github.com/vovuhuydeveloper/agent-content-kit)

**Ngôn ngữ**: [English](README.md) | [Tiếng Việt](README-VI.md)

---

## 🎯 What is this?

Agent Content Kit tự động biến nội dung web thành video ngắn chuyên nghiệp:

1. 🔗 **Fetch** — Crawl nội dung từ URL bất kỳ (web, YouTube, TikTok, docs)
2. ✍️ **Script** — AI (GPT-4o) viết kịch bản video ngắn
3. 🗣 **Voice** — Text-to-speech tiếng Việt/English (edge-tts, miễn phí)
4. 🎬 **Video** — Render video 9:16 với stock footage (Pexels) + character overlay
5. ⭐ **Review** — AI chấm điểm chất lượng (auto-approve nếu ≥ 7/10)
6. 📱 **Telegram** — Gửi notification + nút ✅/❌ để duyệt
7. 🚀 **Publish** — Upload lên TikTok, YouTube, Facebook (coming soon)

---

## ⚡ Quick Start (5 phút)

### Yêu cầu hệ thống

| Tool | Version | Kiểm tra |
|------|---------|----------|
| Docker | 20+ | `docker --version` |
| Docker Compose | v2+ | `docker compose version` |
| Node.js | 18+ | `node --version` (chỉ cần khi build dashboard) |
| npm | 9+ | `npm --version` |

### Bước 1: Clone repo

```bash
git clone https://github.com/vovuhuydeveloper/agent-content-kit.git
cd agent-content-kit
```

### Bước 2: Tạo file `.env`

```bash
cp .env.example .env
```

Mở file `.env` và điền API keys (xem [Hướng dẫn lấy API Keys](#-hướng-dẫn-lấy-api-keys) bên dưới):

```env
# BẮT BUỘC — GPT-4o dùng để viết script
OPENAI_API_KEY=sk-proj-your-key-here

# KHUYẾN NGHỊ — Lấy stock footage miễn phí
PEXELS_API_KEY=your-pexels-key

# KHUYẾN NGHỊ — Bot Telegram để duyệt video
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### Bước 3: Build dashboard (chạy 1 lần)

```bash
cd dashboard
npm install
npm run build
cd ..
```

### Bước 4: Khởi chạy

```bash
docker compose -f docker-compose.agents.yml up -d
```

### Bước 5: Mở dashboard

| URL | Mô tả |
|-----|-------|
| `http://localhost:8000/setup` | 🧙 Setup Wizard — tạo video |
| `http://localhost:8000/dashboard` | 📊 Dashboard — quản lý jobs |
| `http://localhost:8000/docs` | 📖 Swagger API docs |

> **Trên server**: Thay `localhost` bằng IP server, ví dụ `http://192.168.1.100:8000/setup`

---

## 🔑 Hướng dẫn lấy API Keys

### 1. OpenAI API Key (BẮT BUỘC)

Dùng cho: Viết kịch bản, phân tích nội dung, chấm điểm chất lượng

1. Vào [platform.openai.com](https://platform.openai.com) → đăng ký / đăng nhập
2. Click **"API Keys"** ở sidebar trái
3. Click **"+ Create new secret key"**
4. Đặt tên (ví dụ: `agent-content-kit`) → click **Create**
5. **Copy key** (bắt đầu bằng `sk-proj-...`) → dán vào `.env`

> ⚠️ Key chỉ hiện 1 lần. Nếu mất, tạo key mới.
> 💰 Chi phí ~$0.01–0.05 / video (GPT-4o-mini)

### 2. Pexels API Key (KHUYẾN NGHỊ, miễn phí)

Dùng cho: Lấy stock video footage làm nền video

1. Vào [pexels.com/api](https://www.pexels.com/api/) → đăng ký tài khoản (miễn phí)
2. Điền form **"I want to use Pexels API"**
3. Vào [pexels.com/api/new](https://www.pexels.com/api/new/) → tạo API key mới
4. **Copy key** → dán vào `.env`

> ✅ Hoàn toàn miễn phí, 200 requests/giờ

### 3. Telegram Bot (KHUYẾN NGHỊ)

Dùng cho: Nhận thông báo khi video hoàn thành + duyệt upload

**Tạo Bot Token:**
1. Mở Telegram → tìm [@BotFather](https://t.me/BotFather)
2. Gửi lệnh `/newbot`
3. Đặt tên cho bot (ví dụ: `My Content Bot`)
4. Đặt username (ví dụ: `my_content_bot`)
5. **Copy token** (dạng `123456789:AAHdq...`) → dán vào `TELEGRAM_BOT_TOKEN` trong `.env`

**Lấy Chat ID:**
1. Mở Telegram → tìm [@userinfobot](https://t.me/userinfobot)
2. Gửi bất kỳ tin nhắn nào
3. Bot trả về **Chat ID** (dạng số, ví dụ `1975438398`)
4. Copy → dán vào `TELEGRAM_CHAT_ID` trong `.env`

**Kích hoạt bot:**
1. Tìm bot của bạn trên Telegram (bằng username đã đặt)
2. Nhấn **Start** hoặc gửi `/start`

> 💡 Không có Telegram bot? Hệ thống vẫn chạy bình thường — bạn duyệt video qua Dashboard thay vì Telegram.

### 4. ElevenLabs (TÙY CHỌN)

Dùng cho: Text-to-speech giọng nói cao cấp

1. Vào [elevenlabs.io](https://elevenlabs.io) → đăng ký (free tier: 10,000 chars/tháng)
2. Vào **Settings → API Keys** → tạo key mới
3. Copy → dán vào `.env`

> ℹ️ Không bắt buộc — hệ thống mặc định dùng `edge-tts` (miễn phí, không giới hạn)

---

## 📖 Cách sử dụng

### Tạo video qua Dashboard (dễ nhất)

1. **Mở** `http://localhost:8000/setup`
2. **Step 1** — Nhập URL nguồn nội dung (blog, YouTube, etc.)
3. **Step 2** — Thêm link đối thủ (optional — để trống sẽ theo trend)
4. **Step 3** — Upload ảnh character (optional — có mặc định)
5. **Step 4** — Nhập API keys (nếu chưa config trong `.env`)
6. **Step 5** — Chọn platforms muốn upload (TikTok, YouTube, Facebook)
7. **Step 6** — Config Telegram bot (optional)
8. **Bấm "🚀 Bắt đầu tạo video"**

### Theo dõi tiến trình

- **Dashboard** (`/dashboard`) — Xem tất cả jobs, status realtime
- **Telegram** — Nhận noti khi video xong, bấm ✅ duyệt hoặc ❌ từ chối
- **Job detail** (`/jobs/{id}`) — Xem chi tiết pipeline, approve/reject

### Tạo video qua API (cho developer)

```bash
# Submit job
curl -X POST http://localhost:8000/api/v1/content-jobs/ \
  -F "source_url=https://your-website.com" \
  -F "language=vi" \
  -F "video_count=1" \
  -F "platforms=tiktok" \
  -F "niche=education"

# Response
# {"job_id": "abc-123", "status": "pending", "monitor_url": "/api/v1/content-jobs/abc-123"}

# Check status
curl http://localhost:8000/api/v1/content-jobs/abc-123

# Approve (sau khi video render xong)
curl -X POST http://localhost:8000/api/v1/content-jobs/abc-123/approve
```

### Flow sau khi submit

```
Submit → [~3 phút] → Video rendered → Telegram notification
                                          ├─ ✅ Approve → Upload to platforms
                                          └─ ❌ Reject → Job archived
```

> ⏱ Thời gian render: ~2-4 phút / video (tùy độ dài script + tốc độ mạng)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Dashboard (React + MUI v6)           http://localhost:8000  │
├─────────────────────────────────────────────────────────────┤
│ FastAPI                              API + Static serving   │
├─────────────────────────────────────────────────────────────┤
│ Celery Worker                        Agent pipeline         │
│  ├─ ContentFetcherAgent              Web scraping           │
│  ├─ CompetitorAnalyzerAgent          Trend analysis         │
│  ├─ ScriptWriterAgent                GPT-4o scriptwriting   │
│  ├─ VoiceGeneratorAgent              edge-tts               │
│  ├─ VideoComposerAgent               FFmpeg + PIL + Pexels  │
│  ├─ ThumbnailAgent                   PIL rendering          │
│  ├─ QualityReviewAgent               AI scoring             │
│  ├─ TelegramNotifier                 Approval flow          │
│  └─ PublisherAgent                   Social media upload    │
├─────────────────────────────────────────────────────────────┤
│ Redis                                Task queue             │
│ SQLite                               Job storage            │
└─────────────────────────────────────────────────────────────┘
```

### Agent Pipeline Flow

```
Submit Job → Fetch → Script → Voice → Video → Thumbnail → QA Review
                                                              │
                                      ┌───────────────────────┘
                                      ▼
                               Telegram Noti (✅/❌)
                                      │
                            ┌─────────┴─────────┐
                            ▼                   ▼
                     ✅ Approve              ❌ Reject
                         │                      │
                    PublisherAgent          Job archived
                    (TikTok/YT/FB)
```

---

## 📁 Project Structure

```
agent-content-kit/
├── backend/
│   ├── agents/                    # AI Agent pipeline
│   │   ├── base.py                # BaseAgent (retry, config)
│   │   ├── schemas.py             # Pydantic models
│   │   ├── pipeline.py            # Pipeline orchestrator
│   │   ├── llm_client.py          # LLM abstraction (swap OpenAI/Claude)
│   │   ├── fetcher.py             # Web content scraping
│   │   ├── scriptwriter.py        # GPT script generation
│   │   ├── voice.py               # TTS (edge-tts / ElevenLabs)
│   │   ├── composer/              # Video rendering engine
│   │   │   ├── stock_service.py   # Pexels stock footage
│   │   │   ├── renderer.py        # PIL text/caption rendering
│   │   │   └── ffmpeg.py          # FFmpeg video processing
│   │   ├── thumbnail.py           # Thumbnail generation
│   │   ├── reviewer.py            # AI quality review
│   │   ├── notifier.py            # Telegram notifications
│   │   └── publisher.py           # Social media upload
│   ├── api/v1/                    # REST API endpoints
│   ├── core/                      # Config, database, Celery
│   ├── models/                    # Database models
│   ├── tasks/                     # Celery async tasks
│   └── telegram_bot.py            # Telegram bot handler
│
├── dashboard/                     # React + MUI v6 web app
│   ├── src/
│   │   ├── pages/                 # SetupWizard, Dashboard, JobDetail
│   │   ├── components/wizard/     # 6-step setup wizard
│   │   └── services/api.ts        # API client
│   ├── dist/                      # Production build (generated)
│   └── package.json
│
├── docker-compose.agents.yml      # 🐳 Docker deployment
├── Dockerfile.agents              # Container image
├── .env.example                   # ⚙️ Configuration template
└── requirements.txt               # Python dependencies
```

---

## 🔧 API Reference

### Content Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/content-jobs/` | Submit new video job |
| `GET` | `/api/v1/content-jobs/` | List all jobs |
| `GET` | `/api/v1/content-jobs/{id}` | Get job detail & status |
| `POST` | `/api/v1/content-jobs/{id}/approve` | Approve → start upload |
| `POST` | `/api/v1/content-jobs/{id}/reject` | Reject job |
| `DELETE` | `/api/v1/content-jobs/{id}` | Delete job & files |

### Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/config/keys` | Get saved keys (masked) |
| `POST` | `/api/v1/config/keys` | Save/update API keys |
| `POST` | `/api/v1/config/keys/validate` | Test if a key works |
| `POST` | `/api/v1/config/telegram/test` | Test Telegram bot connection |

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | — | GPT-4o for script generation |
| `PEXELS_API_KEY` | 📋 Recommended | — | Stock footage (free, 200 req/hr) |
| `TELEGRAM_BOT_TOKEN` | 📋 Recommended | — | Approval notifications via Telegram |
| `TELEGRAM_CHAT_ID` | 📋 Recommended | — | Your Telegram user chat ID |
| `ELEVENLABS_API_KEY` | ❌ Optional | — | Premium TTS voices |
| `DATABASE_URL` | Auto | `sqlite:///./data/autoclip.db` | Database connection |
| `REDIS_URL` | Auto | `redis://redis:6379/0` | Celery task queue |

---

## 🎬 Video Output

| Spec | Value |
|------|-------|
| Format | MP4 (H.264 + AAC) |
| Resolution | 1080×1920 (9:16 vertical) |
| Composition | Stock footage + caption overlay + character overlay |
| Languages | 🇻🇳 Tiếng Việt, 🇺🇸 English |
| File size | ~15-20MB / video |
| Render time | ~2-4 minutes |

---

## ❓ FAQ

<details>
<summary><b>Q: Không có Telegram bot thì sao?</b></summary>

Hệ thống vẫn chạy bình thường! Video sẽ ở trạng thái `awaiting_approval`. Bạn duyệt qua Dashboard (`/jobs/{id}`) hoặc API (`POST /approve`).
</details>

<details>
<summary><b>Q: Không có Pexels key thì sao?</b></summary>

Video sẽ dùng background màu gradient thay vì stock footage. Khuyến nghị tạo key Pexels (miễn phí) để video đẹp hơn.
</details>

<details>
<summary><b>Q: Chi phí chạy bao nhiêu?</b></summary>

- **OpenAI**: ~$0.01-0.05 / video (GPT-4o-mini)
- **Pexels**: Miễn phí
- **edge-tts**: Miễn phí
- **Server**: VPS $5/tháng (1 vCPU, 2GB RAM) đủ chạy
</details>

<details>
<summary><b>Q: Có thể đổi từ OpenAI sang Claude không?</b></summary>

Có! Hệ thống dùng LLM abstraction layer. Thêm `AnthropicProvider` vào `backend/core/llm_providers.py` (coming soon).
</details>

<details>
<summary><b>Q: Upload lên TikTok/YouTube có tự động không?</b></summary>

Chưa. Hiện tại PublisherAgent là stub. Cần OAuth integration cho mỗi platform (planned in roadmap).
</details>

---

## 🗺 Roadmap

- [x] Multi-agent pipeline with checkpoint/resume
- [x] Pexels stock footage integration
- [x] Vietnamese text rendering (full diacritics)
- [x] Telegram approval flow (inline buttons)
- [x] Material Design 3 dashboard
- [x] API key validation & guided setup
- [ ] Real TikTok/YouTube/Facebook upload (OAuth)
- [ ] Claude/Gemini LLM support
- [ ] PDF/DOCX as content source
- [ ] A/B testing for scripts
- [ ] Analytics dashboard
- [ ] Scheduled content calendar

---

## 🤝 Contributing

1. Fork repo
2. Tạo feature branch (`git checkout -b feature/awesome`)
3. Commit (`git commit -m 'Add awesome feature'`)
4. Push (`git push origin feature/awesome`)
5. Tạo Pull Request

---

## 📄 License

MIT License — miễn phí cho cá nhân và thương mại.

---

## 📬 Liên hệ & Ủng hộ

<table>
  <tr>
    <td align="center">
      <img src="docs/images/telegram-qr.png" width="200" /><br />
      <b>💬 Telegram</b><br />
      Chat hỗ trợ
    </td>
    <td align="center">
      <img src="docs/images/momo-qr.png" width="200" /><br />
      <b>☕ Mời tui ly cà phê</b><br />
      Ủng hộ qua MoMo
    </td>
  </tr>
</table>

---

Made with ❤️ by [vovuhuydeveloper](https://github.com/vovuhuydeveloper)
