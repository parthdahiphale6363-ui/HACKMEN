'use client';

import { useState, useEffect, useRef } from 'react';
import { getYouTubeId, detectPlatform, ClaimWithVerdict, VerdictLabel, DomainTrust } from '../lib/mockData';
import MistralCatFooter from '../components/MistralCatFooter';
import PixelWorldBackground, { PixelAnimationControls } from '../components/PixelWorldBackground';
import { ExportDossierModal } from '../components/ExportDossierModal';
import { SystemHealthModal } from '../components/SystemHealthModal';
import { GaugeCard } from '../components/GaugeCard';
import { OverallVerdictBanner } from '../components/OverallVerdictBanner';
import { ForensicsPanel } from '../components/ForensicsPanel';
import { OSINTPanel } from '../components/OSINTPanel';
import { DataMiningPanel } from '../components/DataMiningPanel';
import { ClaimCard } from '../components/ClaimCard';
import { getVerdictCatStyle } from '../lib/styleUtils';
import { ForensicsReport, OSINTReport, DataMiningReport, VerdictBreakdown } from '../types/reports';

// ─── Types ──────────────────────────────────────────────────────────────────────
type Stage =
  | 'idle' | 'extracting' | 'transcribing' | 'extracting_claims'
  | 'forensics_analysis' | 'osint_collection' | 'data_mining' | 'verifying'
  | 'done' | 'no_claims_found' | 'extraction_failed' | 'failed';

const PIPELINE_STAGES: Stage[] = [
  'extracting', 'transcribing', 'extracting_claims',
  'forensics_analysis', 'verifying', 'osint_collection', 'data_mining', 'done'
];

const STAGE_LABELS: Record<string, string> = {
  extracting: 'Download', transcribing: 'Transcribe',
  extracting_claims: 'Claims', forensics_analysis: 'Forensics',
  osint_collection: 'OSINT', data_mining: 'Data Mining',
  verifying: 'Verify', done: 'Done',
};
const STAGE_ICONS: Record<string, string> = {
  extracting: '↓', transcribing: '◉', extracting_claims: '◈',
  forensics_analysis: '◇', osint_collection: '◎', data_mining: '▦',
  verifying: '⊘', done: '✓',
};

const VERDICT_ICON: Record<string, string> = {
  true: '✓', false: '✗', misleading: '⚠', unverifiable: '⚠'
};
const VERDICT_COLOR: Record<string, string> = {
  true: '#10b981', false: '#f43f5e', misleading: '#f59e0b', unverifiable: '#f59e0b'
};
const TRUST_LABEL: Record<DomainTrust, string> = {
  high: '✓ High Trust', medium: '~ Medium', low: '⚠ Low', blocked: '✗ Blocked'
};

const STAGE_MSG: Partial<Record<Stage, string>> = {
  extracting: 'Downloading video & extracting audio via yt-dlp…',
  transcribing: 'Transcribing with Groq Whisper AI — this may take a minute…',
  extracting_claims: 'Analysing transcript with LLM to extract verifiable claims…',
  forensics_analysis: 'Running deepfake detection & forensic analysis…',
  osint_collection: 'Collecting OSINT: news, social, geolocation & reverse search…',
  data_mining: 'Running data mining: classification, clustering, outlier detection…',
  verifying: 'Fact-checking each claim with live web search & LLM reasoning…',
};


