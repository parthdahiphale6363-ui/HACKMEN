'use client';

import React, { useEffect, useState } from 'react';

export default function MistralCatFooter() {
  const [theme, setTheme] = useState<'night' | 'day'>('night');

  useEffect(() => {
    // Check current theme
    const saved = localStorage.getItem('pixel_theme') as 'night' | 'day' | null;
    if (saved) setTheme(saved);

    const onThemeChange = (e: Event) => {
      const customEvent = e as CustomEvent<'night' | 'day'>;
      if (customEvent.detail) setTheme(customEvent.detail);
    };

    window.addEventListener('pixel-theme-change', onThemeChange);
    return () => window.removeEventListener('pixel-theme-change', onThemeChange);
  }, []);

  const toggleTheme = (newTheme: 'night' | 'day') => {
    setTheme(newTheme);
    localStorage.setItem('pixel_theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme === 'night' ? 'dark' : 'light');
    window.dispatchEvent(new CustomEvent('pixel-theme-change', { detail: newTheme }));
  };

  return (
    <footer className="mistral-footer-root">
      <div className="mistral-nav-wrap">


        {/* ── Sub-bar: Day/Night Pill Switch (Matches Mistral Screenshot) ── */}
        <div className="mistral-sub-bar">
          <div className="footer-theme-pill">
            <button
              className={`theme-icon-btn ${theme === 'day' ? 'active' : ''}`}
              onClick={() => toggleTheme('day')}
              title="Switch to Daytime Meadow mode"
              aria-label="Switch to Daytime mode"
            >
              ☀
            </button>
            <button
              className={`theme-icon-btn ${theme === 'night' ? 'active' : ''}`}
              onClick={() => toggleTheme('night')}
              title="Switch to Starry Midnight mode"
              aria-label="Switch to Night mode"
            >
              ☾
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}
