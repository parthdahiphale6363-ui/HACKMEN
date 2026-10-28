'use client';

import React, { useState } from 'react';
import { DataMiningReport, DMPattern, DMCluster, DMOutlier, DMAssociationRule, DMTemplateMatch } from '../types/reports';
import { getVerdictCatStyle } from '../lib/styleUtils';

interface DataMiningPanelProps {
  report: DataMiningReport | null | undefined;
}

export function DataMiningPanel({ report }: DataMiningPanelProps) {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState<'patterns' | 'clusters' | 'outliers' | 'rules' | 'similarity'>('patterns');
  if (!report) return null;

  const classification = report.classification || { category: '', suspicion_score: 0, confidence: 0 };
  const clusters = report.clustering?.clusters || [];
  const outliers = report.outlier_detection?.outliers || [];
  const rules = report.association_rules?.strong_rules || [];
  const patterns = report.pattern_mining?.patterns || [];
  const similarity = report.similarity_analysis?.template_matches || [];

  return (
    <div className="glass dm-panel">
      <div className="collapse-header" onClick={() => setOpen(!open)}>
        <div className="section-title" style={{ marginBottom: 0, borderBottom: 'none' }}>
          Data Mining Analysis
        </div>
        <span className={`collapse-chevron ${open ? 'open' : ''}`}>▼</span>
      </div>
      {open && (
        <>
          {/* Classification Result */}
          {classification.category && (
            <div
              style={{
                background: getVerdictCatStyle(classification.category).bg,
                border: `1px solid ${getVerdictCatStyle(classification.category).border}`,
                borderRadius: '14px',
                padding: '1.1rem 1.35rem',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                flexWrap: 'wrap',
              }}
            >
              <div style={{ flex: 1 }}>
                <p
                  style={{
                    fontSize: '0.68rem',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.12em',
                    color: getVerdictCatStyle(classification.category).color,
                    marginBottom: '0.25rem',
                  }}
                >
                  DM Narrative Classification
                </p>
                <p
                  style={{
                    fontFamily: 'Outfit, sans-serif',
                    fontSize: '1.3rem',
                    fontWeight: 800,
                    color: getVerdictCatStyle(classification.category).color,
                  }}
                >
                  {classification.category}
                </p>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  Suspicion score: {(classification.suspicion_score * 100).toFixed(0)}% · Pattern Confidence: {(classification.confidence * 100).toFixed(0)}%
                </p>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div
                  style={{
                    fontFamily: 'Outfit, sans-serif',
                    fontSize: '2rem',
                    fontWeight: 900,
                    color: getVerdictCatStyle(classification.category).color,
                  }}
                >
                  {Math.round(classification.confidence * 100)}%
                </div>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Confidence
                </div>
              </div>
            </div>
          )}

          {report.dm_veto?.veto && (
            <div
              style={{
                background: 'rgba(217,119,6,0.08)',
                border: '1px solid rgba(217,119,6,0.25)',
                borderRadius: '12px',
                padding: '0.85rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                gap: '0.65rem',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: '1.2rem' }}>⚡</span>
              <div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#d97706' }}>
                  Data Mining Pattern Governor Override
                </span>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', margin: '0.15rem 0 0', fontWeight: 500 }}>
                  {report.dm_veto.reason}
                </p>
              </div>
            </div>
          )}

          {report.calibrated_claims_count > 0 && (
            <div
              style={{
                fontSize: '0.78rem',
                color: '#6366f1',
                marginBottom: '1rem',
                padding: '0.5rem 0.85rem',
                background: 'rgba(99,102,241,0.06)',
                borderRadius: '10px',
                border: '1px solid rgba(99,102,241,0.18)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>🎯</span>
              <span>
                <strong>Active Calibration:</strong> Re-weighted confidence for {report.calibrated_claims_count} claim{report.calibrated_claims_count > 1 ? 's' : ''} based on outlier detection and deceptive template patterns.
              </span>
            </div>
          )}

          {/* DM Stats Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.65rem', marginBottom: '1.25rem' }}>
            {[
              ['Clusters', report.clustering?.cluster_count ?? 0, '#4f46e5'],
              ['Outliers', report.outlier_detection?.outlier_count ?? 0, '#f59e0b'],
              ['Patterns', report.pattern_mining?.pattern_count ?? 0, '#7c3aed'],
              ['Assoc Rules', report.association_rules?.total_rules ?? 0, '#059669'],
              ['Template Matches', report.similarity_analysis?.total_matches ?? 0, '#dc2626'],
            ].map(([label, val, color]) => (
              <div key={label as string} className="score-cell">
                <div className="score-label">{label}</div>
                <div className="score-value" style={{ color: color as string }}>{val}</div>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="tab-bar">
            {(['patterns', 'clusters', 'outliers', 'rules', 'similarity'] as const).map(t => (
              <button key={t} className={`tab-btn${tab === t ? ' active' : ''}`} onClick={() => setTab(t)}>
                {{ patterns: 'Patterns', clusters: 'Clusters', outliers: 'Outliers', rules: 'Rules', similarity: 'Similarity' }[t]}
              </button>
            ))}
          </div>

          {tab === 'patterns' && (
            <div>
              {patterns.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No suspicious linguistic patterns detected.</p>
              ) : (
                patterns.map((p: DMPattern, i: number) => (
                  <div key={i} className={`pattern-card ${p.severity}`}>
                    <div
                      className="pattern-name"
                      style={{
                        color: p.severity === 'high' ? '#f43f5e' : p.severity === 'medium' ? '#f59e0b' : 'var(--text-primary)',
                      }}
                    >
                      {p.pattern}{' '}
                      <span style={{ fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', opacity: 0.7 }}>
                        ({p.severity} severity)
                      </span>
                    </div>
                    <p className="pattern-desc">{p.description}</p>
                    {p.indicators && p.indicators.length > 0 && (
                      <div className="pattern-tags">
                        {p.indicators.slice(0, 5).map((ind: string, j: number) => (
                          <span key={j} className="pattern-tag">"{ind}"</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'clusters' && (
            <div>
              {clusters.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No claims to cluster.</p>
              ) : (
                clusters.map((c: DMCluster) => (
                  <div key={c.cluster_id} className="cluster-card">
                    <div className="cluster-num">#{c.cluster_id}</div>
                    <div className="cluster-body">
                      <p className="cluster-text">{c.representative_claim || 'No representative claim'}</p>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.35rem', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{c.size} claim{c.size !== 1 ? 's' : ''}</span>
                        <span className={`badge badge-${c.dominant_verdict}`} style={{ fontSize: '0.65rem', padding: '0.1rem 0.5rem' }}>
                          {c.dominant_verdict}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'outliers' && (
            <div>
              {outliers.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>✅ No anomalous claims detected.</p>
              ) : (
                outliers.map((o: DMOutlier, i: number) => (
                  <div key={i} className="outlier-item">
                    <div>
                      <span className={`outlier-severity-badge ${o.anomaly_severity}`}>{o.anomaly_severity}</span>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginBottom: '0.3rem' }}>"{o.claim_text}"</p>
                      {o.reasons.map((r: string, j: number) => (
                        <p key={j} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>• {r}</p>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'rules' && (
            <div>
              {rules.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No strong association rules found.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="search-table">
                    <thead>
                      <tr><th>Antecedent</th><th>→ Consequent</th><th>Support</th><th>Confidence</th><th>Lift</th></tr>
                    </thead>
                    <tbody>
                      {rules.map((r: DMAssociationRule, i: number) => (
                        <tr key={i}>
                          <td><span className="query-mono">{r.antecedent}</span></td>
                          <td style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>{r.consequent}</td>
                          <td style={{ color: '#4f46e5', fontWeight: 700 }}>{(r.support * 100).toFixed(0)}%</td>
                          <td style={{ color: '#059669', fontWeight: 700 }}>{(r.confidence * 100).toFixed(0)}%</td>
                          <td style={{ color: '#d97706' }}>{r.lift?.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === 'similarity' && (
            <div>
              {similarity.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>✅ No known misinformation templates matched.</p>
              ) : (
                similarity.map((m: DMTemplateMatch, i: number) => (
                  <div key={i} className="outlier-item">
                    <div>
                      <span className={`outlier-severity-badge ${m.exact_match ? 'high' : 'medium'}`}>
                        {m.match_type}
                      </span>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.82rem', color: '#dc2626', marginBottom: '0.25rem' }}>Template: "{m.template}"</p>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Similarity: {(m.similarity_score * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: '0.75rem', marginTop: '0.75rem' }}>
            {report.summary}
          </p>
        </>
      )}
    </div>
  );
}

export default DataMiningPanel;
