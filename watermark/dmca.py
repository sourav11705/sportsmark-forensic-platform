"""
watermark/dmca.py
DMCA takedown notice generator for SportsMark.
Generates legally-formatted DMCA notices per 17 U.S.C. § 512.
"""

from datetime import datetime, timezone


def generate_dmca(
    detection: dict,
    asset: dict,
    session: dict,
    organization: str,
    contact_email: str,
    address: str,
    signatory: str,
) -> str:
    """
    Generate a DMCA takedown notice string.

    Args:
        detection:      detection record from registry.log_detection
        asset:          asset record from registry.get_asset
        session:        session record from registry.lookup_session
        organization:   name of the copyright holder / organization
        contact_email:  contact email for DMCA correspondence
        address:        physical address of the copyright holder
        signatory:      full name of the person signing the notice

    Returns:
        Formatted DMCA notice as a multi-line string.
    """
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    # ── Pull values with safe defaults ────────────────────────────────────────
    detection_id = detection.get("detection_id", "N/A")
    detected_at = detection.get("detected_at", "N/A")
    source_url = detection.get("source_url", "N/A")
    platform = detection.get("platform", "N/A")

    asset_id = asset.get("asset_id", "N/A")
    title = asset.get("title", "N/A")

    session_id = session.get("session_id", "N/A") if session else "N/A"
    user_id = session.get("user_id", "N/A") if session else "N/A"
    sess_platform = session.get("platform", "N/A") if session else "N/A"
    distributed_at = session.get("timestamp", "N/A") if session else "N/A"

    fp_match = detection.get("fingerprint_match", {})
    similarity_pct = round(fp_match.get("similarity", 0) * 100, 1)
    matched_frames = fp_match.get("matched_frames", "N/A")
    fp_verdict = fp_match.get("verdict", "N/A")

    notice = f"""\
================================================================================
           DMCA TAKEDOWN NOTICE — Pursuant to 17 U.S.C. § 512
================================================================================

Date:         {now_str}
Detection ID: {detection_id}
Session ID:   {session_id}

────────────────────────────────────────────────────────────────────────────────
SECTION 1 — IDENTIFICATION OF COPYRIGHTED WORK
────────────────────────────────────────────────────────────────────────────────

Title of Copyrighted Work : {title}
Asset Identifier           : {asset_id}
Copyright Holder           : {organization}

The above-identified work is an original audiovisual work owned exclusively by
{organization}. All rights are reserved under applicable copyright law.

────────────────────────────────────────────────────────────────────────────────
SECTION 2 — INFRINGING MATERIAL
────────────────────────────────────────────────────────────────────────────────

Infringing URL    : {source_url}
Platform          : {platform}
Date Detected     : {detected_at}

The infringing content was identified through automated forensic analysis as an
unauthorized reproduction of the copyrighted work identified above.

────────────────────────────────────────────────────────────────────────────────
SECTION 3 — FORENSIC EVIDENCE
────────────────────────────────────────────────────────────────────────────────

Watermark Session ID   : {session_id}
Distributed To         : User "{user_id}" via platform "{sess_platform}"
Distribution Timestamp : {distributed_at}

Content Fingerprint Match
  Similarity Score   : {similarity_pct}%
  Matched Frames     : {matched_frames}
  Forensic Verdict   : {fp_verdict}

This notice is supported by cryptographic digital watermark evidence embedded
invisibly into the video using blind DCT steganography. The watermark uniquely
identifies the distribution session and end-user to whom the content was
licensed. The perceptual fingerprint comparison further confirms the infringing
content is derived from the original copyrighted work.

────────────────────────────────────────────────────────────────────────────────
SECTION 4 — STATEMENT OF AUTHORITY
────────────────────────────────────────────────────────────────────────────────

I, {signatory}, on behalf of {organization}, have a good-faith belief that the
use of the material described above is not authorized by the copyright owner,
its agent, or the law.

I declare under penalty of perjury that the information in this notification is
accurate and that I am authorized to act on behalf of the copyright owner.

────────────────────────────────────────────────────────────────────────────────
SECTION 5 — REQUESTED ACTION
────────────────────────────────────────────────────────────────────────────────

We respectfully request that you immediately:

  1. Remove or disable access to the infringing material at the URL identified
     above.
  2. Prevent re-upload of the same or substantially similar content.
  3. Provide the identity information of the account holder responsible for the
     upload to assist in further legal proceedings if necessary.
  4. Confirm removal via email to {contact_email} within 24 hours.

Failure to comply may result in further legal action, including but not limited
to injunctive relief and claims for statutory damages under 17 U.S.C. § 504.

────────────────────────────────────────────────────────────────────────────────
SECTION 6 — CONTACT INFORMATION
────────────────────────────────────────────────────────────────────────────────

Copyright Holder : {organization}
Contact Email    : {contact_email}
Address          : {address}

────────────────────────────────────────────────────────────────────────────────
DECLARATION
────────────────────────────────────────────────────────────────────────────────

Signed electronically:

{signatory}
Authorized Representative, {organization}
Date: {now_str}

================================================================================
This notice is generated automatically by the SportsMark Forensic Watermarking
System. Forensic evidence is retained and available for legal proceedings.
================================================================================
"""
    return notice


def save_dmca(notice: str, output_path: str) -> None:
    """Write the DMCA notice string to a text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(notice)
    print(f"  [dmca] Notice saved → {output_path}")
