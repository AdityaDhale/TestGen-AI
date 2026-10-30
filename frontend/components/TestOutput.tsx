'use client';

import React, { useState } from 'react';

interface TestItem {
  name: string;
  status: 'passed' | 'failed' | 'error';
  duration_ms: number;
  error?: string | null;
}

interface ExecutionResult {
  status: string;
  passed: number;
  failed: number;
  errors: number;
  total: number;
  tests: TestItem[];
  stdout: string;
  stderr: string;
  coverage_pct: number;
}

interface TestOutputProps {
  testCode: string | null;
  execution: ExecutionResult | null;
  iterations: number;
}

export default function TestOutput({ testCode, execution, iterations }: TestOutputProps) {
  const [copied, setCopied] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const handleCopy = () => {
    if (testCode) {
      navigator.clipboard.writeText(testCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!testCode && !execution) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📝</div>
        <div className="empty-title">No Tests Yet</div>
        <div className="empty-desc">
          Generated tests and execution results will appear here.
        </div>
      </div>
    );
  }

  const passRate = execution && execution.total > 0
    ? Math.round((execution.passed / execution.total) * 100)
    : 0;

  const statusEmoji: Record<string, string> = {
    passed: '✅',
    failed: '❌',
    error: '⚠️',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* ── Summary stats ── */}
      {execution && (
        <>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.25rem',
            }}
          >
            <span
              className={`status-badge ${
                execution.status === 'passed' ? 'passed' : 'failed'
              }`}
            >
              {execution.status === 'passed' ? '✅' : '❌'}{' '}
              {execution.status === 'passed' ? 'All Passing' : 'Some Failing'}
            </span>
            {iterations > 0 && (
              <span
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  fontWeight: 600,
                }}
              >
                🔧 Auto-fixed in {iterations} iteration{iterations !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          <div className="results-summary">
            <div className="stat-card">
              <div className="stat-value passed">{execution.passed}</div>
              <div className="stat-label">Passed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value failed">{execution.failed + execution.errors}</div>
              <div className="stat-label">Failed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value total">{execution.total}</div>
              <div className="stat-label">Total</div>
            </div>
            <div className="stat-card">
              <div className="stat-value score">{passRate}%</div>
              <div className="stat-label">Pass Rate</div>
            </div>
          </div>

          {/* Coverage bar */}
          <div className="coverage-bar-wrap">
            <div className="coverage-label">
              <span>Pass Rate</span>
              <span style={{ color: passRate >= 80 ? 'var(--green-400)' : 'var(--red-400)' }}>
                {passRate}%
              </span>
            </div>
            <div className="coverage-track">
              <div className="coverage-fill" style={{ width: `${passRate}%` }} />
            </div>
          </div>

          {/* Individual test list */}
          {execution.tests.length > 0 && (
            <div className="test-list">
              {execution.tests.map((t, i) => (
                <div key={i} className={`test-item ${t.status}`}>
                  <span className="test-status-icon">{statusEmoji[t.status] ?? '•'}</span>
                  <span className="test-name">{t.name}</span>
                  {t.duration_ms > 0 && (
                    <span className="test-duration">{t.duration_ms}ms</span>
                  )}
                  {t.error && (
                    <div style={{ width: '100%', gridColumn: '1 / -1' }}>
                      <div className="test-error">{t.error}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Generated test code ── */}
      {testCode && (
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '8px',
            }}
          >
            <span
              style={{
                fontSize: '0.8rem',
                fontWeight: 700,
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              Generated Test File
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                className="copy-btn"
                onClick={() => setShowRaw(!showRaw)}
              >
                {showRaw ? '🙈 Hide' : '👁 View Code'}
              </button>
              <button className="copy-btn" onClick={handleCopy}>
                {copied ? '✅ Copied!' : '📋 Copy'}
              </button>
            </div>
          </div>
          {showRaw && (
            <pre className="test-code-block">{testCode}</pre>
          )}
        </div>
      )}

      {/* ── Raw stdout ── */}
      {execution?.stdout && (
        <details style={{ marginTop: '0.5rem' }}>
          <summary
            style={{
              cursor: 'pointer',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              fontWeight: 600,
              userSelect: 'none',
              marginBottom: '6px',
            }}
          >
            📄 Raw Terminal Output
          </summary>
          <pre
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.75rem',
              background: '#0a0a0a',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px',
              color: '#86efac',
              overflow: 'auto',
              maxHeight: '300px',
              whiteSpace: 'pre-wrap',
            }}
          >
            {execution.stdout}
          </pre>
        </details>
      )}
    </div>
  );
}
