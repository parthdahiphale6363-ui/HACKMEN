"""
visual_forensics.py — OpenCV Visual Stream Forensic Analysis
============================================================
Performs computer vision anomaly inspection on sampled video keyframes:
  - Frame-difference & scene cut detection (color histogram / SSIM distance)
  - 2D FFT frequency spectrum analysis (high-frequency spectral energy & grid artifacts)
  - Laplacian focus variance & blur inconsistency across shots
  - Face detection & boundary artifact analysis (sharpness mismatch & alignment jitter)
  - Error Level Analysis (ELA) on selected keyframes with explicit caveats
All outputs represent anomaly indicators rather than deterministic proof of manipulation.
"""

import os
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None


def _require_cv2(feature_name: str = "visual forensics"):
    """Validates cv2 availability and raises an actionable error if missing."""
    if cv2 is None:
        raise RuntimeError(
            f"OpenCV (cv2) is required for {feature_name} but is not installed. "
            "Please install 'opencv-python-headless' (e.g., pip install opencv-python-headless)."
        )
    return cv2


from shared.schemas.forensics import (
    OpenCVVisualForensics,
    SceneCutAnalysis,
    LaplacianBlurAnalysis,
    FFTSpectralAnalysis,
    FaceBoundaryAnalysis,
    ErrorLevelAnalysisData,
)


def _compute_fft_spectrum(gray_frame: np.ndarray) -> Tuple[float, float, List[str]]:
    """
    Computes 2D Fast Fourier Transform high-frequency ratio and spectral regularity.
    GANs and diffusion models often present abnormal high-frequency spectral roll-offs
    or periodic frequency spikes from upsampling convolution layers.
    """
    h, w = gray_frame.shape
    if h < 32 or w < 32:
        return 0.0, 1.0, []

    f = np.fft.fft2(gray_frame)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)

    # Coordinate grid from center
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_r = np.sqrt(cx ** 2 + cy ** 2)

    total_energy = np.sum(magnitude) + 1e-9
    high_freq_mask = r > (0.5 * max_r)
    high_freq_energy = np.sum(magnitude[high_freq_mask])
    high_freq_ratio = float(high_freq_energy / total_energy)

    # Check for radial symmetry / regularity
    quad1 = magnitude[:cy, :cx]
    quad2 = magnitude[:cy, cx:]
    quad3 = magnitude[cy:, :cx]
    quad4 = magnitude[cy:, cx:]
    min_dim_y = min(quad1.shape[0], quad2.shape[0], quad3.shape[0], quad4.shape[0])
    min_dim_x = min(quad1.shape[1], quad2.shape[1], quad3.shape[1], quad4.shape[1])

    q1_sum = np.sum(quad1[:min_dim_y, :min_dim_x])
    q2_sum = np.sum(quad2[:min_dim_y, :min_dim_x])
    q3_sum = np.sum(quad3[:min_dim_y, :min_dim_x])
    q4_sum = np.sum(quad4[:min_dim_y, :min_dim_x])
    quad_sums = [q1_sum, q2_sum, q3_sum, q4_sum]
    regularity = float(min(quad_sums) / (max(quad_sums) + 1e-9))

    flags = []
    if high_freq_ratio < 0.010:
        flags.append("Abnormally suppressed high-frequency spectrum (excessive smoothing/upsampling)")
    elif high_freq_ratio > 0.52:
        flags.append("Elevated high-frequency energy pattern (possible artificial synthesis / noise overlay)")

    if regularity < 0.35:
        flags.append("Asymmetric 2D frequency distribution detected")

    return round(high_freq_ratio, 4), round(regularity, 3), flags


def _compute_ela_metrics(frame: np.ndarray, quality: int = 90) -> Tuple[float, float, float]:
    """
    Error Level Analysis on a single keyframe:
    Compresses frame to JPEG at specified quality, differences against original,
    and returns (mean_error, max_error, variance).
    """
    _require_cv2("Error Level Analysis (ELA)")
    success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        return 0.0, 0.0, 0.0

    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if recompressed is None or recompressed.shape != frame.shape:
        return 0.0, 0.0, 0.0

    diff = cv2.absdiff(frame, recompressed).astype(np.float32)
    mean_err = float(np.mean(diff))
    max_err = float(np.max(diff))
    variance = float(np.var(diff))
    return round(mean_err, 3), round(max_err, 3), round(variance, 3)


