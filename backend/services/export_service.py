"""
export_service.py — Executive Forensic Dossier & Intelligence Brief Generator
Generates publication-ready Markdown and structured JSON intelligence dossiers
for completed video verification jobs.
"""

import hashlib
import json
import datetime
from typing import Dict, Any

def generate_markdown_dossier(
    job_id: str,
    video_url: str,
    overall_verdict: str,
    category: str,
    confidence: float,
    breakdown: Dict[str, Any],
    claims: list,
    forensics: Dict[str, Any] = None,
    osint: Dict[str, Any] = None,
    dm_report: Dict[str, Any] = None
) -> str:
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Generate cryptographic integrity hash for the dossier
    content_to_hash = f"{job_id}:{video_url}:{overall_verdict}:{confidence}:{len(claims)}"
    audit_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()[:16].upper()

    md = []
    md.append("# 🛡️ TruthLens AI — Executive Forensic Verification Dossier")
    md.append(f"**Verification Audit Hash:** `SHA256-{audit_hash}`  ")
    md.append(f"**Generated:** {now_utc}  ")
    md.append(f"**Target Media:** [{video_url}]({video_url})  ")
    md.append(f"**Audit Job ID:** `{job_id}`  \n")
    md.append("---")

    md.append("## 📊 Executive Summary & Final Verdict")
    md.append(f"- **Final Verdict Determination:** **{overall_verdict}**")
    md.append(f"- **Classification Category:** `{category}`")
    md.append(f"- **Calibrated Confidence Score:** **{confidence:.1f}%**")
    
    veto = breakdown.get("veto_applied")
    if veto:
        md.append(f"\n> ⚠️ **CONSTITUTIONAL VETO ENFORCED:** {veto.get('reason')} (Governor: `{veto.get('type')}`)")
        
    md.append("\n### Claim Breakdown Summary")
    md.append(f"| Metric | Value |")
    md.append(f"|---|---|")
    md.append(f"| Total Claims Analyzed | {breakdown.get('total', len(claims))} |")
    md.append(f"| Verified True | {breakdown.get('true', 0)} |")
    md.append(f"| Debunked False | {breakdown.get('false', 0)} |")
    md.append(f"| Misleading / Out of Context | {breakdown.get('misleading', 0)} |")
    md.append(f"| Unverifiable / Low Signal | {breakdown.get('unverifiable', 0)} |")

    # Forensics Section
    if forensics:
        md.append("\n---\n## 🔬 Unified Multimodal Forensics & Media Authenticity")
        
        # Unified Authenticity Engine
        unified = forensics.get("unified_authenticity", {})
        if unified:
            verdict_code = unified.get("overall_verdict") or unified.get("verdict") or "INCONCLUSIVE"
            verdict_label = unified.get("overall_verdict_label") or unified.get("classification") or verdict_code
            confidence_level = unified.get("confidence_level", "UNCERTAIN")
            conf_meaning = unified.get("confidence_meaning", "")
            
            md.append(f"### 🛡️ Final Forensic Determination: **`{verdict_label}`**")
            md.append(f"- **Verdict Code:** `{verdict_code}` ({confidence_level} Confidence)")
            if conf_meaning:
                md.append(f"- **Confidence Basis:** {conf_meaning}")
            md.append(f"- **Technical Summary:** {unified.get('summary') or unified.get('reason')}")
            
            # Coverage Breakdown Table
            coverage = unified.get("analysis_coverage", {})
            vis_m = unified.get("visual", {})
            aud_m = unified.get("audio", {})
            prov_m = unified.get("provenance", {})

            md.append("\n#### 📋 Modality Coverage & Independent Conclusions")
            md.append("| Modality | Execution Status | Independent Verdict | Detector Provenance | Error / Code |")
            md.append("|---|---|---|---|---|")
            md.append(f"| **Visual (Video/Frames)** | `{vis_m.get('status', 'NOT_ANALYZED')}` | `{vis_m.get('verdict_label', 'N/A')}` | {vis_m.get('detector_name', 'OpenCV')} | {vis_m.get('error_code') or 'None'} |")
            md.append(f"| **Audio (Speech/Acoustic)** | `{aud_m.get('status', 'NOT_ANALYZED')}` | `{aud_m.get('verdict_label', 'N/A')}` | {aud_m.get('detector_name', 'Gemini Audio')} | {aud_m.get('error_code') or 'None'} |")
            md.append(f"| **Provenance (C2PA/SHA-256)** | `{prov_m.get('status', 'NOT_ANALYZED')}` | `{prov_m.get('c2pa_status', 'NOT_FOUND')}` | C2PA Content Credentials | None |")

            # C2PA Provenance Details
            sha256_hash = prov_m.get("sha256") or (forensics.get("provenance", {}) or {}).get("sha256")
            md.append(f"\n- **Cryptographic File Digest:** `SHA256:{sha256_hash or 'Not computed'}`")
            if prov_m.get("issuer"):
                md.append(f"- **Content Credentials Origin:** Signed by `{prov_m.get('issuer')}` using `{prov_m.get('generator')}`")
            
            # Suspicious Segments
            segs = unified.get("suspicious_segments", [])
            if segs:
                md.append("\n#### ⏱️ Traceable Suspicious Media Intervals")
                for s in segs:
                    md.append(f"- `{s.get('start_time', 0.0):.1f}s - {s.get('end_time', 0.0):.1f}s`: **{s.get('anomaly_type')}** ({s.get('severity')}) — *{s.get('description')}*")

            # Scientific Limitations
            limits = unified.get("limitations", [])
            if limits:
                md.append("\n#### ⚖️ Scientific Limitations & Forensic Boundaries")
                for lim in limits:
                    md.append(f"- *{lim}*")

        deepfake_pct = round(forensics.get("deepfake_probability", 0) * 100)
        voice_pct = round(forensics.get("voice_clone_probability", 0) * 100)
        consistency_pct = round(forensics.get("scene_consistency_score", 0) * 100)
        
        md.append(f"\n- **Deepfake Manipulation Risk (Heuristic):** **{deepfake_pct}%**")
        md.append(f"- **Neural Voice Clone Risk (Heuristic):** **{voice_pct}%**")
        md.append(f"- **Scene & Lighting Consistency:** **{consistency_pct}%**")
        md.append(f"- **Forensic Red Flags Detected:** **{forensics.get('red_flag_count', 0)}**")
        
        audio = forensics.get("technical_audio", {})
        if audio.get("audio_stream_available"):
            md.append(f"- **Acoustic Stream Analysis:** Codec `{audio.get('codec_name')}`, {audio.get('sample_rate')}Hz, {audio.get('silence_burst_count')} anomalous silence bursts")
        # OpenCV Visual Forensics Sub-Section
        cv_vis = forensics.get("opencv_visual", {})
        if cv_vis:
            md.append("\n### 📸 OpenCV Computer Vision Stream Forensics")
            cv_status = cv_vis.get("status", "not_assessed")
            md.append(f"- **Detector Status:** `{cv_status.upper()}` ({cv_vis.get('detector_provenance', 'OpenCV')})")
            if cv_status == "assessed":
                md.append(f"- **Visual Anomaly Level:** **{cv_vis.get('anomaly_level', 'low').upper()}**")
                md.append(f"- **Frames Analyzed:** {cv_vis.get('frames_analyzed', 0)} frames sampled ({cv_vis.get('video_resolution', 'N/A')}, {cv_vis.get('video_duration_seconds', 'N/A')}s)")
                
                sc = cv_vis.get("scene_cuts", {})
                md.append(f"- **Scene Boundary Shifts:** {sc.get('count', 0)} hard cuts, {sc.get('abrupt_transitions', 0)} abrupt transitions")
                
                lap = cv_vis.get("laplacian_blur", {})
                md.append(f"- **Laplacian Focus Variance:** Mean {lap.get('mean_variance', 0.0)} (Stability: {round(lap.get('variance_stability', 1.0)*100)}%)")
                
                fft = cv_vis.get("fft_spectral_analysis", {})
                md.append(f"- **2D FFT Spectral Distribution:** High-Freq Ratio {fft.get('high_frequency_ratio', 0.0)} (Regularity: {round(fft.get('spectral_regularity', 1.0)*100)}%)")
                
                fb = cv_vis.get("face_boundary_analysis", {})
                if fb.get("faces_detected"):
                    md.append(f"- **Face Boundary Inspection:** {fb.get('total_faces_tracked', 0)} face(s) tracked. Boundary blur ratio: {fb.get('mean_boundary_blur_ratio', 'N/A')}, Centroid jitter: {fb.get('jitter_score', 'N/A')}px")
                else:
                    md.append(f"- **Face Boundary Inspection:** `NOT ASSESSED` (No human faces detected in sampled frames)")
                
                ela = cv_vis.get("error_level_analysis", {})
                if ela.get("applied"):
                    md.append(f"- **Error Level Analysis (ELA):** Mean error: {ela.get('mean_error', 'N/A')}, Variance: {ela.get('variance', 'N/A')}")
                    md.append(f"  > *Caveat:* {ela.get('limitations')}")
            else:
                md.append(f"- *Note:* {cv_vis.get('limitations', 'No visual stream available for OpenCV analysis.')}")

        # Gemini Multimodal Audio Forensics Sub-Section
        gem_audio = forensics.get("gemini_audio", {})
        if gem_audio:
            md.append("\n### 🎙️ Gemini Multimodal Audio Forensics & Cross-Verification")
            gem_status = gem_audio.get("status", "not_assessed")
            md.append(f"- **Engine Status:** `{gem_status.upper()}` (Model: `{gem_audio.get('model_used') or 'N/A'}`)")
            if gem_status == "assessed":
                tc = gem_audio.get("transcript_comparison", {})
                sim = round((tc.get("similarity_score") or 0.0) * 100)
                md.append(f"- **Whisper vs Gemini Transcript Concordance:** **{sim}%** similarity")
                discrepancies = tc.get("discrepancies", [])
                if discrepancies:
                    md.append(f"- **Observed Transcript Discrepancies:** {', '.join(str(d) for d in discrepancies[:3])}")
                
                ac = gem_audio.get("acoustic_anomaly_analysis", {})
                if ac.get("cadence_observations"):
                    md.append(f"- **Cadence & Prosody:** {ac.get('cadence_observations')}")
                if ac.get("robotic_artifacts"):
                    md.append(f"- **Acoustic Artifacts:** {ac.get('robotic_artifacts')}")
                md.append(f"- **Room Acoustic Consistency:** {'Consistent' if ac.get('room_acoustics_consistent') else 'Inconsistent / Anomalous'}")
                
                vc = gem_audio.get("voice_clone_assessment", {})
                md.append(f"  > *Scientific Guard:* {vc.get('disclaimer')}")
            else:
                md.append(f"- *Status Reason:* {gem_audio.get('reason', 'GEMINI_API_KEY unconfigured or audio analysis not requested.')}")

        if forensics.get("summary"):
            md.append(f"\n*Consolidated Forensic Synthesis:* {forensics.get('summary')}")

    # OSINT Section
    if osint:
        md.append("\n---\n## 🌐 Open-Source Intelligence (OSINT) & IFCN Fact-Checks")
        gfc = osint.get("google_factcheck", {})
        fact_checks = gfc.get("fact_checks_found", [])
        if fact_checks:
            md.append(f"### 🎖️ Certified IFCN Fact-Check Reviews ({len(fact_checks)} found)")
            for fc in fact_checks:
                md.append(f"- **[{fc.get('publisher')}]({fc.get('review_url')}):** Rating **{fc.get('rating')}** — *\"{fc.get('title')}\"*")
        else:
            md.append("No active debunks indexed in Google Fact Check Tools database.")
            
        md.append(f"\n- **High-Trust News Sources:** {osint.get('high_trust_sources', 0)} articles")
        md.append(f"- **Corroborating Evidence:** {osint.get('support_count', 0)} sources")
        md.append(f"- **Contradicting Evidence:** {osint.get('contradiction_count', 0)} sources")
        if osint.get("news_summary"):
            md.append(f"\n*OSINT Synthesis:* {osint.get('news_summary')}")

    # Data Mining Section
    if dm_report:
        md.append("\n---\n## ▦ Data Mining & Narrative Pattern Analysis")
        classification = dm_report.get("classification", {})
        md.append(f"- **Linguistic Model Classification:** `{classification.get('category', 'Standard')}` (Confidence: {round(classification.get('confidence', 0)*100)}%)")
        
        patterns = dm_report.get("pattern_mining", {}).get("patterns", [])
        if patterns:
            md.append("\n### Identified Manipulation Patterns")
            for p in patterns:
                md.append(f"- **{p.get('pattern')}** ({p.get('severity').upper()}): {p.get('description')}")

    # Claim-by-Claim Section
    if claims:
        md.append("\n---\n## 🔍 Claim-by-Claim Evidence Matrix")
        for idx, item in enumerate(claims):
            c = item.get("claim", {})
            v = item.get("verdict", {})
            time_str = c.get("time_str") or f"T+{round(c.get('timestamp_in_video', 0))}s"
            
            md.append(f"\n### Claim #{idx + 1} `[{time_str}]` — {v.get('label', 'unverifiable').upper()} ({round(v.get('confidence', 0)*100)}% Confidence)")
            md.append(f"**Extracted Statement:** *\"{c.get('normalized_text') or c.get('raw_text')}\"*")
            md.append(f"\n**AI Reasoning:** {v.get('reasoning') or v.get('summary')}")
            
            evidence_list = v.get("evidence", [])
            if evidence_list:
                md.append("\n**Citations & Sources:**")
                for ev in evidence_list[:3]:
                    stance = "🟢 SUPPORTS" if ev.get("supports_claim") else "🔴 CONTRADICTS"
                    md.append(f"- [{ev.get('source_title')}]({ev.get('source_url')}) ({ev.get('domain')}, Relevance: {round(ev.get('relevance_score', 0)*100)}%) — {stance}")
                    md.append(f"  > *\"{ev.get('snippet')}\"*")

    md.append("\n---\n*TruthLens AI Intelligence Platform — Research-Grade Multimodal Video Fact-Checking Engine*")
    return "\n".join(md)
