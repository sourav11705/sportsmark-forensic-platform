"""
watermark/embedder.py
VideoWatermarker — forensic blind watermarking using DCT steganography (blind_watermark).
FFmpeg is used for frame extraction and video reassembly.
"""

import os
import re
import uuid
import json
import shutil
import tempfile
import subprocess
from collections import Counter
from datetime import datetime, timezone


# ─────────────────────────────────────────────
# Standalone helpers (no class dependency)
# ─────────────────────────────────────────────

def get_video_info(path: str) -> dict:
    """Return fps, width, height, duration via ffprobe JSON."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError(f"No video stream found in {path}")

    # fps can be expressed as "30000/1001" or "30"
    fps_raw = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_raw:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_raw)

    duration = float(data.get("format", {}).get("duration", 0))
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    return {"fps": fps, "width": width, "height": height, "duration": duration}


def extract_frames(video: str, output_dir: str, every_n: int = 1) -> None:
    """Extract every N-th frame as PNG into output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    vf_filter = f"select='not(mod(n\\,{every_n}))',setpts=N/FRAME_RATE/TB"
    cmd = [
        "ffmpeg", "-y", "-i", video,
        "-vf", vf_filter,
        "-vsync", "vfr",
        "-q:v", "1",
        os.path.join(output_dir, "frame_%06d.png"),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def reassemble_video(
    frames_dir: str,
    original_video: str,
    output_path: str,
    fps: float,
) -> None:
    """Reassemble PNG frames into a video, copying original audio."""
    frame_pattern = os.path.join(frames_dir, "frame_%06d.png")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", frame_pattern,
        "-i", original_video,
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-c:a", "copy",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)


# ─────────────────────────────────────────────
# Blind DCT helpers
# ─────────────────────────────────────────────

def embed_watermark_blind(
    frame_path: str,
    output_path: str,
    session_tag: str,
    password_wm: int = 42,
    password_img: int = 84,
) -> None:
    """Embed session_tag invisibly into a PNG frame using blind_watermark DCT."""
    from blind_watermark import WaterMark

    bwm = WaterMark(password_wm=password_wm, password_img=password_img)
    # Increase embedding strength by 30% to survive video compression
    bwm.bwm_core.d1 = 47
    bwm.bwm_core.d2 = 26
    
    # Convert string to exactly 160 bits
    byte_arr = session_tag.encode('utf-8')
    bit_str = ''.join(f'{b:08b}' for b in byte_arr)
    bit_list = [int(b) for b in bit_str]
    
    bwm.read_img(frame_path)
    bwm.read_wm(bit_list, mode="bit")
    bwm.embed(output_path)


def extract_watermark_blind(
    frame_path: str,
    wm_length: int,
    password_wm: int = 42,
    password_img: int = 84,
) -> str:
    """Extract watermark bits from a PNG frame."""
    from blind_watermark import WaterMark

    bwm = WaterMark(password_wm=password_wm, password_img=password_img)
    bwm.bwm_core.d1 = 47
    bwm.bwm_core.d2 = 26
    
    # We use mode="bit" to get the raw float array, then threshold to bits manually
    wm_floats = bwm.extract(frame_path, wm_shape=wm_length, mode="bit")
    byte_str = ''.join(str((i >= 0.5) * 1) for i in wm_floats)
    return byte_str


# ─────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────

class VideoWatermarker:
    """Forensic blind video watermarker with session tagging."""

    EMBED_INTERVAL = 30   # embed into every 30th frame (0-indexed)

    # ── Session ID ──────────────────────────────

    @staticmethod
    def generate_session_id(user_id: str, platform: str) -> dict:
        """
        Returns a session dict with a deterministic 20-char full_tag so that
        wm_length is always exactly 160 bits.

        full_tag format: "<16-HEX-UUID>|<3-CHAR-PLATFORM>"  →  20 chars
        """
        session_id = uuid.uuid4().hex[:16].upper()          # 16 chars
        platform_code = platform.upper()[:3].ljust(3, "X")  # always 3 chars
        full_tag = f"{session_id}|{platform_code}"          # always 20 chars

        assert len(full_tag) == 20, f"full_tag length is {len(full_tag)}, expected 20"

        return {
            "session_id": session_id,
            "user_id": user_id,
            "platform": platform,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform_code": platform_code,
            "full_tag": full_tag,
            "wm_length": len(full_tag) * 8,   # 160
        }

    # ── FFmpeg wrappers (instance methods delegating to module-level fns) ────

    def get_video_info(self, path: str) -> dict:
        return get_video_info(path)

    def extract_frames(self, video: str, output_dir: str, every_n: int = 1) -> None:
        extract_frames(video, output_dir, every_n)

    def reassemble_video(
        self,
        frames_dir: str,
        original_video: str,
        output_path: str,
        fps: float,
    ) -> None:
        reassemble_video(frames_dir, original_video, output_path, fps)

    # ── Watermark helpers (instance methods) ─────────────────────────────────

    def embed_watermark_blind(
        self,
        frame_path: str,
        output_path: str,
        session_tag: str,
        password_wm: int = 42,
        password_img: int = 84,
    ) -> None:
        embed_watermark_blind(frame_path, output_path, session_tag, password_wm, password_img)

    def extract_watermark_blind(
        self,
        frame_path: str,
        wm_length: int,
        password_wm: int = 42,
        password_img: int = 84,
    ) -> str:
        return extract_watermark_blind(frame_path, wm_length, password_wm, password_img)

    # ── Core pipeline ─────────────────────────────────────────────────────────

    def embed(
        self,
        video_path: str,
        user_id: str,
        platform: str,
        output_path: str,
        session_dict: dict = None,
    ) -> dict:
        """
        Full pipeline:
          1. Generate session metadata
          2. Extract all frames with FFmpeg
          3. Embed watermark into every EMBED_INTERVAL-th frame
          4. Reassemble with FFmpeg
          5. Return session dict + frame dimensions
        """
        session = session_dict if session_dict is not None else self.generate_session_id(user_id, platform)
        full_tag = session["full_tag"]
        info = self.get_video_info(video_path)
        fps = info["fps"]

        work_dir = tempfile.mkdtemp(prefix="sportsmark_embed_")
        raw_dir = os.path.join(work_dir, "raw")
        wm_dir = os.path.join(work_dir, "wm")
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(wm_dir, exist_ok=True)

        try:
            # Extract every frame (every_n=1 → all frames)
            print(f"  [embed] Extracting frames from {os.path.basename(video_path)} ...")
            self.extract_frames(video_path, raw_dir, every_n=1)

            frames = sorted(
                f for f in os.listdir(raw_dir) if f.endswith(".png")
            )
            print(f"  [embed] {len(frames)} frames extracted. Watermarking every {self.EMBED_INTERVAL}th ...")

            for idx, fname in enumerate(frames):
                src = os.path.join(raw_dir, fname)
                dst = os.path.join(wm_dir, fname)

                if idx % self.EMBED_INTERVAL == 0:
                    try:
                        self.embed_watermark_blind(src, dst, full_tag)
                    except Exception as e:
                        print(f"  [embed] Warning: failed to watermark frame {fname}: {e}")
                        shutil.copy2(src, dst)
                else:
                    shutil.copy2(src, dst)

            print(f"  [embed] Reassembling video -> {os.path.basename(output_path)} ...")
            self.reassemble_video(wm_dir, video_path, output_path, fps)

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        session["frame_width"] = info["width"]
        session["frame_height"] = info["height"]
        return session

    def extract(self, video_path: str, wm_length: int = 160) -> dict:
        """
        Extract & vote on watermark tags from sampled frames.
        Returns {session_id, platform_code, confidence, raw_tag}.
        """
        work_dir = tempfile.mkdtemp(prefix="sportsmark_extract_")
        all_dir = os.path.join(work_dir, "all_frames")
        os.makedirs(all_dir, exist_ok=True)

        try:
            # Extract every frame so we can pick the watermarked positions exactly
            self.extract_frames(video_path, all_dir, every_n=1)
            all_frames = sorted(
                f for f in os.listdir(all_dir) if f.endswith(".png")
            )

            # Pick every EMBED_INTERVAL-th frame (these were watermarked during embed)
            watermarked = [all_frames[i] for i in range(0, len(all_frames), self.EMBED_INTERVAL)]
            # Cap at 8 frames for speed
            watermarked = watermarked[:8]

            from watermark.registry import list_sessions
            all_sessions = list_sessions()
            expected_bits_map = {}
            for s in all_sessions:
                tag = s.get("full_tag")
                if tag:
                    byte_arr = tag.encode('utf-8')
                    bit_str = ''.join(f'{b:08b}' for b in byte_arr)
                    expected_bits_map[tag] = bit_str

            candidates = []
            for fname in watermarked:
                fpath = os.path.join(all_dir, fname)
                try:
                    extracted_bits = extract_watermark_blind(fpath, wm_length)
                    
                    best_match_tag = None
                    best_match_pct = 0.0
                    
                    for tag, expected_bits in expected_bits_map.items():
                        if len(extracted_bits) == len(expected_bits):
                            match_count = sum(1 for a, b in zip(extracted_bits, expected_bits) if a == b)
                            pct = match_count / len(expected_bits)
                            if pct > best_match_pct:
                                best_match_pct = pct
                                best_match_tag = tag
                                
                    # Require at least 80% bit match
                    if best_match_pct >= 0.80 and best_match_tag:
                        candidates.append(best_match_tag)
                except Exception as e:
                    print(f"  [extract] Warning on frame {fname}: {e}")

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        if not candidates:
            return {
                "session_id": None,
                "platform_code": None,
                "confidence": 0.0,
                "raw_tag": None,
            }

        vote = Counter(candidates)
        best_tag, best_count = vote.most_common(1)[0]
        confidence = best_count / len(candidates)

        parsed = self._parse_session_tag(best_tag)
        parsed["confidence"] = round(confidence, 3)
        parsed["raw_tag"] = best_tag
        return parsed

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_tag(tag: str) -> bool:
        """Tag must be printable ASCII, len >= 16, and contain '|'."""
        if not isinstance(tag, str):
            return False
        tag = tag.strip()
        if len(tag) < 16:
            return False
        if "|" not in tag:
            return False
        if not all(32 <= ord(c) <= 126 for c in tag):
            return False
        return True

    @staticmethod
    def _parse_session_tag(tag: str) -> dict:
        """Split 'SESSION_ID|PLATFORM' → {session_id, platform_code}."""
        parts = tag.strip().split("|", 1)
        return {
            "session_id": parts[0] if parts else None,
            "platform_code": parts[1] if len(parts) > 1 else None,
        }
