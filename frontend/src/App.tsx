import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldCheck, Activity, MapPin, Zap, RefreshCw, CheckCircle, Wrench } from 'lucide-react';
import { Incident } from './types';

const API_BASE = 'http://localhost:8000/api/v1';

export const App: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [activeTab, setActiveTab] = useState<'console' | 'simulator' | 'docs'>('console');
  const [simulationStatus, setSimulationStatus] = useState<string>('');

  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${API_BASE}/incidents`);
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);
        if (data.length > 0 && !selectedIncident) {
          setSelectedIncident(data[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 3000);
    return () => clearInterval(interval);
  }, []);

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
    } catch (err) {
      alert('Resolution failed!');
    }
  };

  const handleInjectFault = async (faultType: string, targetId: string) => {
    setSimulationStatus(`Injecting ${faultType} on ${targetId}...`);
    await fetch(`${API_BASE}/simulator/inject-fault?fault_type=${faultType}&target_id=${targetId}`, { method: 'POST' });
    setSimulationStatus(`Fault Injected! Evaluation complete.`);
    fetchIncidents();
  };

  const handleRepairFault = async (id: string) => {
    setSimulationStatus(`Restoring power for ${id}...`);
    await fetch(`${API_BASE}/simulator/repair-fault?incident_id=${id}`, { method: 'POST' });
    setSimulationStatus(`Power Restored & Ticket Auto-Verified!`);
    fetchIncidents();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans flex flex-col">
      {/* 2 a.m. High-Contrast Operator Header */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <div className="bg-amber-500 text-slate-950 p-2 rounded-lg font-bold flex items-center justify-center">
            <Zap className="w-6 h-6 fill-current" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-wide text-white flex items-center gap-2">
              KARNATAKA SPDB <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded border border-amber-500/30">SUBDIVISION 07</span>
            </h1>
            <p className="text-xs text-slate-400">Low-Tension Fault Localization & Operator Control Console</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab('console')}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all ${
              activeTab === 'console' ? 'bg-amber-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Operator Console
          </button>
          <button
            onClick={() => setActiveTab('simulator')}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all ${
              activeTab === 'simulator' ? 'bg-amber-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Fault Simulator
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      {activeTab === 'console' && (
        <div className="flex-1 grid grid-cols-12 gap-6 p-6 overflow-hidden">
          {/* Incident Feed Column */}
          <div className="col-span-5 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
              <h2 className="font-bold text-slate-200 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" /> Active Incidents ({incidents.length})
              </h2>
              <button onClick={fetchIncidents} className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {incidents.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <ShieldCheck className="w-12 h-12 mx-auto mb-2 text-emerald-500/50" />
                  <p>All lines healthy. No active faults detected.</p>
                </div>
              ) : (
                incidents.map((inc) => (
                  <div
                    key={inc.incident_id}
                    onClick={() => setSelectedIncident(inc)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      selectedIncident?.incident_id === inc.incident_id
                        ? 'border-amber-500 bg-amber-500/10'
                        : 'border-slate-800 bg-slate-950 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-mono font-bold text-slate-400">{inc.incident_id}</span>
                      <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                        inc.confidence >= 0.85 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {(inc.confidence * 100).toFixed(0)}% Confidence
                      </span>
                    </div>

                    <h3 className="font-bold text-white mb-1 flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-red-400" /> {inc.target_id}
                    </h3>

                    <p className="text-xs text-slate-400 mb-2">
                      DT: <span className="font-mono text-slate-300">{inc.dt_id}</span> | PIN: <span className="font-mono text-slate-300">{inc.pincode}</span> | Poles Dark: <span className="text-amber-400 font-bold">{inc.affected_pole_count}</span>
                    </p>

                    <div className="text-xs text-slate-300 bg-slate-900 p-2 rounded border border-slate-800 mb-3">
                      {inc.confidence_reasoning}
                    </div>

                    <div className="flex gap-2">
                      {inc.status === 'DETECTED' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleAcknowledge(inc.incident_id); }}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded"
                        >
                          Acknowledge
                        </button>
                      )}
                      <button
                        onClick={(e) => { e.stopPropagation(); handleResolve(inc.incident_id); }}
                        className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded"
                      >
                        Resolve & Verify Telemetry
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Incident Detail / Map Display Column */}
          <div className="col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-amber-400" /> Incident Location & Topology Details
            </h2>

            {selectedIncident ? (
              <div className="space-y-4">
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-500">TARGET ASSET</span>
                    <p className="font-mono font-bold text-amber-400 text-lg">{selectedIncident.target_id}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">GPS COORDINATES</span>
                    <p className="font-mono text-slate-200">{selectedIncident.lat.toFixed(6)}° N, {selectedIncident.lon.toFixed(6)}° E</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">DIGITIZED TOPOLOGY</span>
                    <p className="font-bold text-slate-200">
                      {selectedIncident.topology_known ? (
                        <span className="text-emerald-400">100% Digitized Line Tree</span>
                      ) : (
                        <span className="text-amber-400">60% Missing (Geometrically Inferred MST)</span>
                      )}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">AFFECTED HOUSES (ESTIMATED)</span>
                    <p className="font-bold text-white">{selectedIncident.affected_pole_count * 5} Households</p>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                  <h4 className="text-xs font-bold text-slate-400 mb-2">FAULT BOUNDARY REASONING</h4>
                  <p className="text-sm text-slate-200">{selectedIncident.confidence_reasoning}</p>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-slate-500">
                Select an incident from the feed to view topology details.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Simulator Tab */}
      {activeTab === 'simulator' && (
        <div className="p-8 max-w-4xl mx-auto space-y-6">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4">
            <h2 className="text-xl font-bold text-amber-400 flex items-center gap-2">
              <Wrench className="w-6 h-6" /> Fault Injection Simulator
            </h2>
            <p className="text-sm text-slate-400">
              Inject synthetic faults into the live Karnataka distribution network to verify real-time localization, deduplication, and ticket auto-closure.
            </p>

            {simulationStatus && (
              <div className="bg-amber-500/10 border border-amber-500/30 p-3 rounded text-amber-300 text-sm font-mono">
                {simulationStatus}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleInjectFault('SPAN_FAULT', 'P-0001-02')}
                className="p-4 bg-slate-950 hover:bg-slate-800 border border-slate-700 rounded-lg text-left"
              >
                <div className="font-bold text-white">Inject Known Span Fault</div>
                <div className="text-xs text-slate-400">Breaks span on digitized 40% DT tree.</div>
              </button>

              <button
                onClick={() => handleInjectFault('SPAN_FAULT', 'P-0002-02')}
                className="p-4 bg-slate-950 hover:bg-slate-800 border border-slate-700 rounded-lg text-left"
              >
                <div className="font-bold text-amber-400">Inject Missing-Topology Span Fault</div>
                <div className="text-xs text-slate-400">Breaks span on 60% missing-topology MST tree.</div>
              </button>

              <button
                onClick={() => handleInjectFault('DT_FAULT', 'D-0003')}
                className="p-4 bg-slate-950 hover:bg-slate-800 border border-slate-700 rounded-lg text-left"
              >
                <div className="font-bold text-red-400">Inject DT Transformer Blackout</div>
                <div className="text-xs text-slate-400">Turns entire DT dark at once.</div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
