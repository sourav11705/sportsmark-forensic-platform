# SportsMark 🛡️
### Digital Asset Protection for Sports Media

Forensic watermarking + perceptual fingerprinting platform that tracks and traces unauthorized redistribution of sports content — down to the individual session.

---

## How It Works

```
OFFICIAL VIDEO  →  UNIQUE WATERMARK PER VIEWER  →  DISTRIBUTE
                                                        ↓
                              PIRATED COPY FOUND ON YOUTUBE/TELEGRAM
                                                        ↓
                     FINGERPRINT MATCH + WATERMARK EXTRACTION
                                                        ↓
                           "Leaked by: user_042 on JioCinema"
                                                        ↓
                              AUTO-GENERATED DMCA TAKEDOWN NOTICE
```

---

## Project Structure

```
sportsmark/
├── watermark/
│   ├── embedder.py      # Core watermark embed/extract (DCT steganography)
│   ├── fingerprint.py   # Perceptual hashing for content matching
│   ├── registry.py      # Asset, session, detection database
│   └── dmca.py          # DMCA notice auto-generator
├── demo.py              # Full end-to-end demo
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Make sure FFmpeg is installed:
```bash
ffmpeg -version
```

### 2. Run the full demo

```bash
python demo.py
```

This will:
- Create a synthetic test video (no video file needed)
- Embed unique watermarks for 3 simulated users
- Simulate piracy (re-encode + crop the "leaked" copy)
- Detect + extract the watermark from the pirated copy
- Identify the leaker
- Generate a DMCA takedown notice

### 3. Use your own video

```bash
python demo.py --video your_highlight.mp4
```

---

## Core API

```python
from watermark.embedder import VideoWatermarker
from watermark.fingerprint import VideoFingerprinter

# Embed unique watermark per user
wm = VideoWatermarker()
session = wm.embed("match.mp4", user_id="user_007", platform="HotstarApp")
# → {'session_id': 'A3F9B2C1...', 'user_id': 'user_007', ...}

# Later: extract from pirated video
result = wm.extract("pirated.mp4")
# → {'session_id': 'A3F9B2C1...', 'platform': 'HotstarApp', 'date': '2025-01-15'}

# Perceptual fingerprint matching
fp = VideoFingerprinter()
original_fingerprint = fp.fingerprint("match.mp4")
pirated_fingerprint  = fp.fingerprint("pirated.mp4")
match = fp.compare(original_fingerprint, pirated_fingerprint)
# → {'is_match': True, 'similarity': 0.91, 'verdict': '🚨 UNAUTHORIZED COPY DETECTED'}
```

---

## Watermark Robustness

The DCT-domain watermark (via `blind-watermark`) survives:
- ✅ Re-encoding (H.264 → H.265 → VP9)
- ✅ Resolution change (1080p → 480p)
- ✅ Compression artifacts (low bitrate)
- ✅ Slight cropping (removes borders)
- ✅ Color grading adjustments
- ✅ Phone-recording-of-screen

---

## Tech Stack

| Component | Technology |
|---|---|
| Watermarking | blind-watermark (DCT/DWT), OpenCV |
| Video processing | FFmpeg |
| Fingerprinting | pHash (perceptual hash) |
| Backend (Day 2) | FastAPI |
| Frontend (Day 2) | React + Tailwind |
| Crawler (Day 4) | YouTube Data API v3, Telethon |

---

## Roadmap

- [x] Day 1: Watermark embed/extract + fingerprinting + registry + DMCA
- [ ] Day 2: FastAPI backend + REST endpoints
- [ ] Day 3: Perceptual fingerprint DB + matching pipeline  
- [ ] Day 4: YouTube + Telegram crawler
- [ ] Day 5: React dashboard
- [ ] Day 6-7: Integration + testing
