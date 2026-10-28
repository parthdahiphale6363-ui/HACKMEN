'use client';

import React, { useState } from 'react';
import { ClaimWithVerdict, VerdictLabel, DomainTrust } from '../lib/mockData';

const VERDICT_ICON: Record<string, string> = {
  true: '✓',
  false: '✗',
  misleading: '⚠',
  unverifiable: '⚠',
};

const VERDICT_COLOR: Record<string, string> = {
  true: '#10b981',
  false: '#f43f5e',
  misleading: '#f59e0b',
  unverifiable: '#f59e0b',
};

const TRUST_LABEL: Record<DomainTrust, string> = {
  high: '✓ High Trust',
  medium: '~ Medium',
  low: '⚠ Low',
  blocked: '✗ Blocked',
};

interface ClaimCardProps {
  item: ClaimWithVerdict;
  index: number;
  onSeek?: (sec: number) => void;
}

export function ClaimCard({ item, index, onSeek }: ClaimCardProps) {
  const { claim, verdict } = item;
  const [tab, setTab] = useState<'verdict' | 'searches' | 'evidence' | 'ai_chain'>('verdict');
  const pct = Math.round((verdict?.confidence ?? 0.5) * 100);
  const s = verdict?.fact_check_summary || {
    searches_run: verdict?.search_runs?.length || 1,
    sources_found: verdict?.evidence?.length || 0,
    sources_accepted: verdict?.evidence?.length || 0,
    sources_blocked: 0,
    consensus_score: verdict?.confidence ?? 0.5,
    cross_platform_hits: 0,
    llm_rounds: verdict?.llm_checks?.length || 1,
    critic_rejections: 0,
  };
  const vColor = (verdict?.label && VERDICT_COLOR[verdict.label]) || 'var(--text-muted)';

  const timeStr = (claim as { time_str?: string })?.time_str || (
    claim?.timestamp_in_video != null
      ? `${String(Math.floor(claim.timestamp_in_video / 60)).padStart(2, '0')}:${String(Math.floor(claim.timestamp_in_video % 60)).padStart(2, '0')}`
      : null
  );

  const timeSec = claim?.timestamp_in_video != null
    ? claim.timestamp_in_video
    : (claim as { time_str?: string })?.time_str
      ? (() => {
          const parts = ((claim as unknown) as { time_str: string }).time_str.split(':').map(Number);
          return parts.length === 2 ? parts[0] * 60 + parts[1] : 0;
        })()
      : null;

  const searchRuns = verdict?.search_runs || [];
  const evidenceList = verdict?.evidence || [];
  const llmChecks = verdict?.llm_checks || [];

  return (
    <div className="glass claim-card" style={{ animationDelay: `${index * 120}ms` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.75rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', marginBottom: '0.4rem', flexWrap: 'wrap' }}>
            <p style={{ fontSize: '0.66rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.09em', margin: 0, fontWeight: 700 }}>
              Claim #{index + 1}{claim?.language ? ` · ${claim.language.toUpperCase()}` : ''}
            </p>
            {timeStr && onSeek && (
              <button
                type="button"
                className="timestamp-jump-btn"
                onClick={() => onSeek(timeSec ?? 0)}
                title={`Jump video & transcript to ${timeStr}`}
              >
                <span>▶</span>
                <span>{timeStr}</span>
              </button>
            )}
          </div>
          <p style={{ fontSize: '1.02rem', fontWeight: 600, lineHeight: 1.5, color: 'var(--text-primary)' }}>
            "{claim?.normalized_text || claim?.raw_text || ''}"
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem', flexShrink: 0 }}>
          <span className={`badge badge-${verdict?.label || 'unverifiable'}`}>
            {VERDICT_ICON[verdict?.label as VerdictLabel] || '?'} {(verdict?.label || 'unverified').toUpperCase()}
          </span>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: vColor }}>{pct}% confidence</span>
        </div>
      </div>

      {Boolean(((verdict as unknown) as { context?: string })?.context) && (
        <div style={{ background: 'rgba(59,158,255,0.04)', border: '1px solid rgba(59,158,255,0.1)', borderRadius: '10px', padding: '0.6rem 0.85rem', marginBottom: '0.9rem' }}>
          <p style={{ fontSize: '0.68rem', color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.2rem' }}>From Transcript</p>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>"{((verdict as unknown) as { context: string }).context}"</p>
        </div>
      )}

      <div style={{ marginBottom: '1.1rem' }}>
        <div className="confidence-bar-bg" style={{ height: '6px' }}>
          <div className="confidence-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
          <span>0%</span><span style={{ color: vColor, fontWeight: 700 }}>{pct}%</span><span>100%</span>
        </div>
      </div>

      <div className="scorecard" style={{ marginBottom: '1.1rem' }}>
        {[
          ['Searches Run', s.searches_run ?? (searchRuns.length || 1), ''],
          ['Sources Found', s.sources_found ?? evidenceList.length, ''],
          ['Accepted', s.sources_accepted ?? evidenceList.length, 'good'],
          ['Blocked', s.sources_blocked ?? 0, (s.sources_blocked ?? 0) > 0 ? 'bad' : ''],
          ['Consensus', `${Math.round(((s.consensus_score ?? verdict?.confidence ?? 0.5) * 100))}%`, ((s.consensus_score ?? 0.5) >= 0.8) ? 'good' : ((s.consensus_score ?? 0.5) >= 0.6) ? 'warn' : 'bad'],
          ['AI Rounds', s.llm_rounds ?? (llmChecks.length || 1), ''],
        ].map(([label, val, cls]) => (
          <div key={label as string} className="score-cell">
            <div className="score-label">{label}</div>
            <div className={`score-value ${cls}`}>{val}</div>
          </div>
        ))}
      </div>

      <div className={`verdict-banner verdict-banner-${verdict?.label || 'unverifiable'}`} style={{ marginBottom: '1.1rem' }}>
        <span className="verdict-icon">{VERDICT_ICON[verdict?.label as VerdictLabel] || '?'}</span>
        <div>
          <p className="verdict-summary-title">Verdict: {(verdict?.label || 'unverified').toUpperCase()}</p>
          <p className="verdict-summary-text">{verdict?.summary || ''}</p>
        </div>
      </div>

      <div className="tab-bar">
        {(['verdict', 'searches', 'evidence', 'ai_chain'] as const).map(t => (
          <button key={t} className={`tab-btn${tab === t ? ' active' : ''}`} onClick={() => setTab(t)}>
            {{
              verdict: 'Reasoning',
              searches: `Searches (${searchRuns.length || s.searches_run || 1})`,
              evidence: `Evidence (${evidenceList.length})`,
              ai_chain: 'AI Chain'
            }[t]}
          </button>
        ))}
      </div>

      {tab === 'verdict' && (
        <div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.7, borderLeft: '2px solid var(--border-active)', paddingLeft: '0.85rem', marginBottom: '0.85rem' }}>
            {verdict?.reasoning || 'No detailed reasoning available.'}
          </p>

          {/* Atomic Claim Decomposition */}
          {verdict?.atomic_assessments && verdict.atomic_assessments.length > 0 && (
            <div style={{ marginTop: '0.85rem', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border)', borderRadius: '10px', padding: '0.75rem 0.85rem' }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--accent)', marginBottom: '0.55rem' }}>
                Atomic Claim Assessments ({verdict.atomic_assessments.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                {verdict.atomic_assessments.map((atom, aIdx: number) => {
                  const aColor = VERDICT_COLOR[atom.verdict as VerdictLabel] || '#f59e0b';
                  return (
                    <div key={atom.id || aIdx} style={{ background: 'rgba(0,0,0,0.18)', borderRadius: '8px', padding: '0.6rem 0.75rem', borderLeft: `3px solid ${aColor}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                        <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>{atom.atomic_claim}</span>
                        <span className={`badge badge-${atom.verdict || 'misleading'}`} style={{ fontSize: '0.65rem' }}>
                          {(atom.verdict || 'misleading').toUpperCase()}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>{atom.reasoning}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Unresolved Uncertainties */}
          {verdict?.unresolved_uncertainties && verdict.unresolved_uncertainties.length > 0 && (
            <div style={{ marginTop: '0.75rem', background: 'rgba(245, 158, 11, 0.06)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '10px', padding: '0.65rem 0.85rem' }}>
              <div style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#f59e0b', marginBottom: '0.3rem' }}>
                ⚠️ Missing Context & Unresolved Uncertainties
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {verdict.unresolved_uncertainties.map((u: string, uIdx: number) => (
                  <li key={uIdx}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Canonical Audit Hash */}
          {verdict?.canonical_hash && (
            <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              <span>Deterministic Verification Hash:</span>
              <code style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent)' }}>
                {verdict.canonical_hash}
              </code>
            </div>
          )}
        </div>
      )}

      {tab === 'searches' && (
        <div style={{ overflowX: 'auto' }}>
          {searchRuns.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '1rem' }}>No search queries recorded for this claim.</p>
          ) : (
            <table className="search-table">
              <thead><tr><th>#</th><th>Query</th><th>Source</th><th>Results</th><th>Domain</th><th>Trust</th><th>Stance</th></tr></thead>
              <tbody>
                {searchRuns.map((run, i) => (
                  <tr key={i}>
                    <td style={{ color: 'var(--text-muted)', fontWeight: 700 }}>#{i + 1}</td>
                    <td><span className="query-mono">{run.query}</span></td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{run.source_type}</td>
                    <td><span className="results-count">{run.results_found}</span></td>
                    <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{run.top_domain}</td>
                    <td><span className={`trust-pill trust-${run.trust_level}`}>{TRUST_LABEL[run.trust_level as DomainTrust] || run.trust_level}</span></td>
                    <td><span className={`stance-pill stance-${run.stance}`}>{run.stance}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'evidence' && (
        <div>
          {evidenceList.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '1rem' }}>No web evidence found for this claim.</p>
          ) : evidenceList.map((ev, i) => {
            const relPct = Math.round((ev.relevance_score ?? 0.8) * 100);
            const relColor = (ev.relevance_score ?? 0.8) >= 0.85 ? '#059669' : (ev.relevance_score ?? 0.8) >= 0.65 ? '#d97706' : '#64748b';
            return (
              <div key={i} className="ev-card">
                <div className="ev-meta">
                  <span className={`trust-pill trust-${ev.domain_trust}`}>{TRUST_LABEL[ev.domain_trust] || ev.domain_trust}</span>
                  <span className="ev-domain">📍 {ev.domain}</span>
                  <span className="ev-date">📅 {ev.publication_date}</span>
                </div>
                <a href={ev.source_url} target="_blank" rel="noreferrer" className="ev-title">{ev.source_title} ↗</a>
                <p className="ev-snippet">"{ev.snippet}"</p>
                {ev.quote && (
                  <div style={{ margin: '0.45rem 0', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '0.55rem 0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                      <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        {ev.quote_verified ? '✓ Verified Verbatim Passage' : 'Extracted Source Passage'}
                      </span>
                      {ev.quote_location && (
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Location: {ev.quote_location}</span>
                      )}
                    </div>
                    <blockquote style={{ margin: 0, fontSize: '0.8rem', fontStyle: 'italic', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                      "{ev.quote}"
                    </blockquote>
                  </div>
                )}
                {ev.credibility_limitation && (
                  <div style={{ margin: '0.35rem 0', fontSize: '0.72rem', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.15)', padding: '3px 8px', borderRadius: '6px' }}>
                    ⚠️ Limitation: {ev.credibility_limitation}
                  </div>
                )}
                <div className="ev-footer">
                  <span className="ev-stance-icon">
                    {ev.stance === 'supports' || ev.supports_claim === true ? '🟢 Supports' :
                     ev.stance === 'contradicts' || ev.supports_claim === false ? '🔴 Contradicts' :
                     ev.stance === 'mixed' ? '🟡 Mixed' :
                     ev.stance === 'irrelevant' ? '⚪ Irrelevant' : '⚪ Insufficient'}
                  </span>
                  {ev.is_independent === false && (
                    <span style={{ fontSize: '0.68rem', background: 'rgba(148,163,184,0.15)', color: '#94a3b8', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>
                      Syndicated Wire
                    </span>
                  )}
                  <div className="relevance-bar-bg"><div className="relevance-bar-fill" style={{ width: `${relPct}%`, background: relColor }} /></div>
                  <span style={{ fontSize: '0.72rem', color: relColor, fontWeight: 700, flexShrink: 0 }}>Relevance {relPct}%</span>
                </div>
                {ev.explanation && (
                  <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '0.35rem', lineHeight: 1.4 }}>
                    💡 {ev.explanation}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {tab === 'ai_chain' && (
        <div className="agent-chain">
          {llmChecks.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '1rem' }}>No AI chain steps recorded.</p>
          ) : llmChecks.map((check, i) => (
            <div key={i} className="agent-step">
              <div className="agent-left">
                <div className={`agent-icon ${check.passed ? 'pass' : 'fail'}`}>{check.passed ? '✓' : '↩'}</div>
              </div>
              <div className="agent-body">
                <p className="agent-name">{check.agent}</p>
                <p className="agent-role">{check.role}</p>
                <p className="agent-finding">{check.finding}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ClaimCard;
