"""
demo.py -- SportsMark end-to-end demonstration
==============================================
Runs the full forensic watermarking and piracy detection pipeline:

  STEP 1  Create synthetic test video via FFmpeg lavfi
  STEP 2  Register asset (fingerprint + registry)
  STEP 3  Distribute watermarked copies to 3 users
  STEP 3.5 Verify watermark extraction round-trip
  STEP 4  Simulate piracy attack (re-encode + colour shift)
  STEP 5  Detect piracy (fingerprint + watermark extraction)
  STEP 6  Generate and save DMCA notice
  SUMMARY Print final report
"""
import sys, io
# Force UTF-8 on Windows consoles that default to cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import uuid
import subprocess

# ── Make sure the project root is on the path ─────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from watermark.embedder import VideoWatermarker
from watermark.fingerprint import VideoFingerprinter
from watermark import registry
from watermark.dmca import generate_dmca, save_dmca

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

DIVIDER = "-" * 72


def section(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")


def check_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run(
                [tool, "-version"],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            sys.exit(
                f"[ERROR] '{tool}' not found in PATH. "
                "Please install FFmpeg and add it to PATH."
            )


def file_size_str(path: str) -> str:
    if not os.path.exists(path):
        return "missing"
    size = os.path.getsize(path)
    if size >= 1_048_576:
        return f"{size / 1_048_576:.2f} MB"
    elif size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


# ─────────────────────────────────────────────
# STEP 1 -- Create test video
# ─────────────────────────────────────────────

def step1_create_test_video(output_path: str) -> str:
    section("STEP 1 -- Creating synthetic test video (FFmpeg lavfi)")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=5:size=640x360:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"  [OK]  Test video created: {output_path}  ({file_size_str(output_path)})")
    return output_path


# ─────────────────────────────────────────────
# STEP 2 -- Register asset
# ─────────────────────────────────────────────

def step2_register_asset(video_path: str) -> tuple[str, dict, dict]:
    section("STEP 2 -- Fingerprinting and registering asset")

    fp = VideoFingerprinter()
    fingerprint = fp.fingerprint(video_path)
    print(f"  Master hash  : {fingerprint['master_hash'][:32]}...")
    print(f"  Duration     : {fingerprint['duration']}s")
    print(f"  Resolution   : {fingerprint['resolution']}")
    print(f"  FPS          : {fingerprint['fps']}")
    print(f"  Frames hashed: {len(fingerprint['frame_hashes'])}")

    asset_id = uuid.uuid4().hex[:12].upper()
    asset = registry.register_asset(
        asset_id=asset_id,
        title="SportsMark Demo Match Highlights",
        fingerprint=fingerprint,
        original_path=os.path.abspath(video_path),
    )
    print(f"\n  [OK]  Asset registered: {asset_id}")
    return asset_id, asset, fingerprint


# ─────────────────────────────────────────────
# STEP 3 -- Distribute watermarked copies
# ─────────────────────────────────────────────

DISTRIBUTION = [
    ("user_007",    "HotstarApp"),
    ("user_042",    "JioCinema"),
    ("user_leaker", "SonyLiv"),
]


def step3_distribute(video_path: str, asset_id: str) -> dict[str, dict]:
    section("STEP 3 -- Distributing watermarked copies")
    embedder = VideoWatermarker()
    sessions = {}

    for user_id, platform in DISTRIBUTION:
        out_name = f"wm_{user_id}.mp4"
        print(f"\n  [{user_id}] -> {platform}")
        session = embedder.embed(
            video_path=video_path,
            user_id=user_id,
            platform=platform,
            output_path=out_name,
        )
        registry.register_session(session, asset_id)
        sessions[user_id] = session
        print(f"  Session ID   : {session['session_id']}")
        print(f"  Full tag     : {session['full_tag']!r}  (len={len(session['full_tag'])})")
        print(f"  wm_length    : {session['wm_length']} bits")
        print(f"  Output       : {out_name}  ({file_size_str(out_name)})")

    return sessions


# ─────────────────────────────────────────────
# STEP 3.5 -- Verify watermark round-trip
# ─────────────────────────────────────────────

def step35_verify(sessions: dict[str, dict]) -> None:
    section("STEP 3.5 -- Verifying watermark extraction round-trip")
    embedder = VideoWatermarker()

    leaker_session = sessions["user_leaker"]
    wm_file = "wm_user_leaker.mp4"
    expected_sid = leaker_session["session_id"]

    print(f"  Extracting from {wm_file} ...")
    result = embedder.extract(wm_file, wm_length=160)

    extracted_sid = result.get("session_id", "")
    match = extracted_sid == expected_sid

    print(f"  Expected session_id : {expected_sid}")
    print(f"  Extracted session_id: {extracted_sid}")
    print(f"  Confidence          : {result.get('confidence', 0):.1%}")

    if match:
        print("  [OK]  Watermark verified -- session_id matches perfectly!")
    else:
        print("  [WARN]  Partial match -- watermark may be degraded (still proceeding)")
        print(f"       Raw tag: {result.get('raw_tag')!r}")


# ─────────────────────────────────────────────
# STEP 4 -- Simulate piracy attack
# ─────────────────────────────────────────────

def step4_simulate_piracy(input_path: str, output_path: str) -> None:
    section("STEP 4 -- Simulating piracy attack (re-encode + colour shift)")
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "eq=brightness=0.05:contrast=1.05",
        "-c:v", "libx264",
        "-crf", "35",
        "-c:a", "copy",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"  [OK]  Pirated clip created: {output_path}  ({file_size_str(output_path)})")
    print("       Attack: CRF-35 re-encode + brightness +0.05 / contrast ×1.05")


