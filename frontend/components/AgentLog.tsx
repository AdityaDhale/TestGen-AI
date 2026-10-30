'use client';

import React, { useEffect, useRef } from 'react';

interface LogEntry {
  step: string;
  detail: string;
  ts?: number;
}

const STEP_META: Record<string, { icon: string; label: string }> = {
  analyzing:    { icon: '🔍', label: 'Analyzing' },
  planning:     { icon: '📋', label: 'Planning' },
  generating:   { icon: '⚡', label: 'Generating' },
  executing:    { icon: '🧪', label: 'Executing' },
  'fixing':     { icon: '🔧', label: 'Fixing' },
  're-executing': { icon: '🔄', label: 'Re-running' },
  complete:     { icon: '✅', label: 'Complete' },
  error:        { icon: '❌', label: 'Error' },
};

interface AgentLogProps {
  entries: LogEntry[];
  isRunning: boolean;
}

export default function AgentLog({ entries, isRunning }: AgentLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🤖</div>
        <div className="empty-title">Agent Ready</div>
        <div className="empty-desc">
          Paste your Python code and click <strong>Generate Tests</strong> to watch
          NVIDIA Nemotron analyze, plan, and write tests in real time.
        </div>
      </div>
    );
  }

  return (
    <div className="agent-log">
      {entries.map((entry, i) => {
        const meta = STEP_META[entry.step] ?? { icon: '•', label: entry.step };
        const isLast = i === entries.length - 1;

        return (
          <div key={i} className="log-entry">
            <div className={`log-step-icon ${entry.step}`}>
              {meta.icon}
            </div>
            <div className="log-text">
              <div className="log-step-name">{meta.label}</div>
              <div className="log-detail">{entry.detail}</div>
            </div>
            {isLast && isRunning && <div className="log-dot" />}
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
