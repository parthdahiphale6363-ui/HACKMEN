"""
forensics.py — Pydantic Schemas for Multi-Modal Forensics
==========================================================
Defines typed schemas for OpenCV visual analysis and Gemini audio analysis.
Every result is treated as an anomaly indicator, not absolute proof of manipulation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SceneCutAnalysis(BaseModel):
    count: int = Field(default=0, description="Total scene cuts / abrupt shot boundaries detected")
    abrupt_transitions: int = Field(default=0, description="Number of severe color/SSIM distance frame transitions")
    cut_timestamps: List[float] = Field(default_factory=list, description="Estimated timestamps (seconds) of scene transitions")
    mean_frame_difference: float = Field(default=0.0, description="Average histogram difference between consecutive frames")


class LaplacianBlurAnalysis(BaseModel):
    mean_variance: float = Field(default=0.0, description="Average Laplacian variance (sharpness)")
    variance_stability: float = Field(default=1.0, description="Stability ratio of blur across frames (0 to 1)")
    min_variance: float = Field(default=0.0, description="Minimum frame sharpness observed")
    max_variance: float = Field(default=0.0, description="Maximum frame sharpness observed")
    flags: List[str] = Field(default_factory=list, description="Sharpness/blur anomaly observations")


class FFTSpectralAnalysis(BaseModel):
    high_frequency_ratio: float = Field(default=0.0, description="Ratio of high-frequency to total spectral energy in 2D FFT")
    spectral_regularity: float = Field(default=1.0, description="Radial power distribution regularity score")
    anomaly_indicators: List[str] = Field(default_factory=list, description="Spectral noise anomaly indicators")


class FaceBoundaryAnalysis(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed (no faces detected) | failed")
    faces_detected: bool = Field(default=False, description="Whether human faces were detected in sampled frames")
    total_faces_tracked: int = Field(default=0, description="Count of face bounding boxes detected across frames")
    mean_boundary_blur_ratio: Optional[float] = Field(None, description="Ratio of face ROI sharpness to outer perimeter band sharpness")
    jitter_score: Optional[float] = Field(None, description="Center coordinate displacement jitter between adjacent face instances")
    anomaly_indicators: List[str] = Field(default_factory=list, description="Face boundary and warping anomaly indicators")


class ErrorLevelAnalysisData(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed | skipped")
    applied: bool = Field(default=False, description="Whether ELA was calculated on keyframes")
    mean_error: Optional[float] = Field(None, description="Mean pixel difference after re-compression")
    max_error: Optional[float] = Field(None, description="Maximum pixel error observed")
    variance: Optional[float] = Field(None, description="Error level spatial variance")
    limitations: str = Field(
        default="ELA highlights re-compression differences across uniform surfaces, but is sensitive to natural edge contrast and historical re-encoding. It is an anomaly indicator, not proof of splicing.",
        description="Scientific limitations disclaimer"
    )


class OpenCVVisualForensics(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed | failed")
    methodology: str = Field(
        default="OpenCV keyframe extraction (1 fps) with 2D FFT spectral profiling, Laplacian focus variance, Haar face boundary analysis, and scene difference metrics.",
        description="Methodology description"
    )
    detector_provenance: str = Field(default="OpenCV 5.0 (cv2) + NumPy signal processing", description="Library/tool provenance")
    frames_analyzed: int = Field(default=0, description="Number of sampled frames analyzed")
    video_duration_seconds: Optional[float] = Field(None, description="Total duration of the analyzed video in seconds")
    video_resolution: Optional[str] = Field(None, description="Resolution string (e.g. 640x360)")
    scene_cuts: SceneCutAnalysis = Field(default_factory=SceneCutAnalysis)
    laplacian_blur: LaplacianBlurAnalysis = Field(default_factory=LaplacianBlurAnalysis)
    fft_spectral_analysis: FFTSpectralAnalysis = Field(default_factory=FFTSpectralAnalysis)
    face_boundary_analysis: FaceBoundaryAnalysis = Field(default_factory=FaceBoundaryAnalysis)
    error_level_analysis: ErrorLevelAnalysisData = Field(default_factory=ErrorLevelAnalysisData)
    anomaly_level: str = Field(default="low", description="low | moderate | elevated")
    visual_synthetic_score: float = Field(default=0.0, description="Estimated visual synthetic AI generation probability (0 to 1)")
    observed_anomalies: List[str] = Field(default_factory=list, description="Consolidated visual anomaly signals")
    suspicious_segments: List[Dict[str, Any]] = Field(default_factory=list, description="Timestamped suspicious visual intervals")
    limitations: str = Field(
        default="Visual forensic indicators measure statistical and frequency anomalies. They do not constitute deterministic proof of synthetic media generation.",
        description="Caveats and limitations"
    )


class TranscriptComparison(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed | failed")
    gemini_transcript: Optional[str] = Field(None, description="Verbatim transcript generated by Gemini Flash")
    whisper_transcript: Optional[str] = Field(None, description="Transcript generated by Groq Whisper")
    similarity_score: Optional[float] = Field(None, description="Token-level lexical similarity between transcripts (0 to 1)")
    discrepancies: List[str] = Field(default_factory=list, description="Substantive word or phrase discrepancies noted")
    timestamp_notes: Optional[str] = Field(None, description="Alignment or temporal observations")


class AcousticAnomalyAnalysis(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed | failed")
    cadence_observations: Optional[str] = Field(None, description="Observations on speech rhythm, prosody, and pauses")
    robotic_artifacts: Optional[str] = Field(None, description="Notes on metallic timbre, unnatural pitch flattening, or phase glitches")
    room_acoustics_consistent: Optional[bool] = Field(None, description="Whether background reverberation is consistent across speech")
    anomaly_indicators: List[str] = Field(default_factory=list, description="Acoustic anomaly signals observed")


class VoiceCloneAssessment(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed")
    disclaimer: str = Field(
        default="No validated biometric voiceprint classifier is available. Voice clone probability cannot be claimed reliably without calibrated acoustic feature models.",
        description="Scientific disclaimer on voice cloning"
    )
    observations: List[str] = Field(default_factory=list, description="Auditory cues noted during multimodal inspection")


class GeminiAudioForensics(BaseModel):
    status: str = Field(default="not_assessed", description="assessed | not_assessed | failed")
    reason: Optional[str] = Field(None, description="Reason if not assessed or failed (e.g. GEMINI_API_KEY missing)")
    methodology: str = Field(
        default="Google GenAI Multimodal native audio analysis with token-level transcript cross-verification and acoustic anomaly audit.",
        description="Methodology description"
    )
    detector_provenance: str = Field(default="Google GenAI SDK (gemini-2.5-flash / gemini-1.5-flash)", description="Model and SDK provenance")
    model_used: Optional[str] = Field(None, description="Actual model queried")
    transcript_comparison: TranscriptComparison = Field(default_factory=TranscriptComparison)
    acoustic_anomaly_analysis: AcousticAnomalyAnalysis = Field(default_factory=AcousticAnomalyAnalysis)
    voice_clone_assessment: VoiceCloneAssessment = Field(default_factory=VoiceCloneAssessment)
    limitations: str = Field(
        default="Gemini Multimodal inspection provides semantic and auditory anomaly reasoning. It does not replace biometric acoustic analysis or cryptographic provenance verification.",
        description="Forensic limitations"
    )


class SuspiciousSegment(BaseModel):
    start_time: float = Field(..., description="Segment start timestamp in seconds")
    end_time: float = Field(..., description="Segment end timestamp in seconds")
    anomaly_type: str = Field(..., description="Type of anomaly (e.g. face_boundary_mismatch, spectral_anomaly, audio_splice)")
    description: str = Field(..., description="Detailed description of forensic finding")
    severity: str = Field(default="moderate", description="low | moderate | high")


class EvidenceItem(BaseModel):
    detector: str = Field(..., description="Name of detector that produced the evidence")
    signal: str = Field(..., description="Specific signal or measurement")
    severity: str = Field(default="moderate", description="low | moderate | high")
    timestamp: Optional[float] = Field(None, description="Timestamp in seconds if localized")
    details: str = Field(..., description="Forensic interpretation and evidence context")


class ProvenanceData(BaseModel):
    status: str = Field(default="unsupported", description="verified | invalid | missing | unsupported")
    sha256: Optional[str] = Field(None, description="SHA-256 hash of original media file")
    is_valid: bool = Field(default=False, description="Cryptographic validity")
    generator: Optional[str] = Field(None, description="Claim generator application")
    issuer: Optional[str] = Field(None, description="Digital certificate issuer")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Recorded editing actions")
    disclaimer: str = Field(default="", description="Legal/scientific provenance disclaimer")


class UnifiedAuthenticityReport(BaseModel):
    classification: str = Field(
        ...,
        description="One of: LIKELY_AI_GENERATED | POTENTIALLY_AI_EDITED | POTENTIALLY_FACIAL_MANIPULATION | POTENTIALLY_SYNTHETIC_SPEECH | CONVENTIONAL_EDITING_DETECTED | INCONCLUSIVE | AUTHENTIC_NO_ANOMALIES_DETECTED"
    )
    confidence_level: str = Field(default="UNCERTAIN", description="HIGH | MEDIUM | LOW | UNCERTAIN")
    reason: str = Field(..., description="Transparent technical explanation for classification")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Structured verified forensic evidence items")
    suspicious_segments: List[SuspiciousSegment] = Field(default_factory=list, description="Timestamped suspicious media intervals")
    provenance: ProvenanceData = Field(default_factory=ProvenanceData, description="Cryptographic C2PA and file integrity data")
    checks_performed: List[str] = Field(default_factory=list, description="Detectors and analyses that executed")
    checks_unavailable: List[Dict[str, str]] = Field(default_factory=list, description="Detectors not assessed with explicit reasons")
    limitations: List[str] = Field(default_factory=list, description="Scientific limitations and confidence boundaries")
    model_versions: Dict[str, str] = Field(default_factory=dict, description="Software and model version provenance")


class ForensicsReport(BaseModel):
    video_integrity_score: float = Field(default=100.0)
    audio_integrity_score: float = Field(default=100.0)
    metadata_integrity_score: float = Field(default=100.0)
    deepfake_probability: float = Field(default=0.0)
    voice_clone_probability: float = Field(default=0.0)
    scene_consistency_score: float = Field(default=1.0)
    is_synthetic: bool = Field(default=False)
    forensics_veto: Dict[str, Any] = Field(default_factory=dict)
    technical_audio: Dict[str, Any] = Field(default_factory=dict)
    opencv_visual: Dict[str, Any] = Field(default_factory=dict)
    gemini_audio: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    audio_authenticity: Dict[str, Any] = Field(default_factory=dict)
    unified_authenticity: Optional[Dict[str, Any]] = None
    red_flag_count: int = Field(default=0)
    red_flags: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    deepfake_analysis: Optional[Dict[str, Any]] = None
    metadata_analysis: Optional[Dict[str, Any]] = None
    geolocation: Optional[Dict[str, Any]] = None
    temporal_analysis: Optional[Dict[str, Any]] = None
    platform: Optional[str] = None
    summary: str = Field(default="")

