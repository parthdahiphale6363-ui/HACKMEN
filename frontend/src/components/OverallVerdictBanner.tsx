'use client';

import React from 'react';
import { getVerdictCatStyle } from '../lib/styleUtils';
import { VerdictBreakdown } from '../types/reports';

interface OverallVerdictBannerProps {
  verdict: string;
  breakdown: VerdictBreakdown;
  category: string;
  confidence: number;
}

export function OverallVerdictBanner({
  verdict,
  breakdown,
  category,
  confidence,
}: OverallVerdictBannerProps) {
  const s = getVerdictCatStyle(category);
  const pct = Math.round(confidence);

  return (
    <div className="overall-verdict-card" style={{ background: s.bg, border: `2px solid ${s.border}` }}>
      <div className="verdict-glow-overlay" style={{ color: s.color }} />
      <div className="verdict-top-row">
        <div className="verdict-left">
          <div className="verdict-eyebrow" style={{ color: s.color }}>Forensic Verdict</div>
          <div className="verdict-title" style={{ color: s.color }}>{verdict}</div>
          <p className="verdict-subtitle">
            Based on {breakdown?.total || 0} factual claims verified via live web search, combined with
            forensic analysis, OSINT intelligence, and data mining algorithms.
          </p>
        </div>
        <div className="confidence-dial-wrap">
          <div
            className="confidence-dial"
            style={{ '--dial-pct': pct, color: s.color } as React.CSSProperties}
          >
            <div className="confidence-dial-number">{pct}</div>
            <div className="confidence-dial-label">CONF%</div>
          </div>
          <div className="confidence-dial-title">Overall<br />Confidence</div>
        </div>
      </div>

      {breakdown?.veto_applied && (
        <div
          style={{
            marginTop: '0.85rem',
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: '12px',
            padding: '0.75rem 1rem',
            display: 'flex',
            gap: '0.65rem',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: '1.2rem' }}>🛡️</span>
          <div>
            <div
              style={{
                fontSize: '0.72rem',
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: '#ef4444',
              }}
            >
              Multi-Modal Verdict Veto Enforced
            </div>
            <p
              style={{
                fontSize: '0.82rem',
                color: 'var(--text-primary)',
                margin: '0.15rem 0 0',
                fontWeight: 500,
                lineHeight: 1.4,
              }}
            >
              {breakdown.veto_applied.reason}
            </p>
          </div>
        </div>
      )}

      {!verdict.includes('No factual') && (
        <div className="verdict-breakdown-row">
          {breakdown.true > 0 && (
            <div
              className="breakdown-pill"
              style={{ background: 'rgba(5,150,105,0.07)', border: '1px solid rgba(5,150,105,0.18)' }}
            >
              <div className="breakdown-number" style={{ color: '#059669' }}>{breakdown.true}</div>
              <div className="breakdown-label" style={{ color: '#059669' }}>True</div>
            </div>
          )}
          {breakdown.false > 0 && (
            <div
              className="breakdown-pill"
              style={{ background: 'rgba(220,38,38,0.07)', border: '1px solid rgba(220,38,38,0.18)' }}
            >
              <div className="breakdown-number" style={{ color: '#dc2626' }}>{breakdown.false}</div>
              <div className="breakdown-label" style={{ color: '#dc2626' }}>False</div>
            </div>
          )}
          {((breakdown.misleading || 0) + (breakdown.unverifiable || 0)) > 0 && (
            <div
              className="breakdown-pill"
              style={{ background: 'rgba(217,119,6,0.07)', border: '1px solid rgba(217,119,6,0.18)' }}
            >
              <div className="breakdown-number" style={{ color: '#d97706' }}>
                {(breakdown.misleading || 0) + (breakdown.unverifiable || 0)}
              </div>
              <div className="breakdown-label" style={{ color: '#d97706' }}>Misleading</div>
            </div>
          )}
          <div
            className="breakdown-pill"
            style={{ background: 'rgba(79,70,229,0.06)', border: '1px solid rgba(79,70,229,0.15)' }}
          >
            <div className="breakdown-number" style={{ color: '#4f46e5' }}>{breakdown.total}</div>
            <div className="breakdown-label" style={{ color: '#4f46e5' }}>Total</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OverallVerdictBanner;