// ─── Main Page ────────────────────────────────────────────────────────────────────
export default function Home() {
  const [url, setUrl] = useState('');
  const [stage, setStage] = useState<Stage>('idle');
  const [progress, setProgress] = useState(0);
  const [ytId, setYtId] = useState<string | null>(null);
  const [platform, setPlatform] = useState<string>('youtube');
  const [transcriptLines, setTranscriptLines] = useState<{ time: string; text: string }[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [realClaims, setRealClaims] = useState<ClaimWithVerdict[]>([]);
  const [overallVerdict, setOverallVerdict] = useState<string | null>(null);
  const [verdictBreakdown, setVerdictBreakdown] = useState<VerdictBreakdown | null>(null);
  const [finalVerdictCategory, setFinalVerdictCategory] = useState<string>('Unverified');
  const [overallConfidence, setOverallConfidence] = useState<number>(0);
  const [videoScore, setVideoScore] = useState<number>(0);
  const [audioScore, setAudioScore] = useState<number>(0);
  const [metadataScore, setMetadataScore] = useState<number>(0);
  const [osintScore, setOsintScore] = useState<number>(0);
  const [dmScore, setDmScore] = useState<number>(0);
  const [forensicsReport, setForensicsReport] = useState<ForensicsReport | null>(null);
  const [osintReport, setOsintReport] = useState<OSINTReport | null>(null);
  const [dmReport, setDmReport] = useState<DataMiningReport | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // 10/10 Interactive Modals & Filtering States
  const [showExportModal, setShowExportModal] = useState(false);
  const [showHealthModal, setShowHealthModal] = useState(false);
  const [claimFilter, setClaimFilter] = useState<'all' | 'true' | 'false' | 'misleading'>('all');
  const [claimSearch, setClaimSearch] = useState('');
  const [seekSec, setSeekSec] = useState<number | null>(null);
  const [activeDemoCase, setActiveDemoCase] = useState<string | null>(null);
  const [idleTab, setIdleTab] = useState<'cases' | 'pipeline'>('cases');

  const stageIndex = PIPELINE_STAGES.indexOf(stage as any);
  const isProcessing = !['idle', 'done', 'no_claims_found', 'extraction_failed', 'failed'].includes(stage);

  // Lock scrolling strictly on idle landing page
  useEffect(() => {
    if (stage === 'idle') {
      document.documentElement.classList.add('idle-no-scroll');
      document.body.classList.add('idle-no-scroll');
    } else {
      document.documentElement.classList.remove('idle-no-scroll');
      document.body.classList.remove('idle-no-scroll');
    }
    return () => {
      document.documentElement.classList.remove('idle-no-scroll');
      document.body.classList.remove('idle-no-scroll');
    };
  }, [stage]);

  // ── Poll Job Status + incremental results ──
  useEffect(() => {
    if (!jobId || !isProcessing) return;
    const poll = async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) {
          if (res.status === 404) {
            setErrorMessage('Job session not found or server was restarted. Please re-submit your analysis.');
            setStage('failed');
            return true;
          }
          return false;
        }
        const job = await res.json();
        setProgress(job.progress_percent ?? 0);
        const s = job.status as Stage;

        if (s === 'failed') { setErrorMessage(job.error_message || 'Unexpected error.'); setStage('failed'); return true; }
        if (s === 'extraction_failed') { setErrorMessage(job.error_message || 'Claim extraction failed.'); setStage('extraction_failed'); return true; }
        if (s === 'no_claims_found') {
          setOverallVerdict(job.overall_verdict || 'No verifiable factual claims found');
          setVerdictBreakdown(job.verdict_breakdown || {});
          setStage('no_claims_found'); return true;
        }

        const validStages: Stage[] = ['extracting', 'transcribing', 'extracting_claims', 'forensics_analysis', 'verifying', 'osint_collection', 'data_mining'];
        if (validStages.includes(s)) setStage(s);

        // Incremental: fetch transcript as soon as available
        if (['extracting_claims', 'forensics_analysis', 'verifying', 'osint_collection', 'data_mining'].includes(s)) {
          try {
            const tRes = await fetch(`/api/jobs/${jobId}/transcript`);
            if (tRes.ok) {
              const tData = await tRes.json();
              if (Array.isArray(tData) && tData.length > 0) {
                setTranscriptLines(tData.map((seg: any) => ({
                  time: `${String(Math.floor(seg.start / 60)).padStart(2, '0')}:${String(Math.floor(seg.start % 60)).padStart(2, '0')}`,
                  text: seg.text,
                })));
              }
            }
          } catch {}
        }

        // Incremental: fetch claims as they are verified
        if (['verifying', 'osint_collection', 'data_mining'].includes(s)) {
          try {
            const cRes = await fetch(`/api/jobs/${jobId}/claims`);
            if (cRes.ok) {
              const claims = await cRes.json();
              if (Array.isArray(claims) && claims.length > 0) setRealClaims(claims);
            }
          } catch {}
        }

        // Incremental: fetch forensics when ready
        if (['forensics_analysis', 'verifying', 'osint_collection', 'data_mining'].includes(s)) {
          try {
            const fRes = await fetch(`/api/jobs/${jobId}/forensics`);
            if (fRes.ok) setForensicsReport(await fRes.json());
          } catch {}
        }

        if (s === 'done') {
          const tRes = await fetch(`/api/jobs/${jobId}/transcript`);
          const tData = await tRes.json();
          setTranscriptLines((tData as any[]).map((seg: any) => ({
            time: `${String(Math.floor(seg.start / 60)).padStart(2, '0')}:${String(Math.floor(seg.start % 60)).padStart(2, '0')}`,
            text: seg.text,
          })));
          const cRes = await fetch(`/api/jobs/${jobId}/claims`);
          setRealClaims(await cRes.json());
          try { const fRes = await fetch(`/api/jobs/${jobId}/forensics`); if (fRes.ok) setForensicsReport(await fRes.json()); } catch {}
          try { const oRes = await fetch(`/api/jobs/${jobId}/osint`); if (oRes.ok) setOsintReport(await oRes.json()); } catch {}
          try { const dRes = await fetch(`/api/jobs/${jobId}/dm_report`); if (dRes.ok) setDmReport(await dRes.json()); } catch {}
          setOverallVerdict(job.overall_verdict || null);
          setVerdictBreakdown(job.verdict_breakdown || null);
          setFinalVerdictCategory(job.final_verdict_category || 'Unverified');
          setOverallConfidence(job.overall_confidence || 0);
          setVideoScore(job.video_score || 0);
          setAudioScore(job.audio_score || 0);
          setMetadataScore(job.metadata_score || 0);
          setOsintScore(job.osint_score || 0);
          setDmScore(job.dm_score || 0);
          setStage('done');
          return true;
        }
      } catch (e) { console.error(e); }
      return false;
    };

    poll();
    const interval = setInterval(async () => {
      const finished = await poll();
      if (finished) clearInterval(interval);
    }, 8000);
    return () => clearInterval(interval);
  }, [jobId, isProcessing]);

  useEffect(() => { transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [transcriptLines]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUrl = url.trim();
    if (!cleanUrl) return;

    // Validate that input is specifically a YouTube Shorts URL
    const isShorts = cleanUrl.includes('/shorts/') || cleanUrl.includes('shorts/');
    const isLocalOrTest = cleanUrl.includes('localhost') || cleanUrl.includes('127.0.0.1') || cleanUrl.includes('example.com') || cleanUrl.startsWith('/');
    
    if (!isShorts && !isLocalOrTest) {
      setErrorMessage('Please enter only a YouTube Shorts URL (e.g., https://www.youtube.com/shorts/VIDEO_ID). TruthLens AI is designed specifically for short-form viral video verification.');
      setStage('failed');
      return;
    }

    setYtId(getYouTubeId(cleanUrl)); setPlatform(detectPlatform(cleanUrl));
    setTranscriptLines([]); setRealClaims([]); setJobId(null);
    setOverallVerdict(null); setVerdictBreakdown(null); setErrorMessage(null);
    setForensicsReport(null); setOsintReport(null); setDmReport(null);
    setFinalVerdictCategory('Unverified'); setOverallConfidence(0);
    setVideoScore(0); setAudioScore(0); setMetadataScore(0); setOsintScore(0); setDmScore(0);
    setActiveDemoCase(null); setSeekSec(null); setClaimFilter('all'); setClaimSearch('');
    setStage('extracting'); setProgress(5);
    try {
      const res = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ video_url: cleanUrl }) });
      if (res.ok) { const job = await res.json(); setJobId(job.id); }
      else { setErrorMessage('Failed to submit job. Is the backend running?'); setStage('failed'); }
    } catch { setErrorMessage('Failed to connect to backend. Please check that the server is running.'); setStage('failed'); }
  };

  const handleSeek = (seconds: number) => {
    setSeekSec(seconds);
  };

  const loadDemoCase = async (caseKey: string) => {
    try {
      const res = await fetch('/api/jobs/demo-cases');
      if (!res.ok) return;
      const data = await res.json();
      const demo = data[caseKey];
      if (!demo) return;

      setActiveDemoCase(caseKey);
      setUrl(demo.video_url);
      setYtId(getYouTubeId(demo.video_url));
      setPlatform(demo.platform || 'youtube');
      setJobId(demo.id);
      setTranscriptLines(demo.transcript.map((seg: any) => ({
        time: `${String(Math.floor(seg.start / 60)).padStart(2, '0')}:${String(Math.floor(seg.start % 60)).padStart(2, '0')}`,
        text: seg.text,
      })));
      setRealClaims(demo.claims);
      setForensicsReport(demo.forensics);
      setOsintReport(demo.osint);
      setDmReport(demo.dm_report);
      setOverallVerdict(demo.overall_verdict);
      setVerdictBreakdown(demo.verdict_breakdown);
      setFinalVerdictCategory(demo.final_verdict_category);
      setOverallConfidence(demo.overall_confidence);
      setVideoScore(demo.video_score);
      setAudioScore(demo.audio_score);
      setMetadataScore(demo.metadata_score);
      setOsintScore(demo.osint_score);
      setDmScore(demo.dm_score);
      setSeekSec(null);
      setClaimFilter('all');
      setClaimSearch('');
      setStage('done');
    } catch (err) {
      console.error('Failed to load demo case:', err);
    }
  };

  const reset = () => {
    setStage('idle'); setUrl(''); setProgress(0); setYtId(null);
    setTranscriptLines([]); setRealClaims([]); setJobId(null);
    setOverallVerdict(null); setVerdictBreakdown(null); setErrorMessage(null);
    setForensicsReport(null); setOsintReport(null); setDmReport(null);
    setFinalVerdictCategory('Unverified'); setOverallConfidence(0);
    setVideoScore(0); setAudioScore(0); setMetadataScore(0); setOsintScore(0); setDmScore(0);
    setActiveDemoCase(null); setSeekSec(null); setClaimFilter('all'); setClaimSearch('');
  };

  const MODULE_CARDS = [
    { icon: '↓', name: 'Data Collection', desc: 'Audio extraction & video metadata' },
    { icon: '◇', name: 'Forensics', desc: 'Deepfake, voice-clone & manipulation detection' },
    { icon: '▦', name: 'Data Mining', desc: 'Classification, clustering & outlier detection' },
    { icon: '◈', name: 'LLM Analysis', desc: 'Groq LLM reasoning & claim extraction' },
    { icon: '⊘', name: 'Fact Checking', desc: 'Live web search verification per claim' },
    { icon: '◻', name: 'Explainable AI', desc: 'Confidence metrics, red flags & evidence chain' },
  ];

  return (
    <>
      <PixelWorldBackground />
      <div className={`page-wrap${stage === 'idle' ? ' idle-page-wrap' : ''}`}>
        {/* ── Top Brand Bar ── */}
        <div className="top-brand-bar">
          <div className="top-brand-left">
            <div className="brand-badge-pill">
              <span className="brand-dot" />
              <span className="brand-name">TruthLens AI</span>
              <span className="brand-sep">•</span>
              <span className="brand-tag">FORENSICS ENGINE v2.4</span>
            </div>
            <button
              type="button"
              className="system-health-pill"
              onClick={() => setShowHealthModal(true)}
              title="Inspect live system diagnostics & API circuit breakers"
            >
              <span className="live-status-dot" />
              <span>System: Operational</span>
              <span className="system-health-ping">[Diagnostics ↗]</span>
            </button>
          </div>
          <div className="top-brand-right">
            <PixelAnimationControls />
          </div>
        </div>

      {/* ── Hero & Main Content ── */}
      {stage === 'idle' ? (
        <div className="idle-hero-center">
          <header className="site-header">
            <div className="site-header-badge">
              <span className="badge-sparkle">✦</span>
              RESEARCH-GRADE FORENSICS • EXPLAINABLE AI • OSINT
            </div>
            <h1 className="hero-title">
              Multimodal Video Forensics
              <span className="gradient-highlight">
                <span className="title-amp">&amp;</span> Fact-Checking Engine
              </span>
            </h1>
            <p className="hero-subtitle">
              Detect deepfakes, inspect voice &amp; video forensics, mine <span style={{ whiteSpace: 'nowrap' }}>cross-platform</span> OSINT signals,
              and verify claims with explainable AI verdicts.
            </p>
            <div className="pipeline-stepper-ribbon">
              {[
                { icon: '↓', label: 'Ingest' },
                { icon: '◉', label: 'Transcribe' },
                { icon: '◈', label: 'Claims' },
                { icon: '◇', label: 'Forensics' },
                { icon: '▦', label: 'Data Mining' },
                { icon: '⊘', label: 'Verify' },
                { icon: '✓', label: 'Verdict' },
              ].map((step, idx, arr) => (
                <div key={step.label} className="stepper-item">
                  <div className="stepper-pill">
                    <span className="stepper-icon">{step.icon}</span>
                    <span className="stepper-label">{step.label}</span>
                  </div>
                  {idx < arr.length - 1 && <span className="stepper-arrow">›</span>}
                </div>
              ))}
            </div>
          </header>

          <div className="url-section">
          <form onSubmit={handleSubmit} className="url-form-container">
            <div className="url-command-bar">
              <div className="url-platform-icon" title="YouTube Shorts Input">
                <span className="yt-badge">▶</span>
              </div>
              <input
                id="video-url-input"
                type="url"
                className="url-input"
                placeholder="Paste YouTube Shorts URL only (e.g., https://www.youtube.com/shorts/…)…"
                value={url}
                onChange={e => setUrl(e.target.value)}
                aria-label="YouTube Shorts URL"
                required
              />
              {url && (
                <button
                  type="button"
                  className="url-clear-btn"
                  onClick={() => setUrl('')}
                  title="Clear input"
                  aria-label="Clear URL input"
                >
                  ✕
                </button>
              )}
              <button id="analyze-btn" type="submit" className="btn-analyze" aria-label="Analyze YouTube Shorts video">
                <span className="btn-sparkle" aria-hidden="true">⚡</span>
                <span>Analyze Shorts</span>
              </button>
            </div>
          </form>

          {/* Unified Sleek Showcase Console */}
          <div className="glass idle-showcase-box">
            <div className="showcase-nav-bar">
              <div className="showcase-tabs">
                <button
                  type="button"
                  className={`showcase-tab ${idleTab === 'cases' ? 'active' : ''}`}
                  onClick={() => setIdleTab('cases')}
                >
                  <span className="tab-sparkle">✨</span>
                  <span>Instant Case Studies</span>
                  <span className="tab-pill-count">3</span>
                </button>
                <button
                  type="button"
                  className={`showcase-tab ${idleTab === 'pipeline' ? 'active' : ''}`}
                  onClick={() => setIdleTab('pipeline')}
                >
                  <span className="tab-sparkle">🔬</span>
                  <span>Verification Pipeline</span>
                  <span className="tab-pill-count">6 Stages</span>
                </button>
              </div>
              <div className="showcase-badge-meta">
                {idleTab === 'cases' ? (
                  <span className="showcase-meta-tag">⚡ Zero-Latency Instant Inspection</span>
                ) : (
                  <span className="showcase-meta-tag">🛡️ Automated Multimodal Intelligence</span>
                )}
              </div>
            </div>

            {idleTab === 'cases' ? (
              <div className="demo-cards-row">
                <div className="demo-card" onClick={() => loadDemoCase('deepfake_scam')} title="Click to inspect this real deepfake case">
                  <div className="demo-card-top">
                    <span className="demo-card-icon">⚡</span>
                    <span className="demo-card-badge" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>Deepfake 94%</span>
                  </div>
                  <div className="demo-card-title">Elon Musk AI Scam &amp; Crypto Bait</div>
                  <div className="demo-card-desc">Synthetic voice cloning, ELA warping, and advance-fee scam veto.</div>
                  <div className="demo-card-action">Inspect Case ↗</div>
                </div>

                <div className="demo-card" onClick={() => loadDemoCase('science_myths')} title="Click to inspect this peer-reviewed science fact-check">
                  <div className="demo-card-top">
                    <span className="demo-card-icon">🧬</span>
                    <span className="demo-card-badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>Verified 89%</span>
                  </div>
                  <div className="demo-card-title">Venom Genes &amp; Human Empathy</div>
                  <div className="demo-card-desc">PNAS genomics &amp; Anthrozoös psychology peer-reviewed validation.</div>
                  <div className="demo-card-action">Inspect Case ↗</div>
                </div>

                <div className="demo-card" onClick={() => loadDemoCase('geopolitical_disinfo')} title="Click to inspect this video CGI manipulation case">
                  <div className="demo-card-top">
                    <span className="demo-card-icon">🛡️</span>
                    <span className="demo-card-badge" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>Manipulated 96%</span>
                  </div>
                  <div className="demo-card-title">Recycled Combat Video &amp; Bot CGI</div>
                  <div className="demo-card-desc">ARMA 3 video game CGI recycled as live combat with IFCN debunks.</div>
                  <div className="demo-card-action">Inspect Case ↗</div>
                </div>
              </div>
            ) : (
              <div className="showcase-pipeline-view">
                <div className="module-grid">
                  {MODULE_CARDS.map(m => (
                    <div key={m.name} className="module-card">
                      <div className="module-card-top">
                        <div className="module-icon">{m.icon}</div>
                        <div className="module-name">{m.name}</div>
                      </div>
                      <div className="module-desc">{m.desc}</div>
                    </div>
                  ))}
                </div>
                {/* Capability tags */}
                <div className="floating-stats-row">
                  {[
                    { label: 'Groq LLM', sublabel: 'Llama 3.3 70B' },
                    { label: 'Live Search', sublabel: 'DuckDuckGo Engine' },
                    { label: 'Data Mining', sublabel: 'Pattern & Outliers' },
                    { label: 'Forensics', sublabel: 'Deepfake & Voice' },
                  ].map(s => (
                    <div key={s.label} className="floating-stat">
                      <span className="stat-label">{s.label}</span>
                      <span className="stat-sublabel">{s.sublabel}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      ) : (
        <header className="site-header">
          <div className="site-header-badge">
            <span className="badge-sparkle">✦</span>
            RESEARCH-GRADE FORENSICS • EXPLAINABLE AI • OSINT
          </div>
          <h1 className="hero-title">
            Multimodal Video Forensics
            <span className="gradient-highlight">
              <span className="title-amp">&amp;</span> Fact-Checking Engine
            </span>
          </h1>
          <p className="hero-subtitle">
            Detect deepfakes, inspect voice &amp; video forensics, mine <span style={{ whiteSpace: 'nowrap' }}>cross-platform</span> OSINT signals,
            and verify claims with explainable AI verdicts.
          </p>
        </header>
      )}

      {/* ── Error States ── */}
      {(stage === 'failed' || stage === 'extraction_failed') && (
        <div className="error-box" role="alert" aria-live="assertive">
          <p style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }} aria-hidden="true">⚠️</p>
          <h2 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '1.4rem', color: '#dc2626', marginBottom: '0.5rem' }}>
            {stage === 'extraction_failed' ? 'Claim Extraction Failed' : 'Processing Failed'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>{errorMessage}</p>
          <button className="btn-reset" onClick={reset} style={{ padding: '0.75rem 2rem' }} aria-label="Try analysis again">↩ Try Again</button>
        </div>
      )}

      {/* ── Processing View ── */}
      {isProcessing && (
        <>
          <div className="glass pipeline-wrap" style={{ marginBottom: '1.5rem', position: 'relative', overflow: 'hidden' }}>
            <div className="scan-ray" aria-hidden="true" />
            <div className="pipeline-stages">
              {PIPELINE_STAGES.filter(s => s !== 'done').map((s, i) => {
                const si = PIPELINE_STAGES.indexOf(s);
                const isDone = stageIndex > si;
                const isActive = stageIndex === si;
                return (
                  <div key={s} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                    <div className="stage-dot-wrap" style={{ flex: 'none', minWidth: 52 }}>
                      <div className={`stage-dot${isActive ? ' active' : isDone ? ' done' : ''}`}>
                        {isDone ? '✓' : STAGE_ICONS[s]}
                      </div>
                      <span className={`stage-label${isActive ? ' active' : isDone ? ' done' : ''}`}>{STAGE_LABELS[s]}</span>
                    </div>
                    {i < PIPELINE_STAGES.filter(s => s !== 'done').length - 1 && (
                      <div className={`stage-connector${isDone ? ' active' : ''}`} style={{ flex: 1 }} />
                    )}
                  </div>
                );
              })}
            </div>
            <div className="progress-bar-wrap">
              <div
                className="progress-bar-fill"
                role="progressbar"
                aria-valuenow={progress}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Video analysis progress"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <div className="processing-status" role="status" aria-live="polite">
              <div className="status-dot" aria-hidden="true" />
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{STAGE_MSG[stage] || 'Processing…'}</p>
            </div>
          </div>

          <div className="two-col">
            <div className="glass" style={{ overflow: 'hidden', borderRadius: '18px' }}>
              <div className="video-preview-wrap">
                {ytId ? (
                  <iframe src={`https://www.youtube.com/embed/${ytId}?autoplay=1&mute=1&controls=1&rel=0`} allowFullScreen allow="autoplay" title="Video Preview" />
                ) : (
                  <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>📹 Video preview not available</div>
                )}
              </div>
              <div className="video-meta">
                <span className={`platform-badge platform-${platform}`}>{platform === 'youtube' ? '▶' : '📸'} {platform}</span>
              </div>
            </div>

            <div className="glass transcript-panel" style={{ borderRadius: '18px', maxHeight: '340px', overflowY: 'auto' }}>
              <p className="panel-label">
                {stage === 'verifying' && realClaims.length > 0
                  ? `Verified ${realClaims.length} claim${realClaims.length !== 1 ? 's' : ''} so far…`
                  : stage === 'transcribing' ? <><span className="live-dot" />Transcribing audio…</> :
                  stage === 'forensics_analysis' ? 'Running forensic analysis…' :
                  stage === 'osint_collection' ? 'Collecting OSINT data…' :
                  stage === 'data_mining' ? 'Running data mining…' :
                  stage === 'extracting_claims' ? 'Extracting key claims…' :
                  stage === 'verifying' ? 'Verifying claims via web…' : 'Transcript'}
              </p>
              {realClaims.length > 0 && ['verifying', 'osint_collection', 'data_mining'].includes(stage) ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  {realClaims.map((item, i) => (
                    <div key={i} style={{ background: 'rgba(59,158,255,0.04)', border: '1px solid rgba(59,158,255,0.1)', borderRadius: '10px', padding: '0.65rem 0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.3rem' }}>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 700 }}>Claim #{i + 1}</span>
                        <span className={`badge badge-${item.verdict?.label || 'unverifiable'}`}>{(item.verdict?.label || 'unverified').toUpperCase()}</span>
                      </div>
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>"{item.claim.normalized_text}"</p>
                      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        {item.verdict.evidence?.length || 0} sources · {Math.round(item.verdict.confidence * 100)}% confidence
                      </p>
                    </div>
                  ))}
                </div>
              ) : transcriptLines.length > 0 ? (
                <div className="transcript-text">
                  {transcriptLines.map((line, i) => (
                    <div key={i} className="transcript-segment">
                      <span className="segment-time">[{line.time}]</span>{line.text}
                    </div>
                  ))}
                  <div ref={transcriptEndRef} />
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '0.75rem', minHeight: 200 }}>
                  <div style={{ width: 36, height: 36, border: '3px solid #e2e8f0', borderTop: '3px solid #4f46e5', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', textAlign: 'center' }}>
                    {stage === 'extracting' ? 'Downloading audio…' :
                      stage === 'verifying' ? 'Searching web & running Groq analysis per claim — this may take 1–2 min…' :
                      stage === 'forensics_analysis' ? 'Analyzing forensic signals…' :
                      stage === 'osint_collection' ? 'Searching open sources…' :
                      stage === 'data_mining' ? 'Mining patterns in data…' :
                      'Processing — results appear when ready'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ── No Claims ── */}
      {stage === 'no_claims_found' && (
        <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '20px', padding: '3rem', textAlign: 'center' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(100,116,139,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem', fontSize: '1.5rem' }}>?</div>
          <h2 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '1.5rem', color: 'var(--text-heading)', marginBottom: '0.5rem' }}>No Verifiable Claims Found</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', maxWidth: 500, margin: '0 auto 1.5rem', lineHeight: 1.7 }}>
            The AI analysed the full transcript but found no independently verifiable factual claims. The video may be entertainment, opinion, or informal conversation.
          </p>
          <button className="btn-reset" onClick={reset} style={{ padding: '0.75rem 2rem' }}>Analyze Another Video</button>
        </div>
      )}

      {/* ── Results ── */}
      {stage === 'done' && (
        <div style={{ animation: 'fadeUp 0.5s ease' }}>
          {/* Meta Bar */}
          <div className="glass results-meta-bar" style={{ borderRadius: '16px', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                <h2 style={{ fontFamily: 'Outfit, sans-serif', fontSize: '1.25rem', margin: 0 }}>
                  {realClaims.length > 0
                    ? `Analysis Complete — ${realClaims.length} claim${realClaims.length !== 1 ? 's' : ''} verified`
                    : 'Visual Forensics Analysis Complete'}
                </h2>
                {realClaims.length === 0 && (
                  <span style={{ fontSize: '0.68rem', fontWeight: 800, padding: '0.2rem 0.6rem', borderRadius: '6px', background: 'rgba(236, 72, 153, 0.15)', color: '#f472b6', border: '1px solid rgba(236, 72, 153, 0.35)', textTransform: 'uppercase' }}>
                    Non-Verbal / Silent Media
                  </span>
                )}
                {activeDemoCase && (
                  <span style={{ fontSize: '0.65rem', fontWeight: 800, padding: '0.15rem 0.5rem', borderRadius: '6px', background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.4)', textTransform: 'uppercase' }}>
                    Demo Case
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0.5rem' }}>
                <a href={url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                  {url.slice(0, 72)}{url.length > 72 ? '…' : ''}
                </a>
              </p>
              <div className="api-status-row">
                <span className="api-status-chip live">Groq AI</span>
                <span className="api-status-chip live">News API</span>
                <span className="api-status-chip live">OSINT Engine</span>
                <span className="api-status-chip live">Forensics</span>
                <span className="api-status-chip live">Data Mining</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn-export"
                onClick={() => setShowExportModal(true)}
                title="Export comprehensive executive audit dossier in Markdown or JSON"
              >
                <span>📥</span>
                <span>Export Dossier</span>
              </button>
              <button className="btn-reset" onClick={reset}>↩ Analyze Another</button>
            </div>
          </div>

          {/* Visual-only media banner if 0 verbal claims */}
          {realClaims.length === 0 && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(236, 72, 153, 0.08))',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              borderRadius: '16px',
              padding: '1.25rem 1.5rem',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '1rem'
            }}>
              <div style={{ fontSize: '1.8rem', lineHeight: 1 }}>🎬</div>
              <div>
                <h4 style={{ margin: '0 0 0.25rem', fontSize: '1rem', color: 'var(--text-heading)', fontWeight: 600 }}>
                  Visual Forensics &amp; AI Generation Audit
                </h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  This video does not contain spoken dialogue or extractable verbal claims. TruthLens AI evaluated visual frame features, 2D FFT frequency spectrum anomalies, keyframe Error Level Analysis (ELA), and C2PA Content Credentials to detect AI generation.
                </p>
              </div>
            </div>
          )}

          {/* Overall Verdict */}
          {overallVerdict && (
            <OverallVerdictBanner
              verdict={overallVerdict}
              breakdown={verdictBreakdown || { true: 0, false: 0, misleading: 0, unverifiable: 0, total: 0 }}
              category={finalVerdictCategory}
              confidence={overallConfidence}
            />
          )}

          {/* Forensics Panel */}
          {forensicsReport && <ForensicsPanel report={forensicsReport} onSeek={handleSeek} />}

          {/* OSINT Panel */}
          {osintReport && <OSINTPanel report={osintReport} />}

          {/* Data Mining Panel */}
          {dmReport && <DataMiningPanel report={dmReport} />}

          {/* Video + Transcript */}
          <p className="section-title">Video &amp; Transcript Synchronization</p>
          <div className="two-col" style={{ marginBottom: '2rem' }}>
            <div className="glass" style={{ overflow: 'hidden', borderRadius: '18px' }}>
              <div className="video-preview-wrap">
                {ytId ? (
                  <iframe
                    src={`https://www.youtube.com/embed/${ytId}?${seekSec != null ? `start=${Math.floor(seekSec)}&autoplay=1&` : ''}controls=1&rel=0`}
                    allowFullScreen
                    allow="autoplay"
                    title="Video"
                  />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>📹 Not available</div>
                )}
              </div>
              <div className="video-meta">
                <span className={`platform-badge platform-${platform}`}>{platform}</span>
                {seekSec != null && (
                  <span style={{ fontSize: '0.72rem', color: '#818cf8', fontFamily: 'JetBrains Mono, monospace', fontWeight: 700 }}>
                    ▶ Seeking {String(Math.floor(seekSec / 60)).padStart(2, '0')}:{String(Math.floor(seekSec % 60)).padStart(2, '0')}
                  </span>
                )}
              </div>
            </div>
            <div className="glass transcript-panel" style={{ borderRadius: '18px', maxHeight: '320px', overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                <p className="panel-label" style={{ margin: 0 }}>Full Transcript (Translated to English)</p>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Click timestamp to seek video</span>
              </div>
              <div className="transcript-text">
                {transcriptLines.length > 0 ? (
                  transcriptLines.map((line, i) => {
                    const segSec = (() => {
                      const p = line.time.split(':').map(Number);
                      return p.length === 2 ? p[0] * 60 + p[1] : 0;
                    })();
                    const isHighlighted = seekSec != null && Math.abs(segSec - seekSec) <= 6;
                    return (
                      <div key={i} className={`transcript-segment${isHighlighted ? ' active-seek' : ''}`}>
                        <span
                          className="segment-time"
                          onClick={() => handleSeek(segSec)}
                          style={{ cursor: 'pointer', transition: 'color 0.15s ease' }}
                          title="Click to seek player here"
                        >
                          [{line.time}]
                        </span>
                        {line.text}
                      </div>
                    );
                  })
                ) : (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1.25rem', fontStyle: 'italic', margin: 0, textAlign: 'center' }}>
                    Silent media: no spoken dialogue was recorded or transcribed.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Claim Cards */}
          {realClaims.length > 0 ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <div>
                  <p className="section-title" style={{ marginBottom: '0.2rem' }}>Claim-by-Claim Fact Check</p>
                  <p className="claims-header" style={{ marginBottom: 0 }}>
                    {realClaims.length} factual claims extracted by LLM · verified via live web search · Groq reasoning
                  </p>
                </div>
              </div>

              {/* Filter & Search Bar */}
              <div className="claim-controls-bar">
                <div className="claim-search-wrap">
                  <input
                    type="text"
                    className="claim-search-input"
                    placeholder="Filter claims by keywords, sources, or entities…"
                    value={claimSearch}
                    onChange={e => setClaimSearch(e.target.value)}
                  />
                  {claimSearch && (
                    <button className="claim-search-clear" onClick={() => setClaimSearch('')}>✕</button>
                  )}
                </div>

                <div className="claim-filter-pills">
                  <button
                    type="button"
                    className={`filter-pill${claimFilter === 'all' ? ' active' : ''}`}
                    onClick={() => setClaimFilter('all')}
                  >
                    All ({realClaims.length})
                  </button>
                  {realClaims.filter(c => c.verdict?.label === 'true').length > 0 && (
                    <button
                      type="button"
                      className={`filter-pill${claimFilter === 'true' ? ' active' : ''}`}
                      onClick={() => setClaimFilter('true')}
                      style={claimFilter === 'true' ? { background: 'rgba(16,185,129,0.25)', borderColor: '#10b981', color: '#10b981' } : {}}
                    >
                      ✓ True ({realClaims.filter(c => c.verdict?.label === 'true').length})
                    </button>
                  )}
                  {realClaims.filter(c => c.verdict?.label === 'false').length > 0 && (
                    <button
                      type="button"
                      className={`filter-pill${claimFilter === 'false' ? ' active' : ''}`}
                      onClick={() => setClaimFilter('false')}
                      style={claimFilter === 'false' ? { background: 'rgba(239,68,68,0.25)', borderColor: '#ef4444', color: '#ef4444' } : {}}
                    >
                      ✗ False ({realClaims.filter(c => c.verdict?.label === 'false').length})
                    </button>
                  )}
                  {realClaims.filter(c => c.verdict?.label === 'misleading').length > 0 && (
                    <button
                      type="button"
                      className={`filter-pill${claimFilter === 'misleading' ? ' active' : ''}`}
                      onClick={() => setClaimFilter('misleading')}
                      style={claimFilter === 'misleading' ? { background: 'rgba(245,158,11,0.25)', borderColor: '#f59e0b', color: '#f59e0b' } : {}}
                    >
                      ⚠ Misleading ({realClaims.filter(c => c.verdict?.label === 'misleading').length})
                    </button>
                  )}
                </div>
              </div>

              {(() => {
                const filtered = realClaims.filter(item => {
                  const itemLabel = item.verdict?.label;
                  if (claimFilter !== 'all' && itemLabel !== claimFilter) return false;
                  if (claimSearch.trim()) {
                    const q = claimSearch.toLowerCase();
                    const textMatch = item.claim?.normalized_text?.toLowerCase().includes(q) ||
                                      item.claim?.raw_text?.toLowerCase().includes(q);
                    const reasoningMatch = item.verdict?.reasoning?.toLowerCase().includes(q) ||
                                           item.verdict?.summary?.toLowerCase().includes(q);
                    const sourceMatch = item.verdict?.evidence?.some(e =>
                      e.source_title?.toLowerCase().includes(q) || e.domain?.toLowerCase().includes(q)
                    );
                    return Boolean(textMatch || reasoningMatch || sourceMatch);
                  }
                  return true;
                });

                if (filtered.length === 0) {
                  return (
                    <div style={{ padding: '2.5rem', textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1.5rem' }}>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>No claims matched your search query or filter.</p>
                      <button
                        type="button"
                        onClick={() => { setClaimFilter('all'); setClaimSearch(''); }}
                        style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid #6366f1', color: '#818cf8', borderRadius: '8px', padding: '0.4rem 1rem', fontSize: '0.78rem', cursor: 'pointer', fontWeight: 700 }}
                      >
                        Clear Filter
                      </button>
                    </div>
                  );
                }

                return filtered.map((item, i) => (
                  <ClaimCard
                    key={(item.claim as any).id || i}
                    item={item}
                    index={i}
                    onSeek={handleSeek}
                  />
                ));
              })()}
            </>
          ) : (
            <div className="glass" style={{ borderRadius: '16px', padding: '2rem', textAlign: 'center', marginBottom: '2rem' }}>
              <p className="section-title" style={{ marginBottom: '0.4rem' }}>Claim-by-Claim Fact Check</p>
              <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.92rem' }}>
                No spoken claims were present in this media. Full verification was conducted through visual stream keyframes, 2D FFT spectral profiling, and C2PA Content Credentials in the Forensic Authenticity Hub above.
              </p>
            </div>
          )}

        </div>
      )}

      {/* ── Modals ── */}
      <ExportDossierModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        jobId={jobId || 'audit-dossier'}
        reportData={{
          videoUrl: url,
          overallVerdict: overallVerdict || 'Unverified',
          category: finalVerdictCategory,
          confidence: overallConfidence,
          breakdown: verdictBreakdown || {},
          claims: realClaims,
          forensics: forensicsReport,
          osint: osintReport,
          dmReport: dmReport,
        }}
      />

      <SystemHealthModal
        isOpen={showHealthModal}
        onClose={() => setShowHealthModal(false)}
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
      {stage !== 'idle' && <MistralCatFooter />}
    </>
  );
}
