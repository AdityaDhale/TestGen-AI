'use client';

import React, { useState, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import AgentLog from '@/components/AgentLog';
import TestOutput from '@/components/TestOutput';

// Monaco editor — load client-side only
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

const DEMO_CODE = `def calculate_discount(price: float, discount_pct: float, min_price: float = 0.0) -> float:
    """
    Calculate the discounted price.

    Args:
        price: Original price (must be positive)
        discount_pct: Discount percentage (0-100)
        min_price: Minimum allowed price after discount

    Returns:
        Final price after discount, never below min_price

    Raises:
        ValueError: If price is negative or discount is out of range
    """
    if price < 0:
        raise ValueError(f"Price cannot be negative: {price}")
    if not 0 <= discount_pct <= 100:
        raise ValueError(f"Discount must be between 0 and 100, got {discount_pct}")

    discounted = price * (1 - discount_pct / 100)
    return max(discounted, min_price)


def apply_bulk_discounts(items: list[dict]) -> list[dict]:
    """
    Apply discounts to a list of items.
    Each item dict should have 'price', 'discount_pct', and optional 'name'.
    Returns a new list with 'final_price' added to each item.
    """
    if not items:
        return []

    result = []
    for item in items:
        final_price = calculate_discount(
            item['price'],
            item.get('discount_pct', 0)
        )
        result.append({**item, 'final_price': round(final_price, 2)})
    return result
`;

interface LogEntry { step: string; detail: string; }
interface ExecutionResult {
  status: string; passed: number; failed: number; errors: number;
  total: number; tests: any[]; stdout: string; stderr: string; coverage_pct: number;
}

type Tab = 'log' | 'tests';

export default function HomePage() {
  const [code, setCode] = useState(DEMO_CODE);
  const [language] = useState('python');
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('log');
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [testCode, setTestCode] = useState<string | null>(null);
  const [execution, setExecution] = useState<ExecutionResult | null>(null);
  const [iterations, setIterations] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const runPipeline = useCallback(async () => {
    if (!code.trim()) return;

    // Reset state
    setIsRunning(true);
    setLogEntries([]);
    setTestCode(null);
    setExecution(null);
    setIterations(0);
    setError(null);
    setActiveTab('log');

    abortRef.current = new AbortController();

    try {
      const res = await fetch(`${BACKEND_URL}/api/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Server error ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let msg: any;
          try { msg = JSON.parse(raw); } catch { continue; }

          const { event, data } = msg;

          if (event === 'step') {
            setLogEntries(prev => [...prev, { step: data.step, detail: data.detail }]);
          } else if (event === 'tests') {
            setTestCode(data.test_code);
          } else if (event === 'execution') {
            setExecution(data);
          } else if (event === 'complete') {
            setIterations(data.iterations ?? 0);
            setLogEntries(prev => [
              ...prev,
              { step: 'complete', detail: `Done! ${data.summary}` },
            ]);
            setActiveTab('tests');
          } else if (event === 'error') {
            setError(data.message ?? 'Unknown error');
            setLogEntries(prev => [
              ...prev,
              { step: 'error', detail: data.message ?? 'Unknown error' },
            ]);
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      setError(err.message ?? 'Failed to connect to backend.');
      setLogEntries(prev => [
        ...prev,
        { step: 'error', detail: err.message ?? 'Connection failed' },
      ]);
    } finally {
      setIsRunning(false);
    }
  }, [code, language]);

  const stopPipeline = () => {
    abortRef.current?.abort();
    setIsRunning(false);
  };

  const testCount = execution?.total ?? 0;

  return (
    <>
      {/* ── Navbar ── */}
      <nav className="navbar" role="navigation" aria-label="Main navigation">
        <a href="/" className="navbar-brand">
          <div className="navbar-logo" aria-hidden="true">🧪</div>
          <span className="navbar-title">
            Test<span>Gen</span> AI
          </span>
        </a>
        <div className="navbar-badges">
          <span className="badge badge-nebius">⚡ Nebius AI Cloud</span>
          <span className="badge badge-nvidia">🟢 NVIDIA Nemotron</span>
        </div>
      </nav>

      {/* ── Hero ── */}
      <header className="hero">
        <div className="hero-eyebrow" aria-label="Category">
          🏆 Coding &amp; Agentic Engineering Track
        </div>
        <h1>Generate Unit Tests<br />with AI, Instantly</h1>
        <p className="hero-sub">
          Paste your Python code. NVIDIA Nemotron on Nebius AI Cloud analyzes it,
          plans a test strategy, writes comprehensive tests, runs them,
          and fixes failures — automatically.
        </p>
      </header>

      {/* ── Workspace ── */}
      <main className="workspace" id="workspace">
        {/* ── Left: Code Editor ── */}
        <section className="panel" aria-label="Code editor">
          <div className="panel-header">
            <div className="panel-title">
              <span className="panel-icon">📄</span>
              Source Code
            </div>
            <div className="panel-actions">
              <select className="lang-select" defaultValue="python" aria-label="Language">
                <option value="python">Python</option>
              </select>
            </div>
          </div>

          <div className="editor-wrapper" style={{ flex: 1 }}>
            <MonacoEditor
              height="100%"
              defaultLanguage="python"
              theme="vs-dark"
              value={code}
              onChange={(val) => setCode(val ?? '')}
              options={{
                fontSize: 13,
                fontFamily: "'JetBrains Mono', monospace",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbersMinChars: 3,
                padding: { top: 14, bottom: 14 },
                renderLineHighlight: 'gutter',
                smoothScrolling: true,
                cursorBlinking: 'smooth',
                bracketPairColorization: { enabled: true },
                wordWrap: 'on',
              }}
            />
          </div>

          <button
            id="generate-btn"
            className={`btn-generate ${isRunning ? 'loading' : ''}`}
            onClick={isRunning ? stopPipeline : runPipeline}
            disabled={!code.trim()}
            aria-label={isRunning ? 'Stop generation' : 'Generate tests'}
          >
            {isRunning ? (
              <>
                <div className="spinner" aria-hidden="true" />
                Running Pipeline… (click to stop)
              </>
            ) : (
              <>
                <span aria-hidden="true">⚡</span>
                Generate Tests with Nemotron
              </>
            )}
          </button>
        </section>

        {/* ── Right: Results ── */}
        <section className="panel" aria-label="Results panel">
          {/* Tabs */}
          <div className="tabs" role="tablist">
            <button
              id="tab-log"
              className={`tab ${activeTab === 'log' ? 'active' : ''}`}
              onClick={() => setActiveTab('log')}
              role="tab"
              aria-selected={activeTab === 'log'}
              aria-controls="tabpanel-log"
            >
              <span>🤖</span> Agent Log
              {logEntries.length > 0 && (
                <span className="tab-count">{logEntries.length}</span>
              )}
            </button>
            <button
              id="tab-tests"
              className={`tab ${activeTab === 'tests' ? 'active' : ''}`}
              onClick={() => setActiveTab('tests')}
              role="tab"
              aria-selected={activeTab === 'tests'}
              aria-controls="tabpanel-tests"
            >
              <span>🧪</span> Tests &amp; Results
              {testCount > 0 && (
                <span className="tab-count">{testCount}</span>
              )}
            </button>
          </div>

          {/* Error banner */}
          {error && (
            <div className="error-banner" role="alert">
              ❌ <strong>Error:</strong> {error}
              <br />
              <small style={{ color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                Make sure the backend is running at <code>{BACKEND_URL}</code> and your NEBIUS_API_KEY is set.
              </small>
            </div>
          )}

          {/* Tab panels */}
          <div
            id="tabpanel-log"
            className="tab-content"
            role="tabpanel"
            aria-labelledby="tab-log"
            hidden={activeTab !== 'log'}
          >
            <AgentLog entries={logEntries} isRunning={isRunning} />
          </div>

          <div
            id="tabpanel-tests"
            className="tab-content"
            role="tabpanel"
            aria-labelledby="tab-tests"
            hidden={activeTab !== 'tests'}
          >
            <TestOutput
              testCode={testCode}
              execution={execution}
              iterations={iterations}
            />
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        <p>
          Built with ❤️ for the{' '}
          <a href="https://nebius.com" target="_blank" rel="noopener noreferrer">
            Nebius AI Cloud
          </a>{' '}
          ×{' '}
          <a href="https://www.nvidia.com/en-us/ai/" target="_blank" rel="noopener noreferrer">
            NVIDIA
          </a>{' '}
          Hackathon &nbsp;·&nbsp; Powered by Nemotron on Nebius Token Factory
        </p>
      </footer>
    </>
  );
}