def analyze_video_visual(video_path: Optional[str]) -> Dict[str, Any]:
    """
    Primary OpenCV Visual Forensics Analyzer.
    Samples frames iteratively (1 fps, max 45 frames) without loading full video into RAM.
    """
    if not video_path or not os.path.isfile(video_path):
        schema = OpenCVVisualForensics(
            status="not_assessed",
            limitations="No local video file available for visual frame analysis (audio-only source or skipped download).",
        )
        return schema.model_dump()

    _require_cv2("video visual frame analysis")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        schema = OpenCVVisualForensics(
            status="failed",
            limitations=f"Could not open video file with OpenCV: {os.path.basename(video_path)}",
        )
        return schema.model_dump()

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        duration = round(total_frames / max(fps, 1.0), 2) if total_frames > 0 else None
        resolution = f"{width}x{height}" if width and height else None

        # Sample at ~1 frame per second, capped between 3 and 45 frames max
        step = max(int(fps), 1)
        max_samples = 45

        # Load OpenCV Haar face detector
        haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(haar_path) if os.path.exists(haar_path) else None

        frames_analyzed = 0
        prev_hsv_hist = None
        scene_cut_count = 0
        abrupt_transitions = 0
        cut_timestamps = []
        frame_diffs = []

        laplacian_variances = []
        fft_high_freq_ratios = []
        fft_regularities = []
        fft_flags_all = []

        face_count_total = 0
        boundary_blur_ratios = []
        face_centroids = []
        face_flags_all = []

        ela_means = []
        ela_maxes = []
        ela_vars = []
        suspicious_segments = []

        current_frame_idx = 0
        while True:
            try:
                ret, frame = cap.read()
            except Exception as read_err:
                logger.warning(f"Error reading frame {current_frame_idx}: {read_err}")
                break

            if not ret or frames_analyzed >= max_samples:
                break

            if current_frame_idx % step == 0:
                try:
                    frames_analyzed += 1
                    curr_timestamp = round(current_frame_idx / max(fps, 1.0), 2)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    # ── 1. Scene Difference & Cut Detection ──
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
                    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                    if prev_hsv_hist is not None:
                        # Compare histogram correlation (1.0 = identical, < 0.6 = transition, < 0.35 = hard cut)
                        sim = float(cv2.compareHist(prev_hsv_hist, hist, cv2.HISTCMP_CORREL))
                        diff_val = round(max(0.0, 1.0 - sim), 3)
                        frame_diffs.append(diff_val)

                        if sim < 0.35:
                            scene_cut_count += 1
                            cut_timestamps.append(curr_timestamp)
                        elif sim < 0.60:
                            abrupt_transitions += 1
                    prev_hsv_hist = hist

                    # ── 2. Laplacian Blur / Focus Variance ──
                    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                    laplacian_variances.append(lap_var)

                    # ── 3. 2D FFT Frequency Analysis ──
                    hf_ratio, reg, fft_flags = _compute_fft_spectrum(gray)
                    fft_high_freq_ratios.append(hf_ratio)
                    fft_regularities.append(reg)
                    fft_flags_all.extend(fft_flags)
                    if fft_flags and len(suspicious_segments) < 8:
                        suspicious_segments.append({
                            "start_time": curr_timestamp,
                            "end_time": round(curr_timestamp + 1.0, 2),
                            "anomaly_type": "spectral_frequency_anomaly",
                            "description": "; ".join(fft_flags),
                            "severity": "moderate",
                        })

                    # ── 4. Face Detection & Boundary Blur Mismatch ──
                    if face_cascade and not face_cascade.empty():
                        detected_faces = face_cascade.detectMultiScale(
                            gray, scaleFactor=1.15, minNeighbors=5, minSize=(40, 40)
                        )
                        if len(detected_faces) > 0:
                            face_count_total += len(detected_faces)
                            for (fx, fy, fw, fh) in detected_faces[:2]:  # inspect up to 2 primary faces
                                face_centroids.append((fx + fw // 2, fy + fh // 2))

                                # Face ROI blur
                                face_roi = gray[fy : fy + fh, fx : fx + fw]
                                face_blur = float(cv2.Laplacian(face_roi, cv2.CV_64F).var()) if face_roi.size > 0 else 0.0

                                # Perimeter margin band (outer 25% boundary border)
                                pad_w, pad_h = int(fw * 0.25), int(fh * 0.25)
                                oy1, oy2 = max(0, fy - pad_h), min(height, fy + fh + pad_h)
                                ox1, ox2 = max(0, fx - pad_w), min(width, fx + fw + pad_w)
                                outer_roi = gray[oy1:oy2, ox1:ox2].copy()

                                if outer_roi.size > 0 and face_roi.size > 0:
                                    # Mask out inner face from outer ROI
                                    mask_y1 = fy - oy1
                                    mask_y2 = mask_y1 + fh
                                    mask_x1 = fx - ox1
                                    mask_x2 = mask_x1 + fw
                                    outer_roi[mask_y1:mask_y2, mask_x1:mask_x2] = 0

                                    outer_blur = float(cv2.Laplacian(outer_roi, cv2.CV_64F).var())
                                    if outer_blur > 10.0 and face_blur > 5.0:
                                        ratio = round(face_blur / outer_blur, 3)
                                        boundary_blur_ratios.append(ratio)
                                        # Splicing artifact: soft face on sharp background
                                        if ratio < 0.30 and face_blur < 20.0 and outer_blur >= 40.0:
                                            msg = "Soft/blurry facial region superimposed on sharper background"
                                            face_flags_all.append(msg)
                                            if len(suspicious_segments) < 8:
                                                suspicious_segments.append({
                                                    "start_time": curr_timestamp,
                                                    "end_time": round(curr_timestamp + 1.0, 2),
                                                    "anomaly_type": "face_boundary_blur_mismatch",
                                                    "description": f"Face blur ratio {ratio} indicates possible soft facial grafting on sharp frame",
                                                    "severity": "high",
                                                })
                                        # Splicing artifact: unnaturally sharp face on already sharp scene
                                        elif ratio > 4.5 and outer_blur >= 35.0:
                                            msg = "Unnaturally sharp facial boundary compared to surrounding scene"
                                            face_flags_all.append(msg)
                                            if len(suspicious_segments) < 8:
                                                suspicious_segments.append({
                                                    "start_time": curr_timestamp,
                                                    "end_time": round(curr_timestamp + 1.0, 2),
                                                    "anomaly_type": "face_boundary_edge_discontinuity",
                                                    "description": f"Face blur ratio {ratio} exceeds typical focus bounds",
                                                    "severity": "moderate",
                                                })

                    # ── 5. Error Level Analysis (on up to 5 evenly spaced keyframes) ──
                    if frames_analyzed in (1, 5, 10, 20, 30):
                        em, emax, ev = _compute_ela_metrics(frame)
                        ela_means.append(em)
                        ela_maxes.append(emax)
                        ela_vars.append(ev)

                except Exception as frame_proc_err:
                    logger.debug(f"Skipping problematic frame {current_frame_idx}: {frame_proc_err}")

            current_frame_idx += 1

    except Exception as stream_err:
        logger.error(f"Error processing video stream with OpenCV: {stream_err}")
        schema = OpenCVVisualForensics(
            status="failed",
            limitations=f"OpenCV visual analysis error: {stream_err}",
        )
        return schema.model_dump()
    finally:
        cap.release()

    if frames_analyzed == 0:
        schema = OpenCVVisualForensics(
            status="failed",
            limitations="No readable video frames could be extracted from video stream.",
        )
        return schema.model_dump()

    # ── Consolidate Metrics ──
    # Scene cuts
    scene_cuts_data = SceneCutAnalysis(
        count=scene_cut_count,
        abrupt_transitions=abrupt_transitions,
        cut_timestamps=cut_timestamps[:10],
        mean_frame_difference=round(float(np.mean(frame_diffs)), 3) if frame_diffs else 0.0,
    )

    # Laplacian blur
    mean_lap = round(float(np.mean(laplacian_variances)), 2) if laplacian_variances else 0.0
    min_lap = round(float(np.min(laplacian_variances)), 2) if laplacian_variances else 0.0
    max_lap = round(float(np.max(laplacian_variances)), 2) if laplacian_variances else 0.0
    lap_flags = []
    if mean_lap < 25.0:
        lap_flags.append(f"Low overall frame sharpness (mean variance: {mean_lap}) — heavy compression or softening filter")
    blur_stability = round(float(min_lap / (max_lap + 1e-9)), 3) if max_lap > 0 else 1.0
    if blur_stability < 0.15 and len(laplacian_variances) > 5:
        lap_flags.append("High focus instability observed across sampled frames")

    laplacian_data = LaplacianBlurAnalysis(
        mean_variance=mean_lap,
        variance_stability=blur_stability,
        min_variance=min_lap,
        max_variance=max_lap,
        flags=lap_flags,
    )

    # FFT Spectral
    mean_hf = round(float(np.mean(fft_high_freq_ratios)), 4) if fft_high_freq_ratios else 0.0
    mean_reg = round(float(np.mean(fft_regularities)), 3) if fft_regularities else 1.0
    unique_fft_flags = list(set(fft_flags_all))[:3]
    fft_data = FFTSpectralAnalysis(
        high_frequency_ratio=mean_hf,
        spectral_regularity=mean_reg,
        anomaly_indicators=unique_fft_flags,
    )

    # Face boundary analysis
    faces_detected = bool(face_count_total > 0)
    jitter_score = None
    if len(face_centroids) >= 2:
        displacements = [
            np.sqrt((face_centroids[i][0] - face_centroids[i - 1][0]) ** 2 + (face_centroids[i][1] - face_centroids[i - 1][1]) ** 2)
            for i in range(1, len(face_centroids))
        ]
        jitter_score = round(float(np.std(displacements)), 2) if displacements else None

    face_indicators = list(set(face_flags_all))[:3]
    if jitter_score and jitter_score > 65.0:
        face_indicators.append(f"High facial centroid displacement jitter ({jitter_score:.1f}px variance)")

    face_data = FaceBoundaryAnalysis(
        status="assessed" if faces_detected else "not_assessed (no faces detected)",
        faces_detected=faces_detected,
        total_faces_tracked=face_count_total,
        mean_boundary_blur_ratio=round(float(np.mean(boundary_blur_ratios)), 3) if boundary_blur_ratios else None,
        jitter_score=jitter_score,
        anomaly_indicators=face_indicators,
    )

    # Error Level Analysis
    ela_applied = len(ela_means) > 0
    ela_data = ErrorLevelAnalysisData(
        status="assessed" if ela_applied else "skipped",
        applied=ela_applied,
        mean_error=round(float(np.mean(ela_means)), 3) if ela_means else None,
        max_error=round(float(np.max(ela_maxes)), 3) if ela_maxes else None,
        variance=round(float(np.mean(ela_vars)), 3) if ela_vars else None,
        limitations="ELA highlights re-compression differences across uniform surfaces, but is sensitive to natural edge contrast and historical re-encoding. It is an anomaly indicator, not proof of splicing.",
    )

    # Consolidated anomaly signals
    observed_anomalies = []
    if scene_cuts_data.abrupt_transitions >= 4:
        observed_anomalies.append(f"Multiple abrupt shot transitions detected ({scene_cuts_data.abrupt_transitions} events)")
    observed_anomalies.extend(lap_flags)
    observed_anomalies.extend(unique_fft_flags)
    observed_anomalies.extend(face_indicators)

    anomaly_count = len(observed_anomalies)
    if anomaly_count == 0:
        anomaly_level = "low"
    elif anomaly_count <= 2:
        anomaly_level = "moderate"
    else:
        anomaly_level = "elevated"

    schema = OpenCVVisualForensics(
        status="assessed",
        frames_analyzed=frames_analyzed,
        video_duration_seconds=duration,
        video_resolution=resolution,
        scene_cuts=scene_cuts_data,
        laplacian_blur=laplacian_data,
        fft_spectral_analysis=fft_data,
        face_boundary_analysis=face_data,
        error_level_analysis=ela_data,
        anomaly_level=anomaly_level,
        observed_anomalies=observed_anomalies[:6],
        suspicious_segments=suspicious_segments,
        limitations="Visual forensic indicators measure statistical, boundary, and frequency properties. They indicate anomalies for analyst review and do not constitute deterministic proof of synthetic media generation.",
    )
    return schema.model_dump()
