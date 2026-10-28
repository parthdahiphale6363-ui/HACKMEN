export interface TechnicalAudio {
  audio_stream_available: boolean;
  codec_name?: string;
  sample_rate?: number;
  channels?: number;
  bit_rate_kbps?: number;
  duration_seconds?: number;
  silence_burst_count: number;
  technical_anomaly_score: number;
  technical_flags: string[];
}

export interface DeepfakeAnalysis {
  analysis_summary?: string;
  speech_rhythm_score?: number;
  pitch_continuity_score?: number;
  spectral_flatness_score?: number;
  tampering_indicators?: string[];
}

export interface GeolocationData {
  locations_found: Array<{
    name: string;
    type: 'country' | 'city' | 'region';
    relevance?: number;
  }>;
}

export interface SceneCutAnalysis {
  count: number;
  abrupt_transitions: number;
  cut_timestamps: number[];
  mean_frame_difference: number;
}

export interface LaplacianBlurAnalysis {
  mean_variance: number;
  variance_stability: number;
  min_variance: number;
  max_variance: number;
  flags: string[];
}

export interface FFTSpectralAnalysis {
  high_frequency_ratio: number;
  spectral_regularity: number;
  anomaly_indicators: string[];
}

export interface FaceBoundaryAnalysis {
  status: string;
  faces_detected: boolean;
  total_faces_tracked: number;
  mean_boundary_blur_ratio?: number;
  jitter_score?: number;
  anomaly_indicators: string[];
}

export interface ErrorLevelAnalysisData {
  status: string;
  applied: boolean;
  mean_error?: number;
  max_error?: number;
  variance?: number;
  limitations: string;
}

export interface OpenCVVisualForensics {
  status: string;
  methodology: string;
  detector_provenance: string;
  frames_analyzed: number;
  video_duration_seconds?: number;
  video_resolution?: string;
  scene_cuts?: SceneCutAnalysis;
  laplacian_blur?: LaplacianBlurAnalysis;
  fft_spectral_analysis?: FFTSpectralAnalysis;
  face_boundary_analysis?: FaceBoundaryAnalysis;
  error_level_analysis?: ErrorLevelAnalysisData;
  anomaly_level: 'low' | 'moderate' | 'elevated';
  observed_anomalies: string[];
  limitations: string;
}

export interface TranscriptComparison {
  status: string;
  gemini_transcript?: string;
  whisper_transcript?: string;
  similarity_score?: number;
  similarity_status?: string;
  comparable_reason?: string;
  discrepancies: string[];
  timestamp_notes?: string;
}

export interface AcousticAnomalyAnalysis {
  status: string;
  cadence_observations?: string;
  robotic_artifacts?: string;
  room_acoustics_consistent?: boolean;
  anomaly_indicators: string[];
}

export interface VoiceCloneAssessment {
  status: string;
  disclaimer: string;
  observations: string[];
}

export interface GeminiAudioForensics {
  status: string;
  reason?: string;
  methodology: string;
  detector_provenance: string;
  model_used?: string;
  transcript_comparison?: TranscriptComparison;
  acoustic_anomaly_analysis?: AcousticAnomalyAnalysis;
  voice_clone_assessment?: VoiceCloneAssessment;
  limitations: string;
}

export interface SuspiciousSegment {
  start_time: number;
  end_time: number;
  anomaly_type: string;
  description: string;
  severity: 'low' | 'moderate' | 'high';
}

export interface EvidenceItem {
  detector: string;
  signal: string;
  severity: 'low' | 'moderate' | 'high';
  timestamp?: number;
  details: string;
}

export interface ProvenanceData {
  status: 'verified' | 'invalid' | 'missing' | 'unsupported';
  sha256?: string;
  is_valid: boolean;
  generator?: string;
  issuer?: string;
  actions?: Array<{ action: string; softwareAgent?: string }>;
  disclaimer: string;
}

export interface UnifiedAuthenticityReport {
  classification:
    | 'LIKELY_AI_GENERATED'
    | 'POTENTIALLY_AI_EDITED'
    | 'POTENTIALLY_FACIAL_MANIPULATION'
    | 'POTENTIALLY_SYNTHETIC_SPEECH'
    | 'CONVENTIONAL_EDITING_DETECTED'
    | 'INCONCLUSIVE'
    | 'AUTHENTIC_NO_ANOMALIES_DETECTED';
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNCERTAIN';
  reason: string;
  evidence: EvidenceItem[];
  suspicious_segments: SuspiciousSegment[];
  provenance: ProvenanceData;
  checks_performed: string[];
  checks_unavailable: Array<{ check: string; reason: string }>;
  limitations: string[];
  model_versions: Record<string, string>;
}

