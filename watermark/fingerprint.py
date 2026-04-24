"""
watermark/fingerprint.py
VideoFingerprinter — perceptual hashing for piracy detection via content matching.
Uses OpenCV DCT-based pHash + Hamming distance similarity scoring.
"""

import hashlib
import json
import os
import subprocess
import tempfile
import shutil

import cv2
import numpy as np


# ─────────────────────────────────────────────
# Standalone pHash helpers
# ─────────────────────────────────────────────

def phash_image(image_path: str, hash_size: int = 16) -> str:
    """
    Compute perceptual hash (pHash) of an image using OpenCV DCT.

    Steps:
      1. Load as grayscale, resize to (hash_size+1) × hash_size
      2. Apply 2D DCT
      3. Take top-left hash_size×hash_size block
      4. Compare each coefficient to mean → binary string
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    # Resize: width = hash_size+1, height = hash_size
    resized = cv2.resize(img, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    resized = np.float32(resized)

    # DCT on full resized image then crop
    dct = cv2.dct(resized)
    dct_low = dct[:hash_size, :hash_size]

    mean_val = dct_low.mean()
    bits = "".join("1" if v >= mean_val else "0" for v in dct_low.flatten())
    return bits  # length = hash_size * hash_size = 256 bits


def hamming_distance(hash1: str, hash2: str) -> int:
    """Count differing bits between two binary hash strings."""
    if len(hash1) != len(hash2):
        raise ValueError(
            f"Hash length mismatch: {len(hash1)} vs {len(hash2)}"
        )
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def similarity_score(hash1: str, hash2: str) -> float:
    """Return similarity in [0, 1] where 1 = identical."""
    dist = hamming_distance(hash1, hash2)
    return 1.0 - dist / len(hash1)


# ─────────────────────────────────────────────
# Main class
# ─────────────────────────────────────────────

class VideoFingerprinter:
    """Content fingerprinter for video piracy detection."""

    SAMPLE_FRAMES = 20
    MATCH_THRESHOLD = 0.72

    # ── Fingerprinting ────────────────────────────────────────────────────────

    def fingerprint(self, video_path: str) -> dict:
        """
        Sample SAMPLE_FRAMES frames evenly, compute pHash for each.

        Returns:
            frame_hashes  — list of pHash strings
            master_hash   — SHA-256 of all hashes concatenated
            duration      — video duration in seconds
            resolution    — "WxH" string
            fps           — frames per second
        """
        from watermark.embedder import get_video_info

        info = get_video_info(video_path)
        fps = info["fps"]
        duration = info["duration"]
        width = info["width"]
        height = info["height"]
        total_frames = int(fps * duration)

        if total_frames < 1:
            raise ValueError("Video has no frames.")

        # Compute evenly-spaced frame indices
        if total_frames <= self.SAMPLE_FRAMES:
            indices = list(range(total_frames))
        else:
            step = total_frames / self.SAMPLE_FRAMES
            indices = [int(i * step) for i in range(self.SAMPLE_FRAMES)]

        work_dir = tempfile.mkdtemp(prefix="sportsmark_fp_")
        frame_hashes = []

        try:
            for i, frame_idx in enumerate(indices):
                ts = frame_idx / fps
                out_path = os.path.join(work_dir, f"fp_{i:04d}.png")
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(ts),
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",
                    out_path,
                ]
                subprocess.run(cmd, capture_output=True, check=True)

                if os.path.exists(out_path):
                    try:
                        h = phash_image(out_path)
                        frame_hashes.append(h)
                    except Exception:
                        pass  # skip unreadable frames
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        if not frame_hashes:
            raise RuntimeError("Could not extract any fingerprint frames.")

        master_hash = hashlib.sha256("".join(frame_hashes).encode()).hexdigest()

        return {
            "frame_hashes": frame_hashes,
            "master_hash": master_hash,
            "duration": round(duration, 3),
            "resolution": f"{width}x{height}",
            "fps": round(fps, 3),
        }

    # ── Comparison ────────────────────────────────────────────────────────────

    def compare(self, fp1: dict, fp2: dict) -> dict:
        """
        Compare two fingerprints.

        For each hash in fp2, find best matching hash in fp1.
        Returns:
            is_match      — True if avg_similarity >= MATCH_THRESHOLD OR match_ratio >= 0.6
            similarity    — average best-match similarity score
            matched_frames— count of frames with similarity >= MATCH_THRESHOLD
            verdict       — human-readable string
        """
        hashes1 = fp1["frame_hashes"]
        hashes2 = fp2["frame_hashes"]

        if not hashes1 or not hashes2:
            return {
                "is_match": False,
                "similarity": 0.0,
                "matched_frames": 0,
                "verdict": "Insufficient fingerprint data",
            }

        similarities = []
        for h2 in hashes2:
            best = max(similarity_score(h1, h2) for h1 in hashes1)
            similarities.append(best)

        avg_sim = sum(similarities) / len(similarities)
        matched = sum(1 for s in similarities if s >= self.MATCH_THRESHOLD)
        match_ratio = matched / len(similarities)

        is_match = avg_sim >= self.MATCH_THRESHOLD or match_ratio >= 0.6

        if avg_sim >= 0.95:
            verdict = "EXACT DUPLICATE — identical or near-identical copy"
        elif is_match:
            verdict = "PROBABLE PIRACY — content matches with high confidence"
        elif avg_sim >= 0.55:
            verdict = "SUSPICIOUS — partial match, manual review recommended"
        else:
            verdict = "NO MATCH — content differs significantly"

        return {
            "is_match": is_match,
            "similarity": round(avg_sim, 4),
            "matched_frames": matched,
            "verdict": verdict,
        }

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def phash_image(self, image_path: str, hash_size: int = 16) -> str:
        return phash_image(image_path, hash_size)

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        return hamming_distance(hash1, hash2)

    def similarity_score(self, hash1: str, hash2: str) -> float:
        return similarity_score(hash1, hash2)
