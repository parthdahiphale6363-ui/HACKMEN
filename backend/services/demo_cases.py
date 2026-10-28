"""
demo_cases.py — Curated Multimodal Verification Case Studies
Provides rich, production-grade test cases for instant demonstration
and automated evaluation of TruthLens AI capabilities.
"""

from typing import Dict, Any, List

DEMO_CASES: Dict[str, Dict[str, Any]] = {
    "deepfake_scam": {
        "id": "demo-deepfake-elon-scam",
        "title": "AI Deepfake Impersonation & Crypto Scam",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "platform": "youtube",
        "overall_verdict": "High Probability Deepfake & Financial Fraud Scheme",
        "final_verdict_category": "Deepfake Video",
        "overall_confidence": 94.0,
        "video_score": 22.0,
        "audio_score": 14.0,
        "metadata_score": 38.0,
        "osint_score": 12.0,
        "dm_score": 18.0,
        "verdict_breakdown": {
            "true": 0,
            "false": 3,
            "misleading": 1,
            "unverifiable": 0,
            "total": 4,
            "veto_applied": {
                "veto": True,
                "type": "forensics_synthetic_veto",
                "reason": "Severe synthetic voice cloning (94%) and temporal facial boundary warping detected — overall verdict capped to DEEPFAKE / FALSE."
            }
        },
        "transcript": [
            {"start": 0.0, "end": 6.5, "text": "Hello everyone. Today our team is officially launching a massive $10,000 crypto giveaway for every viewer."},
            {"start": 6.8, "end": 14.2, "text": "The Federal Reserve and Tesla have collaborated to build this automated quantum wealth distribution platform."},
            {"start": 14.5, "end": 21.0, "text": "Simply scan the QR code on screen and deposit 0.1 Bitcoin to verify your identity and receive the return immediately."},
            {"start": 21.5, "end": 28.0, "text": "This technology is legally guaranteed under the new emergency executive financial order."}
        ],
        "claims": [
            {
                "claim": {
                    "id": "claim-df-1",
                    "raw_text": "Tesla and Elon Musk are giving away $10,000 in cryptocurrency to all viewers",
                    "normalized_text": "Tesla and Elon Musk are giving away $10,000 in cryptocurrency to all viewers",
                    "language": "en",
                    "timestamp_in_video": 3.0,
                    "confidence": 0.98,
                    "time_str": "00:03"
                },
                "verdict": {
                    "label": "false",
                    "confidence": 0.98,
                    "summary": "Debunked impersonation scam. Neither Tesla nor Musk operate any cryptocurrency giveaway.",
                    "reasoning": "Standard social media crypto advance-fee scam utilizing cloned audio and deepfaked speech. Confirmed false by multiple IFCN fact-checkers.",
                    "evidence": [
                        {
                            "source_title": "Fact Check: Elon Musk is not giving away Bitcoin on YouTube",
                            "source_url": "https://www.reuters.com/fact-check/elon-musk-bitcoin-scam",
                            "domain": "reuters.com",
                            "domain_trust": "high",
                            "publication_date": "2026-03-12",
                            "snippet": "Videos claiming Elon Musk is offering Bitcoin giveaways are fraudulent scams using AI voice synthesis and manipulated archival footage.",
                            "supports_claim": False,
                            "relevance_score": 0.96
                        },
                        {
                            "source_title": "FactCheck.org: Viral Deepfake Musk Crypto Schemes Multiply",
                            "source_url": "https://www.factcheck.org/musk-crypto-warning",
                            "domain": "factcheck.org",
                            "domain_trust": "high",
                            "publication_date": "2026-04-05",
                            "snippet": "No legitimate organization requires a deposit in order to give away free funds. The footage has been manipulated.",
                            "supports_claim": False,
                            "relevance_score": 0.92
                        }
                    ],
                    "search_runs": [
                        {
                            "query": "Elon Musk $10,000 crypto giveaway Tesla",
                            "source_type": "NewsAPI",
                            "results_found": 8,
                            "top_domain": "reuters.com",
                            "trust_level": "high",
                            "stance": "contradicts"
                        }
                    ],
                    "llm_checks": [
                        {"agent": "Forensic Voice Classifier", "role": "Acoustic Biomarkers", "finding": "Synthetic pitch jitter > 8.4 st. Match with RVC voice cloning model.", "passed": False},
                        {"agent": "IFCN Cross-Check", "role": "FactCheck Verification", "finding": "Certified false by Reuters and FactCheck.org.", "passed": False}
                    ],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 2,
                        "sources_accepted": 2,
                        "sources_blocked": 0,
                        "consensus_score": 0.98,
                        "cross_platform_hits": 4,
                        "llm_rounds": 2,
                        "critic_rejections": 0
                    }
                }
            },
            {
                "claim": {
                    "id": "claim-df-2",
                    "raw_text": "The Federal Reserve partnered with Tesla on an automated quantum wealth platform",
                    "normalized_text": "Federal Reserve partnered with Tesla on quantum wealth platform",
                    "language": "en",
                    "timestamp_in_video": 10.0,
                    "confidence": 0.95,
                    "time_str": "00:10"
                },
                "verdict": {
                    "label": "false",
                    "confidence": 0.96,
                    "summary": "Fabricated claim. The Federal Reserve has never partnered with private EV companies on crypto schemes.",
                    "reasoning": "Federal Reserve public records and press releases confirm zero association with quantum trading or crypto partnerships.",
                    "evidence": [
                        {
                            "source_title": "Federal Reserve Press Release — Consumer Fraud Alert",
                            "source_url": "https://www.federalreserve.gov/fraud-alerts.htm",
                            "domain": "federalreserve.gov",
                            "domain_trust": "high",
                            "publication_date": "2026-01-20",
                            "snippet": "The Federal Reserve does not offer investment platforms or endorse private cryptocurrency initiatives.",
                            "supports_claim": False,
                            "relevance_score": 0.94
                        }
                    ],
                    "search_runs": [
                        {"query": "Federal Reserve Tesla quantum platform", "source_type": "DuckDuckGo", "results_found": 5, "top_domain": "federalreserve.gov", "trust_level": "high", "stance": "contradicts"}
                    ],
                    "llm_checks": [
                        {"agent": "Entity Validator", "role": "Government Record Verification", "finding": "No such platform or executive order exists.", "passed": False}
                    ],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 1,
                        "sources_accepted": 1,
                        "sources_blocked": 0,
                        "consensus_score": 0.96,
                        "cross_platform_hits": 2,
                        "llm_rounds": 1,
                        "critic_rejections": 0
                    }
                }
            }
        ],
        "forensics": {
            "deepfake_probability": 0.91,
            "voice_clone_probability": 0.94,
            "scene_consistency_score": 0.35,
            "red_flag_count": 5,
            "is_synthetic": True,
            "technical_audio": {
                "audio_stream_available": True,
                "codec_name": "aac",
                "sample_rate": 44100,
                "channels": 2,
                "bit_rate_kbps": 128,
                "silence_burst_count": 7
            },
            "forensics_veto": {
                "veto": True,
                "reason": "Synthetic speech cloning (94%) with ELA boundary compression anomaly detected."
            },
            "opencv_visual": {
                "status": "assessed",
                "methodology": "OpenCV keyframe extraction (1 fps) with 2D FFT spectral profiling, Laplacian focus variance, Haar face boundary analysis, and scene difference metrics.",
                "detector_provenance": "OpenCV 5.0 (cv2) + NumPy signal processing",
                "frames_analyzed": 28,
                "video_duration_seconds": 28.0,
                "video_resolution": "640x360",
                "scene_cuts": {
                    "count": 0,
                    "abrupt_transitions": 2,
                    "cut_timestamps": [],
                    "mean_frame_difference": 0.12
                },
                "laplacian_blur": {
                    "mean_variance": 18.4,
                    "variance_stability": 0.32,
                    "min_variance": 8.2,
                    "max_variance": 42.1,
                    "flags": ["Low overall frame sharpness — heavy compression smoothing", "High focus instability observed across sampled frames"]
                },
                "fft_spectral_analysis": {
                    "high_frequency_ratio": 0.0092,
                    "spectral_regularity": 0.44,
                    "anomaly_indicators": ["Abnormally suppressed high-frequency spectrum (excessive smoothing/upsampling)", "Asymmetric 2D frequency distribution detected"]
                },
                "face_boundary_analysis": {
                    "status": "assessed",
                    "faces_detected": True,
                    "total_faces_tracked": 28,
                    "mean_boundary_blur_ratio": 0.28,
                    "jitter_score": 78.4,
                    "anomaly_indicators": ["Soft/blurry facial region superimposed on sharper background", "High facial centroid displacement jitter (78.4px variance)"]
                },
                "error_level_analysis": {
                    "status": "assessed",
                    "applied": True,
                    "mean_error": 14.8,
                    "max_error": 68.2,
                    "variance": 112.5,
                    "limitations": "ELA highlights re-compression differences across uniform surfaces, but is sensitive to natural edge contrast and historical re-encoding. It is an anomaly indicator, not proof of splicing."
                },
                "anomaly_level": "elevated",
                "observed_anomalies": [
                    "Soft/blurry facial region superimposed on sharper background",
                    "High facial centroid displacement jitter (78.4px variance)",
                    "Abnormally suppressed high-frequency spectrum (excessive smoothing/upsampling)"
                ],
                "limitations": "Visual forensic indicators measure statistical, boundary, and frequency properties. They indicate anomalies for analyst review and do not constitute deterministic proof of synthetic media generation."
            },
            "gemini_audio": {
                "status": "assessed",
                "methodology": "Google GenAI Multimodal native audio analysis with token-level transcript cross-verification and acoustic anomaly audit.",
                "detector_provenance": "Google GenAI SDK (gemini-2.5-flash)",
                "model_used": "gemini-2.5-flash",
                "transcript_comparison": {
                    "status": "assessed",
                    "gemini_transcript": "Hello everyone. Today our team is officially launching a massive ten thousand dollar crypto giveaway...",
                    "whisper_transcript": "Hello everyone. Today our team is officially launching a massive $10,000 crypto giveaway...",
                    "similarity_score": 0.94,
                    "discrepancies": ["Verbal currency expansion differences"],
                    "timestamp_notes": "Continuous monophonic cadence without organic breath intakes."
                },
                "acoustic_anomaly_analysis": {
                    "status": "assessed",
                    "cadence_observations": "Unnaturally flat prosody with zero breathing pauses between complex clauses.",
                    "robotic_artifacts": "Phase clipping and metallic resonant overtone characteristic of RVC voice models.",
                    "room_acoustics_consistent": False,
                    "anomaly_indicators": ["Metallic overtone distortion", "Missing inhalation acoustic bursts"]
                },
                "voice_clone_assessment": {
                    "status": "assessed",
                    "disclaimer": "No validated acoustic biometric classifier available. Observations represent semantic/auditory cues, not deterministic clone proof.",
                    "observations": ["Flat inflection slope matches neural text-to-speech synthetic profile."]
                },
                "limitations": "Gemini multimodal audio inspection provides semantic and auditory anomaly reasoning. It does not replace biometric acoustic analysis or cryptographic provenance verification."
            },
            "summary": "High-confidence deepfake manipulation. Video exhibits unnatural lip-sync boundary warping and cloned neural acoustic profile.",
            "provenance": {
                "status": "missing",
                "sha256": "8f4a19b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
                "is_valid": False,
                "generator": None,
                "issuer": None,
                "issued_time": None,
                "tamper_detected": False,
                "details": "No C2PA manifest found in container"
            },
            "unified_authenticity": {
                "verdict": "POTENTIALLY_FACIAL_MANIPULATION",
                "confidence_level": "HIGH",
                "reason": "Multimodal biometric mismatch: severe facial centroid displacement jitter (78.4px) and spectral high-frequency suppression.",
                "evidence": [
                    {"detector": "OpenCV Visual", "signal": "Facial boundary blur ratio anomaly", "severity": "high", "timestamp": 4.0, "details": "Soft facial region superimposed on sharper background"},
                    {"detector": "Gemini Audio", "signal": "Acoustic prosody anomaly", "severity": "moderate", "timestamp": 6.8, "details": "Phase clipping and flat inflection slope characteristic of synthetic voice"}
                ],
                "suspicious_segments": [
                    {"start_time": 2.0, "end_time": 8.0, "anomaly_type": "facial_boundary_warping", "description": "Temporal face boundary blur and centroid jitter", "severity": "high"}
                ],
                "provenance": {
                    "status": "missing",
                    "sha256": "8f4a19b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
                    "is_valid": False,
                    "generator": None,
                    "issuer": None,
                    "issued_time": None,
                    "tamper_detected": False,
                    "details": "No C2PA manifest found in container"
                },
                "checks_performed": ["OpenCV Visual (FFT, Laplacian, Haar)", "Gemini Multimodal Audio", "C2PA Provenance Manifest", "FFmpeg Acoustic Profiles"],
                "checks_unavailable": [],
                "limitations": ["Visual and acoustic heuristics indicate statistical anomalies and cannot guarantee deterministic proof."],
                "model_versions": {"opencv": "4.10", "c2pa": "0.38.0", "gemini": "gemini-2.5-flash"}
            }
        },
        "osint": {
            "google_factcheck": {
                "fact_checks_found": [
                    {
                        "publisher": "Reuters Fact Check",
                        "review_url": "https://www.reuters.com/fact-check/elon-musk-bitcoin-scam",
                        "title": "Altered video depicts fake Elon Musk cryptocurrency distribution",
                        "rating": "False",
                        "is_debunk": True
                    },
                    {
                        "publisher": "PolitiFact",
                        "review_url": "https://www.politifact.com/factchecks/fake-crypto-giveaway",
                        "title": "Viral Facebook & YouTube crypto giveaway video is deepfaked",
                        "rating": "Pants on Fire",
                        "is_debunk": True
                    }
                ],
                "debunked_count": 2,
                "manipulated_count": 0,
                "verified_true_count": 0,
                "total_reviews": 2,
                "factcheck_summary": "Google Fact Check API: Found 2 authoritative reviews. Debunked: 2, Manipulated: 0, True: 0."
            },
            "news_summary": "Major international news and security agencies have repeatedly issued warnings regarding AI-generated Elon Musk crypto scams.",
            "total_news_found": 12,
            "high_trust_sources": 8,
            "contradiction_count": 6,
            "support_count": 0
        },
        "dm_report": {
            "classification": {
                "category": "Deepfake Video",
                "confidence": 0.95,
                "suspicion_score": 0.92
            },
            "dm_veto": {
                "veto": True,
                "reason": "High-density scam indicators (Giveaway, QR deposit, Instant Wealth) combined with neural voice clone markers."
            },
            "calibrated_claims_count": 2,
            "clustering": {
                "cluster_count": 2,
                "clusters": [
                    {"cluster_id": 1, "size": 3, "dominant_verdict": "false", "representative_claim": "Elon Musk Tesla cryptocurrency giveaway scam"}
                ]
            },
            "pattern_mining": {
                "pattern_count": 3,
                "patterns": [
                    {"pattern": "High-Urgency Financial Bait", "severity": "high", "description": "Demands immediate crypto deposit with guarantee of return.", "indicators": ["giveaway", "deposit", "immediately", "wealth"]},
                    {"pattern": "Institutional Authority Hijacking", "severity": "high", "description": "Falsely attributes legitimacy to Federal Reserve and executive orders.", "indicators": ["Federal Reserve", "executive order", "guaranteed"]}
                ]
            },
            "outlier_detection": {"outlier_count": 1, "outliers": ["$10,000 instant return on 0.1 BTC deposit"]},
            "association_rules": {"total_rules": 4},
            "similarity_analysis": {"total_matches": 3}
        }
    },

    "science_myths": {
        "id": "demo-viral-science-myths",
        "title": "Viral Human Biology & Behavioral Psychology",
        "video_url": "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
        "platform": "youtube",
        "overall_verdict": "Verified Legitimate Scientific Discoveries with Nuanced Context",
        "final_verdict_category": "Genuine Video",
        "overall_confidence": 89.0,
        "video_score": 94.0,
        "audio_score": 96.0,
        "metadata_score": 92.0,
        "osint_score": 88.0,
        "dm_score": 85.0,
        "verdict_breakdown": {
            "true": 2,
            "false": 0,
            "misleading": 1,
            "unverifiable": 0,
            "total": 3
        },
        "transcript": [
            {"start": 0.0, "end": 7.0, "text": "Recent evolutionary biology reveals that human saliva contains the exact genetic pathways capable of producing venom."},
            {"start": 7.5, "end": 15.0, "text": "In behavioral psychology experiments, humans consistently demonstrated greater empathy towards pet dogs than unfamiliar adult strangers."},
            {"start": 15.5, "end": 22.0, "text": "Under severe starvation conditions, the human brain begins consuming its own cellular components via autophagy to maintain consciousness."}
        ],
        "claims": [
            {
                "claim": {
                    "id": "claim-sc-1",
                    "raw_text": "Humans are technically capable of producing venom due to shared genetic architecture",
                    "normalized_text": "Humans have genetic capability to produce venom",
                    "language": "en",
                    "timestamp_in_video": 3.0,
                    "confidence": 0.91,
                    "time_str": "00:03"
                },
                "verdict": {
                    "label": "true",
                    "confidence": 0.91,
                    "summary": "Confirmed by genomics. Humans share the foundational kallikrein gene family found in venomous snakes and mammals.",
                    "reasoning": "A 2021 study published in PNAS demonstrated that mammalian salivary glands share the flexible genetic foundation that venomous animals co-opted to produce toxins.",
                    "evidence": [
                        {
                            "source_title": "PNAS: An ancient, conserved gene regulatory network underlies venom evolution",
                            "source_url": "https://www.pnas.org/doi/10.1073/pnas.2026672118",
                            "domain": "pnas.org",
                            "domain_trust": "high",
                            "publication_date": "2021-04-06",
                            "snippet": "Researchers discovered that amniotes, including humans and mice, possess the genetic architecture necessary to produce venom, centered around kallikrein proteins.",
                            "supports_claim": True,
                            "relevance_score": 0.95
                        },
                        {
                            "source_title": "Live Science: Humans Have the Toolkit to Produce Venom",
                            "source_url": "https://www.livescience.com/humans-can-produce-venom.html",
                            "domain": "livescience.com",
                            "domain_trust": "high",
                            "publication_date": "2021-04-07",
                            "snippet": "Humans possess the genes for venom production, though our evolutionary trajectory focused on complex salivary digestion rather than toxin delivery.",
                            "supports_claim": True,
                            "relevance_score": 0.89
                        }
                    ],
                    "search_runs": [
                        {"query": "humans produce venom biology kallikrein", "source_type": "NewsAPI", "results_found": 6, "top_domain": "pnas.org", "trust_level": "high", "stance": "supports"}
                    ],
                    "llm_checks": [
                        {"agent": "Genomics Verification", "role": "Peer-Reviewed Literature", "finding": "Confirmed by PNAS 2021 publication.", "passed": True}
                    ],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 2,
                        "sources_accepted": 2,
                        "sources_blocked": 0,
                        "consensus_score": 0.91,
                        "cross_platform_hits": 3,
                        "llm_rounds": 1,
                        "critic_rejections": 0
                    }
                }
            },
            {
                "claim": {
                    "id": "claim-sc-2",
                    "raw_text": "People will prioritize saving their pet dog over an adult stranger in an emergency",
                    "normalized_text": "People prioritize pet dog over unfamiliar stranger in danger",
                    "language": "en",
                    "timestamp_in_video": 11.0,
                    "confidence": 0.88,
                    "time_str": "00:11"
                },
                "verdict": {
                    "label": "true",
                    "confidence": 0.88,
                    "summary": "Empirically supported by sociology & evolutionary psychology research.",
                    "reasoning": "Studies in Anthrozoös and Northeastern University documented that respondents feel equal or greater empathy toward dogs compared to unfamiliar adult humans due to perceived innocence and vulnerability.",
                    "evidence": [
                        {
                            "source_title": "Anthrozoös: Human Empathy Toward Dogs vs Human Strangers",
                            "source_url": "https://www.tandfonline.com/doi/abs/10.2752/175303713X13788107980838",
                            "domain": "tandfonline.com",
                            "domain_trust": "high",
                            "publication_date": "2020-08-15",
                            "snippet": "Subjects reported significantly higher distress and willingness to assist battered dogs compared to adult human victims.",
                            "supports_claim": True,
                            "relevance_score": 0.91
                        }
                    ],
                    "search_runs": [
                        {"query": "empathy dogs vs human strangers study", "source_type": "Wikipedia", "results_found": 4, "top_domain": "en.wikipedia.org", "trust_level": "high", "stance": "supports"}
                    ],
                    "llm_checks": [
                        {"agent": "Psychology Corpus Check", "role": "Empirical Review", "finding": "Consistent with published Anthrozoös findings.", "passed": True}
                    ],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 1,
                        "sources_accepted": 1,
                        "sources_blocked": 0,
                        "consensus_score": 0.88,
                        "cross_platform_hits": 1,
                        "llm_rounds": 1,
                        "critic_rejections": 0
                    }
                }
            },
            {
                "claim": {
                    "id": "claim-sc-3",
                    "raw_text": "The human brain literally eats itself during starvation",
                    "normalized_text": "Brain consumes its own cells via autophagy in starvation",
                    "language": "en",
                    "timestamp_in_video": 18.0,
                    "confidence": 0.82,
                    "time_str": "00:18"
                },
                "verdict": {
                    "label": "misleading",
                    "confidence": 0.84,
                    "summary": "Technically refers to cellular autophagy, not macroscopic cannibalization of the organ.",
                    "reasoning": "Under starvation, hypothalamic neurons upregulate autophagy (self-eating) to recycle lipids into fatty acids, which is a protective survival mechanism rather than tissue destruction.",
                    "evidence": [
                        {
                            "source_title": "Cell Metabolism: Starvation-Induced Autophagy in Hypothalamic Neurons",
                            "source_url": "https://www.cell.com/cell-metabolism/fulltext/S1550-4131(11)00249-1",
                            "domain": "cell.com",
                            "domain_trust": "high",
                            "publication_date": "2019-02-10",
                            "snippet": "Autophagy in hypothalamic AgRP neurons regulates food intake and energy balance during nutrient deprivation.",
                            "supports_claim": True,
                            "relevance_score": 0.88
                        }
                    ],
                    "search_runs": [
                        {"query": "starvation brain autophagy hypothalamic", "source_type": "NewsAPI", "results_found": 5, "top_domain": "cell.com", "trust_level": "high", "stance": "neutral"}
                    ],
                    "llm_checks": [
                        {"agent": "Medical Nuance Engine", "role": "Biochemical Precision", "finding": "Sensationalized phrasing of physiological cellular autophagy.", "passed": False}
                    ],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 1,
                        "sources_accepted": 1,
                        "sources_blocked": 0,
                        "consensus_score": 0.84,
                        "cross_platform_hits": 2,
                        "llm_rounds": 1,
                        "critic_rejections": 0
                    }
                }
            }
        ],
        "forensics": {
            "deepfake_probability": 0.05,
            "voice_clone_probability": 0.04,
            "scene_consistency_score": 0.94,
            "red_flag_count": 0,
            "is_synthetic": False,
            "technical_audio": {
                "audio_stream_available": True,
                "codec_name": "aac",
                "sample_rate": 48000,
                "channels": 2,
                "bit_rate_kbps": 192,
                "silence_burst_count": 1
            },
            "summary": "Authentic organic media. Normal spectral harmonics, natural vocal timbre, zero synthetic splicing artifacts.",
            "provenance": {
                "status": "verified",
                "sha256": "4a7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
                "is_valid": True,
                "generator": "Sony ILCE-7SM3 Camera Hardware Root",
                "issuer": "Sony Electronics C2PA Root CA",
                "issued_time": "2026-03-10T14:22:00Z",
                "tamper_detected": False,
                "details": "Verified C2PA hardware manifest with valid signature"
            },
            "unified_authenticity": {
                "verdict": "AUTHENTIC_NO_ANOMALIES_DETECTED",
                "confidence_level": "HIGH",
                "reason": "Cryptographically verified C2PA provenance with zero acoustic, facial, or spectral anomalies.",
                "evidence": [
                    {"detector": "C2PA Provenance", "signal": "Hardware cryptographic signature valid", "severity": "low", "details": "Signed by Sony Electronics C2PA Root CA"}
                ],
                "suspicious_segments": [],
                "provenance": {
                    "status": "verified",
                    "sha256": "4a7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
                    "is_valid": True,
                    "generator": "Sony ILCE-7SM3 Camera Hardware Root",
                    "issuer": "Sony Electronics C2PA Root CA",
                    "issued_time": "2026-03-10T14:22:00Z",
                    "tamper_detected": False,
                    "details": "Verified C2PA hardware manifest with valid signature"
                },
                "checks_performed": ["C2PA Provenance Verification", "OpenCV Visual Forensics", "FFmpeg Acoustic Spectrum"],
                "checks_unavailable": [],
                "limitations": ["C2PA verifies capture provenance; subsequent analog re-recording cannot be completely eliminated."],
                "model_versions": {"c2pa": "0.38.0", "opencv": "4.10"}
            }
        },
        "osint": {
            "google_factcheck": {
                "fact_checks_found": [],
                "debunked_count": 0,
                "manipulated_count": 0,
                "verified_true_count": 0,
                "total_reviews": 0,
                "factcheck_summary": "No debunks in Google Fact Check Tools database — claims are verified by academic peer-reviewed biology."
            },
            "news_summary": "Peer-reviewed scientific journals (PNAS, Cell Metabolism, Anthrozoös) substantiate the core biological findings.",
            "total_news_found": 15,
            "high_trust_sources": 12,
            "contradiction_count": 0,
            "support_count": 8
        },
        "dm_report": {
            "classification": {
                "category": "Genuine Video",
                "confidence": 0.92,
                "suspicion_score": 0.08
            },
            "calibrated_claims_count": 1,
            "clustering": {
                "cluster_count": 2,
                "clusters": [
                    {"cluster_id": 1, "size": 2, "dominant_verdict": "true", "representative_claim": "Evolutionary biology and human genetics"},
                    {"cluster_id": 2, "size": 1, "dominant_verdict": "misleading", "representative_claim": "Nutrient deprivation autophagy mechanisms"}
                ]
            },
            "pattern_mining": {
                "pattern_count": 1,
                "patterns": [
                    {"pattern": "Sensationalized Scientific Hyperbole", "severity": "medium", "description": "Phrasing cellular autophagy as 'brain eating itself'.", "indicators": ["eats itself", "starvation"]}
                ]
            },
            "outlier_detection": {"outlier_count": 0, "outliers": []},
            "association_rules": {"total_rules": 2},
            "similarity_analysis": {"total_matches": 0}
        }
    },

    "geopolitical_disinfo": {
        "id": "demo-geopolitical-disinfo",
        "title": "Recycled Conflict Video & Astroturfed Bot Signals",
        "video_url": "https://www.youtube.com/watch?v=21X5lGlDOfg",
        "platform": "youtube",
        "overall_verdict": "Recycled Out-of-Context Media with Coordinated Bot Disinformation",
        "final_verdict_category": "Manipulated Out of Context",
        "overall_confidence": 92.0,
        "video_score": 45.0,
        "audio_score": 58.0,
        "metadata_score": 28.0,
        "osint_score": 22.0,
        "dm_score": 19.0,
        "verdict_breakdown": {
            "true": 0,
            "false": 2,
            "misleading": 1,
            "unverifiable": 0,
            "total": 3,
            "veto_applied": {
                "veto": True,
                "type": "osint_google_factcheck_veto",
                "reason": "Directly debunked by certified IFCN fact-checkers — footage is a 2020 military simulator game (ARMA 3) recycled as active breaking combat."
            }
        },
        "transcript": [
            {"start": 0.0, "end": 6.0, "text": "Breaking news: Live combat footage showing anti-aircraft batteries shooting down enemy fighter jet over capital city."},
            {"start": 6.5, "end": 13.0, "text": "Defense Ministry officials have confirmed the pilot was captured and international military assistance has been triggered."},
            {"start": 13.5, "end": 20.0, "text": "Over 500,000 citizens are currently evacuating under immediate emergency air raid sirens."}
        ],
        "claims": [
            {
                "claim": {
                    "id": "claim-geo-1",
                    "raw_text": "Video shows real live anti-aircraft combat over capital city today",
                    "normalized_text": "Footage depicts live combat shooting down fighter jet",
                    "language": "en",
                    "timestamp_in_video": 2.0,
                    "confidence": 0.99,
                    "time_str": "00:02"
                },
                "verdict": {
                    "label": "false",
                    "confidence": 0.99,
                    "summary": "Debunked recycled video game simulation. Footage originates from video game ARMA 3.",
                    "reasoning": "Reverse image search and IFCN fact checks confirm this clip is virtual gameplay from Bohemia Interactive's ARMA 3, widely recycled during conflict events.",
                    "evidence": [
                        {
                            "source_title": "Associated Press: Video game clip falsely shared as combat footage",
                            "source_url": "https://apnews.com/article/fact-check-arma-video-game",
                            "domain": "apnews.com",
                            "domain_trust": "high",
                            "publication_date": "2026-02-14",
                            "snippet": "Footage claiming to show military anti-aircraft defenses is computer-generated gameplay from the simulator ARMA 3.",
                            "supports_claim": False,
                            "relevance_score": 0.98
                        },
                        {
                            "source_title": "BBC Verify: How video game clips fool social media during breaking news",
                            "source_url": "https://www.bbc.com/news/world-arma-simulation-check",
                            "domain": "bbc.com",
                            "domain_trust": "high",
                            "publication_date": "2026-02-15",
                            "snippet": "Visual anomalies including repeating tracer rounds and polygon textures indicate computer graphics rather than real footage.",
                            "supports_claim": False,
                            "relevance_score": 0.94
                        }
                    ],
                    "search_runs": [
                        {"query": "anti aircraft video game arma simulation footage", "source_type": "Google FactCheck", "results_found": 7, "top_domain": "apnews.com", "trust_level": "high", "stance": "contradicts"}
                    ],
                    "llm_checks": [
                        {"agent": "Reverse Video Forensics", "role": "Visual Matcher", "finding": "100% texture match with Bohemia Interactive simulator asset library.", "passed": False}
                    ],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 2,
                        "sources_accepted": 2,
                        "sources_blocked": 0,
                        "consensus_score": 0.99,
                        "cross_platform_hits": 5,
                        "llm_rounds": 1,
                        "critic_rejections": 0
                    }
                }
            }
        ],
        "forensics": {
            "deepfake_probability": 0.42,
            "voice_clone_probability": 0.28,
            "scene_consistency_score": 0.45,
            "red_flag_count": 4,
            "is_synthetic": False,
            "technical_audio": {
                "audio_stream_available": True,
                "codec_name": "aac",
                "sample_rate": 44100,
                "channels": 1,
                "bit_rate_kbps": 96,
                "silence_burst_count": 4
            },
            "summary": "Out-of-context computer graphics. Low-resolution compression artifacts intentionally applied to disguise 3D gaming textures.",
            "provenance": {
                "status": "missing",
                "sha256": "1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d",
                "is_valid": False,
                "generator": None,
                "issuer": None,
                "issued_time": None,
                "tamper_detected": False,
                "details": "No C2PA manifest found; video container metadata shows capture re-encoding"
            },
            "unified_authenticity": {
                "verdict": "CONVENTIONAL_EDITING_DETECTED",
                "confidence_level": "HIGH",
                "reason": "Recycled 3D computer graphics simulation with intentional resolution downscaling and spliced audio bursts.",
                "evidence": [
                    {"detector": "OpenCV Visual", "signal": "Abrupt scene transitions without organic motion blur", "severity": "moderate", "details": "4 scene cuts with unnatural polygonal edge contrast"},
                    {"detector": "Acoustic Spectrum", "signal": "Discontinuous audio spliced bursts", "severity": "moderate", "details": "Recurrent spliced siren track over ambient noise"}
                ],
                "suspicious_segments": [
                    {"start_time": 0.0, "end_time": 12.0, "anomaly_type": "cgi_rendering_splicing", "description": "3D engine rendering artifacts with downsampled resolution", "severity": "moderate"}
                ],
                "provenance": {
                    "status": "missing",
                    "sha256": "1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d",
                    "is_valid": False,
                    "generator": None,
                    "issuer": None,
                    "issued_time": None,
                    "tamper_detected": False,
                    "details": "No C2PA manifest found; video container metadata shows capture re-encoding"
                },
                "checks_performed": ["OpenCV Visual Scene Analysis", "FFmpeg Acoustic Profiles", "C2PA Provenance Manifest"],
                "checks_unavailable": [],
                "limitations": ["Visual scene difference indicates abrupt structural shifts consistent with synthetic gameplay cuts."],
                "model_versions": {"opencv": "4.10", "c2pa": "0.38.0"}
            }
        },
        "osint": {
            "google_factcheck": {
                "fact_checks_found": [
                    {
                        "publisher": "Associated Press",
                        "review_url": "https://apnews.com/article/fact-check-arma-video-game",
                        "title": "Video game footage miscaptioned as genuine combat",
                        "rating": "False",
                        "is_debunk": True
                    },
                    {
                        "publisher": "Boom Live",
                        "review_url": "https://www.boomlive.in/fact-check/arma-3-gameplay",
                        "title": "ARMA 3 gameplay shared as live airstrikes",
                        "rating": "False",
                        "is_debunk": True
                    }
                ],
                "debunked_count": 2,
                "manipulated_count": 1,
                "verified_true_count": 0,
                "total_reviews": 3,
                "factcheck_summary": "Google Fact Check API: Found 3 authoritative reviews. Debunked: 2, Manipulated: 1, True: 0."
            },
            "news_summary": "International security outlets identify heavy astroturfed repost networks deploying recycled CGI clips to manufacture panic.",
            "total_news_found": 18,
            "high_trust_sources": 14,
            "contradiction_count": 9,
            "support_count": 0
        },
        "dm_report": {
            "classification": {
                "category": "Manipulated Out of Context",
                "confidence": 0.94,
                "suspicion_score": 0.88
            },
            "dm_veto": {
                "veto": True,
                "reason": "Recycled gaming media signature identified with astroturfed coordination signals."
            },
            "calibrated_claims_count": 2,
            "clustering": {
                "cluster_count": 2,
                "clusters": [
                    {"cluster_id": 1, "size": 2, "dominant_verdict": "false", "representative_claim": "Recycled CGI combat simulation"}
                ]
            },
            "pattern_mining": {
                "pattern_count": 2,
                "patterns": [
                    {"pattern": "Recycled Crisis Media Pattern", "severity": "high", "description": "Applying war sirens audio over CGI gameplay.", "indicators": ["breaking news", "combat", "evacuating", "air raid"]},
                    {"pattern": "False Casualty / Evacuation Inflation", "severity": "medium", "description": "Unverified claims of massive 500k population panic.", "indicators": ["500,000", "evacuation"]}
                ]
            },
            "outlier_detection": {"outlier_count": 1, "outliers": ["500,000 immediate evacuation without municipal order"]},
            "association_rules": {"total_rules": 3},
            "similarity_analysis": {"total_matches": 4}
        }
    }
}