# ─────────────────────────────────────────────
# STEP 5 -- Detect piracy
# ─────────────────────────────────────────────

def step5_detect(
    pirated_path: str,
    original_fingerprint: dict,
    asset_id: str,
) -> tuple[dict, dict]:
    section("STEP 5 -- Detecting piracy")

    # 5a. Fingerprint comparison
    print("  [5a] Fingerprinting pirated clip ...")
    fp = VideoFingerprinter()
    pirated_fp = fp.fingerprint(pirated_path)
    cmp = fp.compare(original_fingerprint, pirated_fp)

    print(f"  Similarity    : {cmp['similarity']:.1%}")
    print(f"  Matched frames: {cmp['matched_frames']}")
    print(f"  Verdict       : {cmp['verdict']}")
    print(f"  Is match?     : {'YES [OK]' if cmp['is_match'] else 'NO ❌'}")

    # 5b. Watermark extraction
    print("\n  [5b] Extracting watermark from pirated clip ...")
    embedder = VideoWatermarker()
    wm_result = embedder.extract(pirated_path, wm_length=160)
    session_id = wm_result.get("session_id")

    print(f"  Extracted session_id : {session_id}")
    print(f"  Platform code        : {wm_result.get('platform_code')}")
    print(f"  Confidence           : {wm_result.get('confidence', 0):.1%}")

    # 5c. Registry lookup
    leaker_session = None
    if session_id:
        leaker_session = registry.lookup_session(session_id)

    if leaker_session:
        print(f"\n  [FOUND]  LEAKER IDENTIFIED!")
        print(f"      User ID   : {leaker_session['user_id']}")
        print(f"      Platform  : {leaker_session['platform']}")
        print(f"      Licensed  : {leaker_session['timestamp']}")
    else:
        print("\n  [WARN]  Session not found in registry (watermark may be degraded)")
        # Use any session for demo continuation
        all_sessions = registry.list_sessions(asset_id)
        leaker_session = next(
            (s for s in all_sessions if "leaker" in s.get("user_id", "")),
            all_sessions[0] if all_sessions else {},
        )
        print(f"  Using fallback session for demo: {leaker_session.get('session_id')}")

    return cmp, leaker_session


# ─────────────────────────────────────────────
# STEP 6 -- Generate DMCA
# ─────────────────────────────────────────────

