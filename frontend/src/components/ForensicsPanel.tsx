'use client';

import React, { useState } from 'react';
import { ForensicsReport, SuspiciousSegment } from '../types/reports';

interface ForensicsPanelProps {
  report: ForensicsReport | null | undefined;
  onSeek?: (seconds: number) => void;
}

export function ForensicsPanel({ report, onSeek }: ForensicsPanelProps) {
  const [open, setOpen] = useState(true);
  const [showOpenCV, setShowOpenCV] = useState(true);
  const [showGemini, setShowGemini] = useState(true);
  const [showProvenance, setShowProvenance] = useState(true);
  const [showAudit, setShowAudit] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  if (!report) return null;

  const unified = report.unified_authenticity;
  const classification = unified?.overall_verdict || unified?.classification || (report.is_synthetic ? 'AI_GENERATED' : 'INCONCLUSIVE');
  const verdictLabel = unified?.overall_verdict_label || unified?.classification;
  const confidence = unified?.confidence_level || 'UNCERTAIN';
  const confidenceMeaning = unified?.confidence_meaning || '';
  const reason = unified?.summary || unified?.reason || report.summary || 'Forensic analysis completed.';
  const suspiciousSegments: SuspiciousSegment[] = unified?.suspicious_segments || [];
  const provenance = unified?.provenance || report.provenance;
  const c2paStatus = (provenance?.status || provenance?.c2pa_status || 'unsupported').toLowerCase();
  const sha256 = provenance?.sha256;

  const visMod = unified?.visual;
  const audMod = unified?.audio;
  const coverage = unified?.analysis_coverage || {};

  const cv = report.opencv_visual;
  const gem = report.gemini_audio;

  // Color mappings for Section 1 qualitative categories
  const getClassificationMeta = (cls: string, customLabel?: string) => {
    switch (cls) {
      case 'AI_GENERATED':
      case 'LIKELY_AI_GENERATED':
        return { label: customLabel || 'Likely AI-Generated', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.12)', border: 'rgba(139, 92, 246, 0.35)', icon: '🤖' };
      case 'PARTIALLY_AI_GENERATED':
      case 'POTENTIALLY_AI_EDITED':
        return { label: customLabel || 'Likely Partially AI-Generated / AI-Edited', color: '#6366f1', bg: 'rgba(99, 102, 241, 0.12)', border: 'rgba(99, 102, 241, 0.35)', icon: '✨' };
      case 'POTENTIALLY_FACIAL_MANIPULATION':
        return { label: customLabel || 'Potentially Face-Swapped / Manipulated', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.35)', icon: '👤' };
      case 'POTENTIALLY_SYNTHETIC_SPEECH':
        return { label: customLabel || 'Potentially Synthetic Speech', color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.12)', border: 'rgba(244, 63, 94, 0.35)', icon: '🎙️' };
      case 'LIKELY_MANIPULATED':
      case 'CONVENTIONAL_EDITING_DETECTED':
        return { label: customLabel || 'Likely Manipulated — Origin Undetermined', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.12)', border: 'rgba(6, 182, 212, 0.35)', icon: '✂️' };
      case 'LIKELY_AUTHENTIC':
      case 'AUTHENTIC_NO_ANOMALIES_DETECTED':
        return { label: customLabel || 'Likely Authentic — No Strong AI Indicators Detected', color: '#10b981', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.35)', icon: '🛡️' };
      case 'INCONCLUSIVE':
      default:
        return { label: customLabel || 'Inconclusive', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.12)', border: 'rgba(148, 163, 184, 0.35)', icon: '⚖️' };
    }
  };

  const meta = getClassificationMeta(classification, verdictLabel);

  const getC2PAColor = (status: string) => {
    switch (status) {
      case 'verified':
        return { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', text: 'VERIFIED SIGNATURE' };
      case 'invalid':
        return { color: '#dc2626', bg: 'rgba(220, 38, 38, 0.15)', text: 'INVALID / CORRUPT' };
      case 'missing':
        return { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', text: 'NO CREDENTIALS FOUND' };
      case 'unsupported':
      default:
        return { color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)', text: 'NOT APPLICABLE' };
    }
  };

  const c2paColor = getC2PAColor(c2paStatus);

  const handleCopyHash = () => {
    if (sha256) {
      navigator.clipboard.writeText(sha256);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const handleDownloadReport = () => {
    const reportData = {
      title: 'TrueLens AI Forensics & Media Authenticity Investigation Report',
      timestamp: new Date().toISOString(),
      authenticity_classification: classification,
      confidence_level: confidence,
      reason: reason,
      provenance: provenance,
      suspicious_segments: suspiciousSegments,
      opencv_visual: cv,
      gemini_audio: gem,
      technical_audio: report.technical_audio,
      checks_performed: unified?.checks_performed || [],
      checks_unavailable: unified?.checks_unavailable || [],
      limitations: unified?.limitations || [],
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forensics_dossier_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="glass forensics-panel" style={{ position: 'relative' }}>
      <div className="collapse-header" onClick={() => setOpen(!open)}>
        <div className="section-title" style={{ marginBottom: 0, borderBottom: 'none', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span>Unified Forensics & Authenticity Engine</span>
          <span
            style={{
              fontSize: '0.65rem',
              fontWeight: 800,
              padding: '0.2rem 0.5rem',
              borderRadius: '6px',
              color: meta.color,
              background: meta.bg,
              border: `1px solid ${meta.border}`,
              letterSpacing: '0.04em',
            }}
          >
            {meta.label.toUpperCase()}
          </span>
        </div>
        <span className={`collapse-chevron ${open ? 'open' : ''}`}>▼</span>
      </div>

      {open && (
        <>
          {/* ── Top Classification Verdict Card ── */}
          <div
            style={{
              background: meta.bg,
              border: `1px solid ${meta.border}`,
              borderRadius: '14px',
              padding: '1.1rem 1.25rem',
              marginBottom: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.8rem' }}>{meta.icon}</span>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '1.05rem', fontWeight: 800, color: meta.color }}>
                      {meta.label}
                    </span>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        fontWeight: 800,
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        background: 'rgba(255,255,255,0.08)',
                        color: 'var(--text-primary)',
                      }}
                    >
                      {confidence} CONFIDENCE
                    </span>
                  </div>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0', lineHeight: 1.5 }}>
                    {reason}
                  </p>
                  {confidenceMeaning && (
                    <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.2rem 0 0', fontStyle: 'italic' }}>
                      {confidenceMeaning}
                    </p>
                  )}
                </div>
              </div>

              <button
                onClick={handleDownloadReport}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  padding: '0.4rem 0.8rem',
                  borderRadius: '8px',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  transition: 'all 0.2s ease',
                }}
                title="Download verified investigation dossier"
              >
                <span>📥</span> Export Dossier
              </button>
            </div>
          </div>

          {/* ── Independent Modality Coverage Cards (Section 1 & 7) ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
            {/* Visual Modality Card */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '0.85rem 1rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span>🎬</span>
                  <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)' }}>Visual Modality</span>
                </div>
                <span
                  style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '0.1rem 0.4rem',
                    borderRadius: '4px',
                    background: (visMod?.status || coverage.visual || 'NOT_ANALYZED') === 'COMPLETED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(107, 114, 128, 0.15)',
                    color: (visMod?.status || coverage.visual || 'NOT_ANALYZED') === 'COMPLETED' ? '#10b981' : '#94a3b8',
                  }}
                >
                  {visMod?.status || coverage.visual || (cv?.status === 'assessed' ? 'COMPLETED' : 'NOT_ANALYZED')}
                </span>
              </div>
              <div
                style={{
                  fontSize: '0.82rem',
                  fontWeight: 800,
                  color: (visMod?.verdict === 'AI_GENERATED' ? '#ef4444' : (visMod?.verdict === 'LIKELY_AUTHENTIC' ? '#10b981' : (visMod?.verdict === 'LIKELY_MANIPULATED' ? '#06b6d4' : meta.color))),
                  marginBottom: '0.25rem',
                }}
              >
                {visMod?.verdict_label || (cv?.anomaly_level === 'elevated' ? 'LIKELY AI-GENERATED' : cv?.anomaly_level === 'low' ? 'LIKELY AUTHENTIC' : 'INCONCLUSIVE')}
              </div>
              <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {cv?.frames_analyzed || 0} keyframes analyzed (~1 fps) · {cv?.video_resolution || 'Resolution N/A'}
              </p>
            </div>

            {/* Audio Modality Card */}
            <div
              style={{
                background: (audMod?.error_code || gem?.status === 'failed') ? 'rgba(239, 68, 68, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                border: `1px solid ${(audMod?.error_code || gem?.status === 'failed') ? 'rgba(239, 68, 68, 0.3)' : 'var(--border)'}`,
                borderRadius: '12px',
                padding: '0.85rem 1rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span>🎙️</span>
                  <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)' }}>Audio Modality</span>
                </div>
                <span
                  style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '0.1rem 0.4rem',
                    borderRadius: '4px',
                    background: (audMod?.status || coverage.audio) === 'COMPLETED'
                      ? 'rgba(16, 185, 129, 0.15)'
                      : (audMod?.status || coverage.audio) === 'FAILED' || gem?.status === 'failed'
                      ? 'rgba(239, 68, 68, 0.15)'
                      : 'rgba(107, 114, 128, 0.15)',
                    color: (audMod?.status || coverage.audio) === 'COMPLETED'
                      ? '#10b981'
                      : (audMod?.status || coverage.audio) === 'FAILED' || gem?.status === 'failed'
                      ? '#ef4444'
                      : '#94a3b8',
                  }}
                >
                  {audMod?.status || coverage.audio || (gem?.status === 'assessed' ? 'COMPLETED' : gem?.status === 'failed' ? 'FAILED' : 'NOT_ANALYZED')}
                </span>
              </div>
              <div
                style={{
                  fontSize: '0.82rem',
                  fontWeight: 800,
                  color: (audMod?.error_code || gem?.status === 'failed')
                    ? '#ef4444'
                    : (audMod?.verdict === 'AI_GENERATED'
                    ? '#ef4444'
                    : (audMod?.verdict === 'LIKELY_AUTHENTIC'
                    ? '#10b981'
                    : (audMod?.verdict === 'LIKELY_MANIPULATED'
                    ? '#06b6d4'
                    : 'var(--text-primary)'))),
                  marginBottom: '0.25rem',
                }}
              >
                {audMod?.verdict_label || (gem?.status === 'failed' ? 'INCONCLUSIVE (DETECTOR TIMEOUT)' : 'INCONCLUSIVE')}
              </div>
              {(audMod?.error_code || gem?.status === 'failed') ? (
                <p style={{ margin: 0, fontSize: '0.72rem', color: '#ef4444', lineHeight: 1.4 }}>
                  ⚠️ Error: <strong>{audMod?.error_code || gem?.error_code || 'DEADLINE_EXCEEDED'}</strong>. Acoustic model timed out. Timeouts are never treated as proof of authenticity.
                </p>
              ) : (
                <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {report.technical_audio?.duration_seconds ? `${report.technical_audio.duration_seconds.toFixed(1)}s analyzed` : 'Speech acoustics analyzed'} · Codec {report.technical_audio?.codec_name || 'N/A'}
                </p>
              )}
            </div>
          </div>

          {/* ── Qualitative Forensic Grid (No Unsupported Percentages) ── */}
          <div className="forensics-grid" style={{ marginBottom: '1rem' }}>
            <div className="forensics-stat-card">
              <div className="forensics-stat-value" style={{ color: meta.color, fontSize: '1.05rem', fontWeight: 800 }}>
                {classification === 'AUTHENTIC_NO_ANOMALIES_DETECTED' || classification === 'LIKELY_AUTHENTIC'
                  ? 'Authentic'
                  : classification === 'CONVENTIONAL_EDITING_DETECTED' || classification === 'LIKELY_MANIPULATED'
                  ? 'Conventional'
                  : classification === 'INCONCLUSIVE'
                  ? 'Inconclusive'
                  : 'Synthetic / AI'}
              </div>
              <div className="forensics-stat-label">Authenticity Status</div>
            </div>

            <div className="forensics-stat-card">
              <div className="forensics-stat-value" style={{ color: c2paColor.color, fontSize: '0.95rem', fontWeight: 800 }}>
                {c2paStatus.toUpperCase()}
              </div>
              <div className="forensics-stat-label">C2PA Credentials</div>
            </div>

            <div className="forensics-stat-card">
              <div
                className="forensics-stat-value"
                style={{
                  color: cv?.anomaly_level === 'elevated' ? '#dc2626' : cv?.anomaly_level === 'moderate' ? '#d97706' : '#059669',
                  fontSize: '1.05rem',
                  fontWeight: 800,
                }}
              >
                {(cv?.anomaly_level || 'LOW').toUpperCase()}
              </div>
              <div className="forensics-stat-label">Visual Anomaly Risk</div>
            </div>

            <div className="forensics-stat-card">
              <div
                className="forensics-stat-value"
                style={{
                  color: report.red_flag_count === 0 ? '#059669' : report.red_flag_count >= 4 ? '#dc2626' : '#d97706',
                  fontSize: '1.15rem',
                  fontWeight: 800,
                }}
              >
                {report.red_flag_count}
              </div>
              <div className="forensics-stat-label">Verified Anomaly Signals</div>
            </div>
          </div>

          {/* ── Provenance & C2PA Content Credentials Card ── */}
          <div
            style={{
              marginBottom: '1rem',
              padding: '0.9rem 1.1rem',
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '12px',
              border: '1px solid var(--border)',
            }}
          >
            <div
              onClick={() => setShowProvenance(!showProvenance)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '1.1rem' }}>📜</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Media Provenance & Content Credentials (C2PA)
                </span>
                <span
                  style={{
                    fontSize: '0.65rem',
                    padding: '0.15rem 0.5rem',
                    borderRadius: '6px',
                    fontWeight: 700,
                    background: c2paColor.bg,
                    color: c2paColor.color,
                  }}
                >
                  {c2paColor.text}
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {showProvenance ? '▲' : '▼'}
              </span>
            </div>

            {showProvenance && (
              <div style={{ marginTop: '0.8rem', fontSize: '0.78rem' }}>
                {sha256 && (
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.6rem 0.8rem', borderRadius: '8px', marginBottom: '0.6rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.68rem', fontWeight: 600 }}>ORIGINAL FILE SHA-256 HASH</span>
                      <code style={{ fontSize: '0.74rem', color: '#38bdf8', wordBreak: 'break-all' }}>{sha256}</code>
                    </div>
                    <button
                      onClick={handleCopyHash}
                      style={{
                        background: 'transparent',
                        border: '1px solid var(--border)',
                        color: 'var(--text-secondary)',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.68rem',
                      }}
                    >
                      {copiedHash ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                )}

                {provenance?.issuer && (
                  <div style={{ marginBottom: '0.4rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Credential Issuer: </span>
                    <strong>{provenance.issuer}</strong>
                  </div>
                )}
                {provenance?.generator && (
                  <div style={{ marginBottom: '0.4rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Claim Generator Tool: </span>
                    <strong>{provenance.generator}</strong>
                  </div>
                )}

                <p style={{ margin: '0.4rem 0 0', color: 'var(--text-muted)', fontSize: '0.72rem', fontStyle: 'italic' }}>
                  {provenance?.disclaimer || 'Absence of C2PA Content Credentials is standard for web media and does NOT imply synthetic manipulation.'}
                </p>
              </div>
            )}
          </div>

          {/* ── Suspicious Timestamps / Segments Card ── */}
          {suspiciousSegments.length > 0 && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.9rem 1.1rem',
                background: 'rgba(245, 158, 11, 0.05)',
                borderRadius: '12px',
                border: '1px solid rgba(245, 158, 11, 0.25)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.6rem' }}>
                <span style={{ fontSize: '1.1rem' }}>⏱️</span>
                <span style={{ fontSize: '0.75rem', color: '#f59e0b', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Suspicious Media Intervals ({suspiciousSegments.length} flagged)
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {suspiciousSegments.map((seg, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.4rem',
                      fontSize: '0.78rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <button
                        type="button"
                        onClick={() => onSeek?.(seg.start_time)}
                        style={{
                          background: 'rgba(245, 158, 11, 0.18)',
                          border: '1px solid rgba(245, 158, 11, 0.35)',
                          color: '#f59e0b',
                          padding: '0.15rem 0.5rem',
                          borderRadius: '6px',
                          fontWeight: 700,
                          fontSize: '0.7rem',
                          cursor: onSeek ? 'pointer' : 'default',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                        }}
                        title={onSeek ? `Seek video to ${seg.start_time.toFixed(1)}s` : undefined}
                      >
                        <span>▶</span>
                        <span>{seg.start_time.toFixed(1)}s - {seg.end_time.toFixed(1)}s</span>
                      </button>
                      <span>{seg.description}</span>
                    </div>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        color: seg.severity === 'high' ? '#dc2626' : '#f59e0b',
                      }}
                    >
                      {seg.severity} severity
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── OpenCV Computer Vision Forensics Card ── */}
          {cv && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.9rem 1rem',
                background: 'rgba(16, 185, 129, 0.04)',
                borderRadius: '12px',
                border: '1px solid rgba(16, 185, 129, 0.2)',
              }}
            >
              <div
                onClick={() => setShowOpenCV(!showOpenCV)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '1.1rem' }}>📸</span>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      color: '#059669',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                    }}
                  >
                    OpenCV Visual Forensics
                  </span>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      padding: '0.15rem 0.5rem',
                      borderRadius: '6px',
                      fontWeight: 700,
                      background: cv.status === 'assessed' ? 'rgba(5, 150, 105, 0.15)' : 'rgba(107, 114, 128, 0.15)',
                      color: cv.status === 'assessed' ? '#059669' : '#6b7280',
                    }}
                  >
                    {cv.status.toUpperCase()}
                  </span>
                  {cv.status === 'assessed' && (
                    <span
                      style={{
                        fontSize: '0.65rem',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '6px',
                        fontWeight: 700,
                        background:
                          cv.anomaly_level === 'elevated'
                            ? 'rgba(220, 38, 38, 0.15)'
                            : cv.anomaly_level === 'moderate'
                            ? 'rgba(217, 119, 6, 0.15)'
                            : 'rgba(5, 150, 105, 0.15)',
                        color:
                          cv.anomaly_level === 'elevated'
                            ? '#dc2626'
                            : cv.anomaly_level === 'moderate'
                            ? '#d97706'
                            : '#059669',
                      }}
                    >
                      {cv.anomaly_level.toUpperCase()} ANOMALY RISK
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {showOpenCV ? '▲' : '▼'}
                </span>
              </div>

              {showOpenCV && (
                <div style={{ marginTop: '0.8rem' }}>
                  {cv.status === 'assessed' ? (
                    <>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                          gap: '0.6rem',
                          marginBottom: '0.8rem',
                          fontSize: '0.78rem',
                        }}
                      >
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '8px' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>Frames Analyzed</span>
                          <strong>{cv.frames_analyzed}</strong> {cv.video_resolution ? `(${cv.video_resolution})` : ''}
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '8px' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>Editorial Scene Cuts</span>
                          <strong>{cv.scene_cuts?.count ?? 0}</strong> cuts ({cv.scene_cuts?.abrupt_transitions ?? 0} abrupt)
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '8px' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>Focus Variance</span>
                          <strong>{cv.laplacian_blur?.mean_variance ?? 0}</strong> (Stab: {Math.round((cv.laplacian_blur?.variance_stability ?? 1) * 100)}%)
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '8px' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>2D FFT Spectral Ratio</span>
                          <strong>{cv.fft_spectral_analysis?.high_frequency_ratio ?? 0}</strong> (Reg: {Math.round((cv.fft_spectral_analysis?.spectral_regularity ?? 1) * 100)}%)
                        </div>
                      </div>

                      {/* Face boundary checks */}
                      {cv.face_boundary_analysis && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem 0.8rem', borderRadius: '8px', marginBottom: '0.6rem', fontSize: '0.78rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                            <span style={{ fontWeight: 700, color: '#10b981' }}>Face Boundary & Temporal Jitter</span>
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                              {cv.face_boundary_analysis.faces_detected ? `${cv.face_boundary_analysis.total_faces_tracked} faces detected` : 'No human faces found'}
                            </span>
                          </div>
                          {cv.face_boundary_analysis.faces_detected && (
                            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', color: 'var(--text-secondary)' }}>
                              <span>Boundary Blur Ratio: <strong>{cv.face_boundary_analysis.mean_boundary_blur_ratio ?? 'N/A'}</strong></span>
                              <span>Centroid Jitter: <strong>{cv.face_boundary_analysis.jitter_score ? `${cv.face_boundary_analysis.jitter_score}px` : 'N/A'}</strong></span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Error Level Analysis */}
                      {cv.error_level_analysis?.applied && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem 0.8rem', borderRadius: '8px', marginBottom: '0.6rem', fontSize: '0.78rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                            <span style={{ fontWeight: 700, color: '#38bdf8' }}>Error Level Analysis (ELA)</span>
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Re-compression Artifacts</span>
                          </div>
                          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', color: 'var(--text-secondary)' }}>
                            <span>Mean Error: <strong>{cv.error_level_analysis.mean_error ?? 'N/A'}</strong></span>
                            <span>Max Error: <strong>{cv.error_level_analysis.max_error ?? 'N/A'}</strong></span>
                            <span>Spatial Variance: <strong>{cv.error_level_analysis.variance ?? 'N/A'}</strong></span>
                          </div>
                          <p style={{ margin: '0.3rem 0 0', color: 'var(--text-muted)', fontSize: '0.68rem', fontStyle: 'italic' }}>
                            {cv.error_level_analysis.limitations}
                          </p>
                        </div>
                      )}
                    </>
                  ) : (
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>
                      {cv.limitations || 'OpenCV video stream inspection not performed (no video file supplied).'}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Gemini Multimodal Audio Forensics Card ── */}
          {gem && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.9rem 1rem',
                background: 'rgba(124, 58, 237, 0.04)',
                borderRadius: '12px',
                border: '1px solid rgba(124, 58, 237, 0.2)',
              }}
            >
              <div
                onClick={() => setShowGemini(!showGemini)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '1.1rem' }}>🎙️</span>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      color: '#7c3aed',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                    }}
                  >
                    Audio Stream & Speech Authenticity
                  </span>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      padding: '0.15rem 0.5rem',
                      borderRadius: '6px',
                      fontWeight: 700,
                      background: gem.status === 'assessed' ? 'rgba(124, 58, 237, 0.15)' : 'rgba(107, 114, 128, 0.15)',
                      color: gem.status === 'assessed' ? '#7c3aed' : '#6b7280',
                    }}
                  >
                    {gem.status.toUpperCase()}
                  </span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {showGemini ? '▲' : '▼'}
                </span>
              </div>

              {showGemini && (
                <div style={{ marginTop: '0.8rem', fontSize: '0.78rem' }}>
                  {gem.status === 'assessed' ? (
                    <>
                      {/* Technical Audio Stream Properties */}
                      {report.technical_audio && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.5rem 0.75rem', borderRadius: '8px', marginBottom: '0.6rem' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.68rem', fontWeight: 600 }}>ACOUSTIC CONTAINER PROPERTIES</span>
                          <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', marginTop: '0.2rem' }}>
                            <span>Codec: <strong>{report.technical_audio.codec_name || 'N/A'}</strong></span>
                            <span>Sample Rate: <strong>{report.technical_audio.sample_rate ? `${report.technical_audio.sample_rate} Hz` : 'N/A'}</strong></span>
                            <span>Silence Bursts: <strong>{report.technical_audio.silence_burst_count}</strong></span>
                          </div>
                        </div>
                      )}

                      {/* Transcript Comparison */}
                      {gem.transcript_comparison && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.5rem 0.75rem', borderRadius: '8px', marginBottom: '0.6rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 700, color: '#a78bfa' }}>Dual-Engine Transcript Concordance</span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                              Whisper vs. Gemini
                            </span>
                          </div>
                          <div style={{ marginTop: '0.3rem', color: 'var(--text-secondary)' }}>
                            {gem.transcript_comparison.similarity_score !== undefined && gem.transcript_comparison.similarity_score !== null ? (
                              <span>Concordance Match: <strong>{Math.round(gem.transcript_comparison.similarity_score * 100)}%</strong></span>
                            ) : (
                              <span style={{ color: '#94a3b8' }}>
                                Status: <strong>{gem.transcript_comparison.similarity_status || 'NOT COMPARABLE'}</strong>
                                {gem.transcript_comparison.comparable_reason ? ` (${gem.transcript_comparison.comparable_reason})` : ''}
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Acoustic Anomaly Audit */}
                      {gem.acoustic_anomaly_analysis && (
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '0.5rem 0.75rem', borderRadius: '8px', marginBottom: '0.6rem' }}>
                          <span style={{ fontWeight: 700, color: '#f43f5e', display: 'block', marginBottom: '0.2rem' }}>
                            Acoustic & Prosodic Audit
                          </span>
                          {gem.acoustic_anomaly_analysis.cadence_observations && (
                            <div style={{ margin: '0.2rem 0', color: 'var(--text-secondary)' }}>
                              <span>Speech Cadence: </span>{gem.acoustic_anomaly_analysis.cadence_observations}
                            </div>
                          )}
                          {gem.acoustic_anomaly_analysis.robotic_artifacts && (
                            <div style={{ margin: '0.2rem 0', color: 'var(--text-secondary)' }}>
                              <span>Timbre Artifacts: </span>{gem.acoustic_anomaly_analysis.robotic_artifacts}
                            </div>
                          )}
                        </div>
                      )}

                      <p style={{ margin: '0.4rem 0 0', color: 'var(--text-muted)', fontSize: '0.7rem', fontStyle: 'italic' }}>
                        {gem.limitations || 'Acoustic cues provide auditory anomaly context and do not replace biometric speaker verification.'}
                      </p>
                    </>
                  ) : (
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>
                      {gem.reason || 'Gemini native audio inspection was not assessed for this stream.'}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Detector Execution Audit Collapsible ── */}
          <div
            style={{
              marginBottom: '1rem',
              padding: '0.75rem 1rem',
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '12px',
              border: '1px solid var(--border)',
            }}
          >
            <div
              onClick={() => setShowAudit(!showAudit)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Forensic Detector Audit & Disclaimers
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {showAudit ? '▲' : '▼'}
              </span>
            </div>

            {showAudit && (
              <div style={{ marginTop: '0.8rem', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                <div style={{ marginBottom: '0.6rem' }}>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '0.2rem' }}>Checks Performed:</span>
                  <ul style={{ margin: '0 0 0 1.2rem', padding: 0 }}>
                    {(unified?.checks_performed || ['OpenCV Visual Analysis', 'FFprobe Audio Inspection']).map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>

                {unified?.checks_unavailable && unified.checks_unavailable.length > 0 && (
                  <div style={{ marginBottom: '0.6rem' }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '0.2rem' }}>Checks Not Assessed (Transparent Limitations):</span>
                    <ul style={{ margin: '0 0 0 1.2rem', padding: 0 }}>
                      {unified.checks_unavailable.map((u, i) => (
                        <li key={i}>
                          <strong>{u.check}:</strong> {u.reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border)', paddingTop: '0.5rem', color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.7rem' }}>
                  Scientific Disclaimer: TrueLens AI reports statistical and frequency anomalies. It never claims absolute proof of authenticity or manipulation based solely on heuristics.
                </div>
              </div>
            )}
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: '0.75rem', margin: 0 }}>
            {report.summary}
          </p>
        </>
      )}
    </div>
  );
}

export default ForensicsPanel;
