'use client';

import React, { useState } from 'react';
import { OSINTReport, NewsResult, SocialResult, GeoVerificationItem, GoogleFactCheckItem } from '../types/reports';
import { DomainTrust } from '../lib/mockData';

const TRUST_LABEL: Record<DomainTrust, string> = {
  high: '✓ High Trust',
  medium: '~ Medium',
  low: '⚠ Low',
  blocked: '✗ Blocked',
};

interface OSINTPanelProps {
  report: OSINTReport | null | undefined;
}

export function OSINTPanel({ report }: OSINTPanelProps) {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState<'news' | 'social' | 'geo' | 'timestamp'>('news');
  if (!report) return null;

  const newsResults = report.news_verification?.news_results || [];
  const socialResults = report.social_signals?.social_results || [];
  const geoVers = report.geo_verification?.geo_verifications || [];
  const timestampIssues = report.timestamp_verification?.timestamp_issues || [];

  return (
    <div className="glass osint-panel">
      <div className="collapse-header" onClick={() => setOpen(!open)}>
        <div className="section-title" style={{ marginBottom: 0, borderBottom: 'none' }}>
          OSINT Intelligence
        </div>
        <span className={`collapse-chevron ${open ? 'open' : ''}`}>▼</span>
      </div>
      {open && (
        <>
          <div className="osint-stat-row">
            <div className="osint-stat-box">
              <div className="osint-stat-number" style={{ color: '#4f46e5' }}>
                {report.news_verification?.total_news_found || 0}
              </div>
              <div className="osint-stat-label">News Sources</div>
            </div>
            <div className="osint-stat-box">
              <div className="osint-stat-number" style={{ color: '#059669' }}>
                {report.news_verification?.high_trust_sources || 0}
              </div>
              <div className="osint-stat-label">High Trust</div>
            </div>
            <div className="osint-stat-box">
              <div className="osint-stat-number" style={{ color: '#dc2626' }}>
                {report.contradiction_count || 0}
              </div>
              <div className="osint-stat-label">Contradictions</div>
            </div>
            <div className="osint-stat-box">
              <div className="osint-stat-number" style={{ color: '#059669' }}>
                {report.support_count || 0}
              </div>
              <div className="osint-stat-label">Supporting</div>
            </div>
            <div className="osint-stat-box">
              <div className="osint-stat-number" style={{ color: '#d97706' }}>
                {report.social_signals?.total_social_found || 0}
              </div>
              <div className="osint-stat-label">Social Posts</div>
            </div>
          </div>

          {report.osint_veto?.veto && (
            <div
              style={{
                background: 'rgba(220,38,38,0.08)',
                border: '1px solid rgba(220,38,38,0.25)',
                borderRadius: '12px',
                padding: '0.85rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                gap: '0.65rem',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: '1.2rem' }}>⚠️</span>
              <div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    color: '#dc2626',
                  }}
                >
                  OSINT Evidence Veto Enforced
                </span>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', margin: '0.15rem 0 0', fontWeight: 500 }}>
                  {report.osint_veto.reason}
                </p>
              </div>
            </div>
          )}

          {report.potential_recycled_content && (
            <div
              style={{
                background: 'rgba(217,119,6,0.06)',
                border: '1px solid rgba(217,119,6,0.18)',
                borderRadius: '10px',
                padding: '0.8rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                gap: '0.6rem',
                alignItems: 'flex-start',
              }}
            >
              <span>⚠️</span>
              <p style={{ fontSize: '0.83rem', color: '#d97706', lineHeight: 1.5 }}>
                <strong>Old Footage Warning:</strong> Reverse search found signals suggesting this may be recycled or reused video content presented in a new context.
              </p>
            </div>
          )}

          {report.google_factcheck && report.google_factcheck.fact_checks_found.length > 0 && (
            <div
              style={{
                marginBottom: '1.2rem',
                padding: '0.85rem 1rem',
                background: 'rgba(5,150,105,0.05)',
                borderRadius: '12px',
                border: '1px solid rgba(5,150,105,0.2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.72rem', color: '#059669', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Google Fact Check Tools API ({report.google_factcheck.fact_checks_found.length} Certified Reviews)
                </span>
                <span style={{ fontSize: '0.72rem', color: '#dc2626', fontWeight: 700 }}>
                  {report.google_factcheck.debunked_count} Debunked
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {report.google_factcheck.fact_checks_found.map((fc: GoogleFactCheckItem, i: number) => (
                  <div
                    key={i}
                    style={{
                      padding: '0.55rem 0.8rem',
                      background: 'var(--bg-secondary)',
                      borderRadius: '8px',
                      borderLeft: `3px solid ${fc.is_debunk ? '#dc2626' : '#059669'}`,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', marginBottom: '0.2rem' }}>
                      <span style={{ fontWeight: 700, color: 'var(--text-muted)' }}>{fc.publisher}</span>
                      <span style={{ fontWeight: 800, color: fc.is_debunk ? '#dc2626' : '#059669' }}>
                        Verdict: {fc.rating}
                      </span>
                    </div>
                    <a
                      href={fc.review_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ fontSize: '0.82rem', color: 'var(--accent)', fontWeight: 600 }}
                    >
                      {fc.title} ↗
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="tab-bar">
            {(['news', 'social', 'geo', 'timestamp'] as const).map(t => (
              <button key={t} className={`tab-btn${tab === t ? ' active' : ''}`} onClick={() => setTab(t)}>
                {{
                  news: `News (${newsResults.length})`,
                  social: `Social (${socialResults.length})`,
                  geo: 'Geolocation',
                  timestamp: 'Timeline',
                }[t]}
              </button>
            ))}
          </div>

          {tab === 'news' && (
            <div>
              {newsResults.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No news sources found for this content.</p>
              ) : (
                newsResults.slice(0, 5).map((r: NewsResult, i: number) => (
                  <div key={i} className="osint-source-card">
                    <div className="osint-source-meta">
                      <span className={`trust-pill trust-${r.domain_trust}`}>
                        {TRUST_LABEL[r.domain_trust as DomainTrust] || r.domain_trust}
                      </span>
                      <span className="ev-domain">📍 {r.domain}</span>
                      {r.published_date && <span className="ev-date">📅 {r.published_date}</span>}
                    </div>
                    <a href={r.url} target="_blank" rel="noreferrer" className="osint-source-title">{r.title} ↗</a>
                    {r.snippet && <p className="osint-source-snippet">"{r.snippet.slice(0, 160)}"</p>}
                  </div>
                ))
              )}
            </div>
          )}

          {tab === 'social' && (
            <div>
              {socialResults.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No social media discussions found.</p>
              ) : (
                socialResults.slice(0, 5).map((r: SocialResult, i: number) => (
                  <div key={i} className="osint-source-card">
                    <div className="osint-source-meta">
                      <span
                        style={{
                          fontSize: '0.72rem',
                          color: '#4f46e5',
                          fontWeight: 700,
                          background: 'rgba(79,70,229,0.06)',
                          border: '1px solid rgba(79,70,229,0.15)',
                          borderRadius: '99px',
                          padding: '0.12rem 0.5rem',
                        }}
                      >
                        {r.platform || 'Social'}
                      </span>
                      <span className="ev-domain">{r.domain}</span>
                    </div>
                    <a href={r.url} target="_blank" rel="noreferrer" className="osint-source-title">{r.title} ↗</a>
                    {r.snippet && <p className="osint-source-snippet">"{r.snippet.slice(0, 140)}"</p>}
                  </div>
                ))
              )}
              {report.social_signals?.manipulation_signals && report.social_signals.manipulation_signals.length > 0 && (
                <div
                  style={{
                    marginTop: '0.75rem',
                    background: 'rgba(220,38,38,0.05)',
                    border: '1px solid rgba(220,38,38,0.15)',
                    borderRadius: '10px',
                    padding: '0.8rem',
                  }}
                >
                  <p style={{ fontSize: '0.75rem', color: '#dc2626', fontWeight: 700, marginBottom: '0.4rem' }}>
                    Social Manipulation Signals
                  </p>
                  {report.social_signals.manipulation_signals.map((s: string, i: number) => (
                    <p key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>• {s}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === 'geo' && (
            <div>
              <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                {report.geo_verification?.geo_summary || 'No geographic verification data.'}
              </p>
              {geoVers.length > 0 &&
                geoVers.slice(0, 4).map((g: GeoVerificationItem, i: number) => (
                  <div
                    key={i}
                    className="osint-source-card"
                    style={{
                      borderLeft: g.geo_contradicts
                        ? '3px solid #f43f5e'
                        : g.geo_supports
                        ? '3px solid #10b981'
                        : undefined,
                    }}
                  >
                    <div className="osint-source-meta">
                      <span
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          color: g.geo_contradicts ? '#dc2626' : g.geo_supports ? '#059669' : 'var(--text-muted)',
                        }}
                      >
                        {g.geo_contradicts ? 'Contradicts' : g.geo_supports ? 'Supports' : 'Neutral'}
                      </span>
                      <span className={`trust-pill trust-${g.domain_trust}`}>
                        {TRUST_LABEL[g.domain_trust as DomainTrust] || g.domain_trust}
                      </span>
                      <span style={{ fontSize: '0.72rem', color: '#4f46e5', fontWeight: 700 }}>{g.location}</span>
                    </div>
                    <a href={g.url} target="_blank" rel="noreferrer" className="osint-source-title">{g.source} ↗</a>
                  </div>
                ))}
            </div>
          )}

          {tab === 'timestamp' && (
            <div>
              <p style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                {report.timestamp_verification?.timestamp_summary || 'No timestamp issues detected.'}
              </p>
              {timestampIssues.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  {timestampIssues.map((issue: string, i: number) => (
                    <div key={i} className="red-flag-item">
                      <span className="red-flag-icon">⏰</span>
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              )}
              {report.weather_verification?.weather_claims_found && report.weather_verification.weather_claims_found.length > 0 && (
                <div>
                  <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.5rem' }}>
                    Weather Claims
                  </p>
                  <div className="geo-tags">
                    {report.weather_verification.weather_claims_found.map((w: string, i: number) => (
                      <span key={i} className="geo-tag">{w}</span>
                    ))}
                  </div>
                </div>
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

export default OSINTPanel;
