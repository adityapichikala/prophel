export type IncidentStatus = 'DETECTED' | 'ACKNOWLEDGED' | 'CREW_ASSIGNED' | 'RESOLVED' | 'VERIFIED' | 'CLOSED';
export type FaultType = 'SPAN_FAULT' | 'DT_FAULT' | 'FEEDER_FAULT' | 'DEAD_SENSOR';

export interface Incident {
  incident_id: string;
  status: IncidentStatus;
  fault_type: FaultType;
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

export interface TelemetryMessage {
  device_id: string;
  pole_id: string;
  event: 'heartbeat' | 'power_lost' | 'power_restored' | 'boot';
  energized: boolean;
  ts: string;
  seq: number;
}
