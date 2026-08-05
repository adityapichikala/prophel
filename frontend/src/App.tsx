import React, { useState, useEffect } from 'react';
import './index.css';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Incident {
  incident_id: string;
  status: 'DETECTED' | 'ACKNOWLEDGED' | 'CREW_ASSIGNED' | 'RESOLVED' | 'VERIFIED' | 'CLOSED';
  fault_type: 'SPAN_FAULT' | 'DT_FAULT' | 'FEEDER_FAULT' | 'DEAD_SENSOR';
  target_id: string;
  substation_id: string;
  feeder_id: string;
  dt_id: string;
  pincode: string;
  lat: number;
  lon: number;
  affected_pole_count: number;
  confidence: number;
  confidence_reasoning: string;
  topology_known: boolean;
  affected_pole_ids: string[];
  suppressed_by_scheduled_outage?: string;
  span_range?: string;
}

const API_BASE = 'http://localhost:8000/api/v1';

// ─── App ──────────────────────────────────────────────────────────────────────

export const App: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [activeTab, setActiveTab] = useState<'console' | 'simulator'>('console');
  const [simulationStatus, setSimulationStatus] = useState<string>('');

  // ── Data fetching ────────────────────────────────────────────────────────

  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${API_BASE}/incidents`);
      if (res.ok) {
        const data: Incident[] = await res.json();
        setIncidents(data);
        // Auto-select the first incident when the list first populates
        if (data.length > 0 && !selectedIncident) {
          setSelectedIncident(data[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
    }
  };

  // Poll every 3 seconds for real-time updates
  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 3000);
    return () => clearInterval(interval);
  }, []);

  // ── Ticket lifecycle actions ─────────────────────────────────────────────

  const handleAcknowledge = async (id: string) => {
    await fetch(`${API_BASE}/incidents/${id}/acknowledge`, { method: 'POST' });
    fetchIncidents();
  };

  const handleResolve = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/incidents/${id}/resolve`, { method: 'POST' });
      if (!res.ok) {
        const errData = await res.json();
        alert(`❌ CANNOT RESOLVE: ${errData.detail}`);
      } else {
        alert('✅ Ticket Verified and Auto-Closed by Telemetry!');
        fetchIncidents();
      }
    } catch {
      alert('Resolution failed!');
    }
  };

  // ── Fault injection (simulator tab) ─────────────────────────────────────

  const handleInjectFault = async (faultType: string, targetId: string) => {
    setSimulationStatus(`⚡ Injecting ${faultType} on ${targetId}…`);
    await fetch(
      `${API_BASE}/simulator/inject-fault?fault_type=${faultType}&target_id=${targetId}`,
      { method: 'POST' }
    );
    setSimulationStatus(`✅ Fault injected. Localization complete — check Operator Console.`);
    fetchIncidents();
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#020617' }}>

      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <div className="header-icon">⚡</div>
          <div>
            <h1 className="header-title">
              KARNATAKA SPDB
              <span className="badge">SUBDIVISION 07</span>
            </h1>
            <p className="header-sub">Low-Tension Fault Localization &amp; Operator Control Console</p>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="tab-bar">
          <button
            className={`tab-btn${activeTab === 'console' ? ' active' : ''}`}
            onClick={() => setActiveTab('console')}
          >
            Operator Console
          </button>
          <button
            className={`tab-btn${activeTab === 'simulator' ? ' active' : ''}`}
            onClick={() => setActiveTab('simulator')}
          >
            Fault Simulator
          </button>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════════════════
          OPERATOR CONSOLE TAB
      ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'console' && (
        <div className="console-grid">

          {/* ── Left: Incident feed ── */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">
                <span className="icon-amber">⚠</span>
                Active Incidents ({incidents.length})
              </span>
              <button className="refresh-btn" onClick={fetchIncidents} title="Refresh">↻</button>
            </div>

            <div className="panel-body">
              {incidents.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">✓</span>
                  All lines healthy. No active faults detected.
                </div>
              ) : (
                incidents.map((inc) => (
                  <div
                    key={inc.incident_id}
                    className={`incident-card${selectedIncident?.incident_id === inc.incident_id ? ' selected' : ''}`}
                    onClick={() => setSelectedIncident(inc)}
                  >
                    {/* ID + confidence */}
                    <div className="incident-card-top">
                      <span className="incident-id">{inc.incident_id}</span>
                      <span className={`confidence-badge ${inc.confidence >= 0.85 ? 'confidence-high' : 'confidence-low'}`}>
                        {(inc.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>

                    {/* Target pole/DT */}
                    <div className="incident-target">
                      <span className="icon-red">📍</span>
                      {inc.target_id}
                    </div>

                    {/* Key metadata */}
                    <div className="incident-meta">
                      DT: <span>{inc.dt_id}</span> &nbsp;|&nbsp;
                      PIN: <span>{inc.pincode}</span> &nbsp;|&nbsp;
                      Poles dark: <strong>{inc.affected_pole_count}</strong>
                    </div>

                    {/* Localization reasoning */}
                    <div className="incident-reasoning">{inc.confidence_reasoning}</div>

                    {/* Action buttons */}
                    <div className="incident-actions">
                      {inc.status === 'DETECTED' && (
                        <button
                          className="btn btn-blue"
                          onClick={(e) => { e.stopPropagation(); handleAcknowledge(inc.incident_id); }}
                        >
                          Acknowledge
                        </button>
                      )}
                      <button
                        className="btn btn-green"
                        onClick={(e) => { e.stopPropagation(); handleResolve(inc.incident_id); }}
                      >
                        Resolve &amp; Verify
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* ── Right: Detail / topology panel ── */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">
                <span className="icon-blue">⌁</span>
                Incident Location &amp; Topology Details
              </span>
            </div>

            <div className="panel-body">
              {selectedIncident ? (
                <>
                  {/* Key fields grid */}
                  <div className="detail-grid">
                    <div className="detail-field">
                      <label>Target Asset</label>
                      <div className="val val-amber">{selectedIncident.target_id}</div>
                    </div>
                    <div className="detail-field">
                      <label>GPS Coordinates</label>
                      <div className="val">{selectedIncident.lat.toFixed(6)}° N, {selectedIncident.lon.toFixed(6)}° E</div>
                    </div>
                    <div className="detail-field">
                      <label>Digitized Topology</label>
                      <div className="val">
                        {selectedIncident.topology_known
                          ? <span className="val-green">100% Digitized Line Tree</span>
                          : <span className="val-amber-sm">60% Missing — Geometric MST Inferred</span>
                        }
                      </div>
                    </div>
                    <div className="detail-field">
                      <label>Affected Households (est.)</label>
                      <div className="val">{selectedIncident.affected_pole_count * 5} households</div>
                    </div>
                    <div className="detail-field">
                      <label>Status</label>
                      <div className="val">{selectedIncident.status}</div>
                    </div>
                    <div className="detail-field">
                      <label>Fault Type</label>
                      <div className="val">{selectedIncident.fault_type}</div>
                    </div>
                  </div>

                  {/* Reasoning */}
                  <div className="reasoning-box">
                    <h4>Fault Boundary Reasoning</h4>
                    <p>{selectedIncident.confidence_reasoning}</p>
                  </div>
                </>
              ) : (
                <div className="detail-placeholder">
                  Select an incident from the feed to view topology details.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          FAULT SIMULATOR TAB
      ══════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'simulator' && (
        <div className="simulator-wrap">
          <div className="simulator-card">
            <div className="simulator-title">🔧 Fault Injection Simulator</div>
            <p className="simulator-desc">
              Inject synthetic faults into the live Karnataka distribution network to verify
              real-time localization, sequence-based deduplication, and ticket auto-closure.
            </p>

            {simulationStatus && (
              <div className="status-bar">{simulationStatus}</div>
            )}

            <div className="sim-grid">
              <button className="sim-btn" onClick={() => handleInjectFault('SPAN_FAULT', 'P-0001-02')}>
                <div className="sim-btn-title">Inject Known Span Fault</div>
                <div className="sim-btn-desc">Breaks a span on the fully-digitized 40% DT tree (topology_known = true).</div>
              </button>

              <button className="sim-btn" onClick={() => handleInjectFault('SPAN_FAULT', 'P-0002-02')}>
                <div className="sim-btn-title amber">Inject Missing-Topology Span Fault</div>
                <div className="sim-btn-desc">Breaks a span on a 60% missing-topology tree — localization uses geometric MST.</div>
              </button>

              <button className="sim-btn" onClick={() => handleInjectFault('DT_FAULT', 'D-0003')}>
                <div className="sim-btn-title red">Inject DT Transformer Blackout</div>
                <div className="sim-btn-desc">Turns all poles downstream of DT-0003 dark simultaneously.</div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
