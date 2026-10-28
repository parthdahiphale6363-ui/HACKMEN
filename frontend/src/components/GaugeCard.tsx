'use client';

import React from 'react';

interface GaugeCardProps {
  icon: string;
  label: string;
  value: number;
  color: string;
}

export function GaugeCard({ icon, label, value, color }: GaugeCardProps) {
  const status = value >= 75 ? 'Good' : value >= 50 ? 'Moderate' : 'At Risk';
  const statusColor = value >= 75 ? '#059669' : value >= 50 ? '#d97706' : '#dc2626';

  return (
    <div
      className="score-gauge-card"
      style={{ '--gauge-color': color } as React.CSSProperties}
    >
      <div className="gauge-icon">{icon}</div>
      <div className="gauge-label">{label}</div>
      <div className="gauge-value" style={{ color }}>{value.toFixed(0)}</div>
      <div className="gauge-bar-bg">
        <div className="gauge-bar-fill" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
      <div className="gauge-status" style={{ color: statusColor }}>{status}</div>
    </div>
  );
}

export default GaugeCard;