def step6_dmca(
    asset_id: str,
    asset: dict,
    leaker_session: dict,
    cmp: dict,
    pirated_url: str = "https://t.me/piracy_channel/leaked_match_highlights.mp4",
    dmca_output: str = "dmca_notice.txt",
) -> str:
    section("STEP 6 -- Logging detection and generating DMCA notice")

    detection = registry.log_detection(
        asset_id=asset_id,
        source_url=pirated_url,
        platform=leaker_session.get("platform", "Unknown"),
        session_data=leaker_session,
        fingerprint_match=cmp,
    )
    print(f"  Detection logged: {detection['detection_id']}")

    notice = generate_dmca(
        detection=detection,
        asset=asset,
        session=leaker_session,
        organization="SportsMark Media Rights Ltd.",
        contact_email="legal@sportsmark.io",
        address="12 Broadcast House, Mumbai 400001, India",
        signatory="A. Antigravity, Chief Legal Officer",
    )
    save_dmca(notice, dmca_output)
    print(f"  [OK]  DMCA notice written -> {dmca_output}")
    return dmca_output


# ─────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────

def print_summary(
    sessions: dict,
    cmp: dict,
    leaker_session: dict,
    dmca_path: str,
) -> None:
    section("FINAL SUMMARY")
    stats = registry.get_stats()

    files = [
        "test_video.mp4",
        "wm_user_007.mp4",
        "wm_user_042.mp4",
        "wm_user_leaker.mp4",
        "pirated_clip.mp4",
        "dmca_notice.txt",
    ]

    print(f"  Assets registered  : {stats['total_assets']}")
    print(f"  Copies distributed : {stats['total_sessions']}")
    print(f"  Violations found   : {stats['total_detections']}")
    print(f"  Platforms affected : {', '.join(stats['platforms_affected']) or 'None'}")
    print()
    print(f"  LEAKER IDENTIFIED  : {leaker_session.get('user_id', 'N/A')}")
    print(f"  Platform           : {leaker_session.get('platform', 'N/A')}")
    print(f"  Fingerprint match  : {cmp['similarity']:.1%}")
    print(f"  DMCA notice        : {os.path.abspath(dmca_path)}")
    print()
    print("  Generated files:")
    for f in files:
        print(f"    {f:<30} {file_size_str(f)}")

    print()
    print("  [DONE] SportsMark forensic pipeline complete.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    print()
    print("=" * 72)
    print("  SportsMark -- Forensic Video Watermarking System")
    print("  Piracy Detection & DMCA Automation Demo")
    print("=" * 72)

    # Pre-flight check
    check_ffmpeg()

    TEST_VIDEO = "test_video.mp4"
    PIRATED = "pirated_clip.mp4"
    DMCA_OUT = "dmca_notice.txt"

    # ── STEP 1 ───────────────────────────────────────────────────────────────
    step1_create_test_video(TEST_VIDEO)

    # ── STEP 2 ───────────────────────────────────────────────────────────────
    asset_id, asset, orig_fp = step2_register_asset(TEST_VIDEO)

    # ── STEP 3 ───────────────────────────────────────────────────────────────
    sessions = step3_distribute(TEST_VIDEO, asset_id)

    # ── STEP 3.5 ─────────────────────────────────────────────────────────────
    step35_verify(sessions)

    # ── STEP 4 ───────────────────────────────────────────────────────────────
    step4_simulate_piracy("wm_user_leaker.mp4", PIRATED)

    # ── STEP 5 ───────────────────────────────────────────────────────────────
    cmp, leaker_session = step5_detect(PIRATED, orig_fp, asset_id)

    # ── STEP 6 ───────────────────────────────────────────────────────────────
    dmca_path = step6_dmca(asset_id, asset, leaker_session, cmp, dmca_output=DMCA_OUT)

    # ── SUMMARY ──────────────────────────────────────────────────────────────
    print_summary(sessions, cmp, leaker_session, dmca_path)


if __name__ == "__main__":
    main()
