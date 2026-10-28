export function getVerdictCatStyle(cat: string): { color: string; bg: string; border: string } {
  const lc = (cat || '').toLowerCase();
  if (lc.includes('genuine') || lc.includes('authentic') || lc.includes('supported') || lc === 'true')
    return { color: '#059669', bg: 'rgba(5,150,105,0.07)', border: 'rgba(5,150,105,0.2)' };
  if (lc.includes('deepfake') || lc.includes('synthetic'))
    return { color: '#7c3aed', bg: 'rgba(124,58,237,0.07)', border: 'rgba(124,58,237,0.2)' };
  if (lc.includes('fake') || lc.includes('misinformation') || lc.includes('deceptive') || lc.includes('debunked'))
    return { color: '#dc2626', bg: 'rgba(220,38,38,0.07)', border: 'rgba(220,38,38,0.2)' };
  if (lc.includes('misleading') || lc.includes('sensationalized') || lc.includes('mixed'))
    return { color: '#d97706', bg: 'rgba(217,119,6,0.07)', border: 'rgba(217,119,6,0.2)' };
  if (lc.includes('manipulated') || lc.includes('context'))
    return { color: '#ea580c', bg: 'rgba(234,88,12,0.07)', border: 'rgba(234,88,12,0.2)' };
  if (lc.includes('unsubstantiated') || lc.includes('inconclusive') || lc.includes('low corroboration') || lc.includes('unverified'))
    return { color: '#0284c7', bg: 'rgba(2,132,199,0.07)', border: 'rgba(2,132,199,0.2)' };
  return { color: '#64748b', bg: 'rgba(100,116,139,0.07)', border: 'rgba(100,116,139,0.2)' };
}