export interface ForensicsReport {
  deepfake_probability: number;
  voice_clone_probability: number;
  scene_consistency_score: number;
  video_integrity_score?: number;
  audio_integrity_score?: number;
  metadata_integrity_score?: number;
  red_flag_count: number;
  is_synthetic: boolean;
  detector_status?: string;
  summary: string;
  red_flags?: string[];
  forensics_veto?: {
    veto: boolean;
    reason: string;
    detector?: string;
  };
  technical_audio?: TechnicalAudio;
  deepfake_analysis?: DeepfakeAnalysis;
  geolocation?: GeolocationData;
  opencv_visual?: OpenCVVisualForensics;
  gemini_audio?: GeminiAudioForensics;
  provenance?: ProvenanceData;
  unified_authenticity?: UnifiedAuthenticityReport;
}

export interface NewsResult {
  title: string;
  url: string;
  domain: string;
  domain_trust: 'high' | 'medium' | 'low';
  published_date?: string;
  snippet?: string;
}

export interface SocialResult {
  title: string;
  url: string;
  domain: string;
  platform?: string;
  snippet?: string;
}

export interface GeoVerificationItem {
  location: string;
  source: string;
  url: string;
  domain_trust: 'high' | 'medium' | 'low';
  geo_supports?: boolean;
  geo_contradicts?: boolean;
}

export interface GoogleFactCheckItem {
  title: string;
  review_url: string;
  publisher: string;
  rating: string;
  is_debunk: boolean;
}

export interface OSINTReport {
  summary: string;
  contradiction_count: number;
  support_count: number;
  osint_score?: number;
  recycled_footage_detected?: boolean;
  potential_recycled_content?: boolean;
  osint_veto?: {
    veto: boolean;
    reason: string;
  };
  news_verification?: {
    total_news_found: number;
    high_trust_sources: number;
    news_results: NewsResult[];
  };
  social_signals?: {
    total_social_found: number;
    social_results: SocialResult[];
    manipulation_signals?: string[];
  };
  geo_verification?: {
    geo_summary?: string;
    geo_verifications: GeoVerificationItem[];
  };
  timestamp_verification?: {
    timestamp_summary?: string;
    timestamp_issues?: string[];
  };
  weather_verification?: {
    weather_claims_found?: string[];
  };
  google_factcheck?: {
    fact_checks_found: GoogleFactCheckItem[];
    debunked_count: number;
    manipulated_count?: number;
  };
}

export interface DMClassification {
  category: string;
  suspicion_score: number;
  confidence: number;
}

export interface DMCluster {
  cluster_id: string | number;
  size: number;
  representative_claim?: string;
  dominant_verdict: string;
}

export interface DMOutlier {
  claim_text: string;
  anomaly_severity: 'low' | 'medium' | 'high';
  reasons: string[];
}

export interface DMAssociationRule {
  antecedent: string;
  consequent: string;
  support: number;
  confidence: number;
  lift: number;
}

export interface DMPattern {
  pattern: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  indicators?: string[];
}

export interface DMTemplateMatch {
  template: string;
  match_type: string;
  similarity_score: number;
  exact_match?: boolean;
}

export interface DataMiningReport {
  summary: string;
  dm_score?: number;
  calibrated_claims_count: number;
  classification?: DMClassification;
  dm_veto?: {
    veto: boolean;
    verdict?: string;
    reason: string;
  };
  clustering?: {
    cluster_count: number;
    clusters: DMCluster[];
  };
  outlier_detection?: {
    outlier_count: number;
    outliers: DMOutlier[];
  };
  association_rules?: {
    total_rules: number;
    strong_rules: DMAssociationRule[];
  };
  pattern_mining?: {
    pattern_count: number;
    patterns: DMPattern[];
  };
  similarity_analysis?: {
    total_matches: number;
    template_matches: DMTemplateMatch[];
  };
}

export interface VerdictBreakdown {
  true: number;
  false: number;
  misleading: number;
  unverifiable: number;
  total: number;
  veto_applied?: {
    type: string;
    reason: string;
  };
}
