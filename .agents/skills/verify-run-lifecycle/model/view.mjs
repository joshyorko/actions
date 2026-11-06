export const title = 'One Robot Run: durable launch, leases, and recovery';
export function state(v) {
  const s=v.s;
  if(s.spawned.length>1) return 'Duplicate external execution';
  if(s.badWrite) return 'Stale publication committed';
  if(s.status==='cancelled') return s.running.length ? 'Cancelled while process runs' : (s.epoch && !s.reaped.includes(s.epoch) ? 'Cancellation reported without stopped proof' : 'Cancellation confirmed');
  if(s.status==='passed'||s.status==='failed') return 'Result published';
  if(s.recovery && s.launch) return 'Recovery authorized; retained launch blocks progress';
  if(s.recovery) return 'Pre-launch recovery authorized';
  if(s.cancel) return s.running.length ? 'Cancellation requested; process runs' : 'Waiting for stopped-launch confirmation';
  if(!s.epoch) return 'Queued';
  if(!s.runLive) return s.launch ? 'Expired with retained launch' : 'Expired before launch';
  if(s.running.length) return 'Owned process running';
  if(s.launch) return 'Launch committed or awaiting publication';
  return s.epoch>1 ? 'Replacement attempt fenced' : 'Attempt leased';
}
export function step(action) { return action.replaceAll(/([a-z])([A-Z])/g,'$1 $2'); }
