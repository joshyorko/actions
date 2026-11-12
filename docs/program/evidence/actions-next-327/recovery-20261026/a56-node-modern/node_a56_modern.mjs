import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const started = performance.now();
const root = process.env.PROBE_ROOT;
let client;
let transport;
let stage = 'sdk_metadata';

function record(event, fields = {}) {
  console.log(JSON.stringify({ event, elapsed_ms: Math.round(performance.now() - started), ...fields }));
}

function assert(condition, code) {
  if (!condition) throw new Error(code);
}

function digest(bytes) {
  return 'sha256:' + createHash('sha256').update(bytes).digest('hex');
}

function outputHandle(ref) {
  const raw = String(ref.output_id ?? '').replaceAll('-', '');
  assert(/^[0-9a-f]{32}$/i.test(raw), 'invalid_output_id');
  return 'art_' + Buffer.from(raw, 'hex').toString('base64url');
}

async function managed(operation, queue, args = {}) {
  const endpoint = process.env.RUNTIME_ENDPOINT.replace(/\/mcp$/, '');
  const response = await fetch(endpoint + '/api/managed-work-items/v1/operations', {
    method: 'POST',
    headers: {
      Authorization: 'Bearer ' + process.env.RUNTIME_BEARER,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ schema_version: 'actions.managed-work-items/v1', operation, queue, ...args }),
    redirect: 'error',
    signal: AbortSignal.timeout(15_000),
  });
  assert(response.status === 200, 'managed_http_' + operation + '_' + response.status);
  const envelope = await response.json();
  assert(envelope.operation === operation, 'managed_envelope_' + operation);
  return envelope.result;
}

async function readArtifact(queue, ref) {
  let bytes = Buffer.alloc(0);
  let cursor = null;
  for (let index = 0; index < 32; index += 1) {
    const page = await managed('artifacts.read', queue, { artifact_handle: ref.handle, cursor });
    assert(page.offset === bytes.length, 'artifact_offset');
    bytes = Buffer.concat([bytes, Buffer.from(page.data_base64, 'base64')]);
    assert(bytes.length <= 2 * 1024 * 1024, 'artifact_limit');
    if (page.eof) {
      assert(page.next_cursor === null, 'artifact_final_cursor');
      break;
    }
    cursor = page.next_cursor;
    assert(cursor, 'artifact_cursor_missing');
    if (index === 31) throw new Error('artifact_read_bound');
  }
  assert(bytes.length === ref.size && digest(bytes) === ref.digest, 'artifact_digest_mismatch');
  return bytes;
}

async function executeCase(name) {
  stage = 'fixture_' + name;
  const prior = JSON.parse(await readFile(resolve(root, 'prior-' + name + '.json'), 'utf8'));
  const appId = prior.snapshot.canvas_application.app_id;
  record('canvas_get_start', { case: name });
  stage = 'canvas_get_' + name;
  const opened = await client.callTool(
    { name: 'canvas_get', arguments: { appId } },
    { timeout: 20_000 },
  );
  assert(opened.isError !== true && opened.structuredContent, 'canvas_get_error_' + name);
  const descriptor = opened.structuredContent.invocationDescriptors.find((item) => item.bindingId === 'robot');
  assert(descriptor?.inputMode === 'claim' && descriptor.standaloneAllowed === false, 'claim_descriptor_invalid');
  const { snapshot, inputQueue: queue } = descriptor;
  assert(queue, 'missing_queue');
  record('canvas_get_success', { case: name });

  const suffix = Date.now() + '-' + process.pid;
  const enqueueArgs = {
    snapshot,
    payload: { text: 'Node a56 modern claimed Robot ' + name + ' ' + suffix },
    idempotency_key: 'node-a56-modern-' + name + '-' + suffix,
  };
  stage = 'enqueue_' + name;
  const enqueued = await managed('items.enqueue', queue, enqueueArgs);
  const replay = await managed('items.enqueue', queue, enqueueArgs);
  assert(replay.replay === true && JSON.stringify(replay.item) === JSON.stringify(enqueued.item), 'enqueue_replay_mismatch');
  record('enqueue_replay_verified', { case: name });

  stage = 'claim_' + name;
  const claimReply = await managed('items.claim', queue, {
    idempotency_key: 'node-a56-claim-' + name + '-' + suffix,
    lease_seconds: 120,
  });
  const claim = claimReply.claim;
  assert(claim?.item_id === enqueued.item.id && claim.owner_id === process.env.EXPECTED_OWNER, 'claim_mismatch');
  record('claim_success', { case: name });

  stage = 'invoke_' + name;
  const invocation = await client.callTool(
    { name: 'capability_invoke', arguments: { mode: 'generic', snapshot, claim } },
    { timeout: 70_000 },
  );
  assert(invocation.isError !== true, 'generic_invoke_tool_error_' + name);
  const execution = invocation.structuredContent?.execution;
  assert(execution, 'generic_execution_missing');
  const pass = name === 'pass';
  assert(
    execution.attemptState === (pass ? 'succeeded' : 'failed')
      && execution.workItemState === (pass ? 'COMPLETED' : 'FAILED')
      && execution.workItemId === enqueued.item.id
      && execution.workItemEpoch === claim.epoch,
    'execution_terminal_state_mismatch',
  );
  assert(execution.state === (pass ? 'completed' : 'failed') && execution.outputs?.length === 4, 'execution_projection_mismatch');
  record('generic_execution_terminal', {
    case: name,
    state: execution.state,
    attempt_state: execution.attemptState,
    work_item_state: execution.workItemState,
  });

  stage = 'runs_get_' + name;
  const run = (await managed('runs.get', queue, { run_id: execution.runId })).run;
  assert(run?.id === execution.runId, 'run_missing');
  const robotReceipt = run.result;
  assert(
    robotReceipt.version === 'actions.robot-execution/v1'
      && robotReceipt.mode === 'work-items'
      && robotReceipt.status === (pass ? 'PASS' : 'FAIL')
      && robotReceipt.returnCode === (pass ? 0 : 1),
    'robot_receipt_mismatch',
  );
  assert(
    robotReceipt.claim.item_id === claim.item_id
      && robotReceipt.claim.owner_id === claim.owner_id
      && robotReceipt.claim.epoch === claim.epoch,
    'receipt_claim_mismatch',
  );
  assert(
    robotReceipt.cleanup.wrapper_reaped === true
      && robotReceipt.cleanup.descendant_snapshot_complete === true
      && robotReceipt.cleanup.live_descendant_pids.length === 0
      && robotReceipt.cleanup.errors.length === 0,
    'worker_cleanup_mismatch',
  );
  assert(robotReceipt.publicationFence.attempt_id === execution.attemptId, 'publication_fence_mismatch');

  const refs = Object.fromEntries(run.artifacts.map((item) => [item.handle, item]));
  assert(Object.keys(refs).length === 4, 'artifact_count');
  const blobs = {};
  const artifactSha256 = {};
  stage = 'authorized_artifact_reads_' + name;
  for (const output of robotReceipt.outputs) {
    const handle = outputHandle(output.ref);
    const ref = refs[handle];
    assert(ref, 'artifact_ref_missing');
    const bytes = await readArtifact(queue, ref);
    blobs[output.name] = bytes;
    artifactSha256[output.name] = createHash('sha256').update(bytes).digest('hex');
  }
  assert(Object.keys(blobs).length === 4, 'authorized_artifact_count');
  await writeFile(resolve(root, 'robot-output-' + name + '.xml'), blobs['robot-output.xml']);
  const rccReceipt = JSON.parse(blobs['rcc-receipt.json'].toString('utf8'));
  assert(rccReceipt.exitCode === (pass ? 0 : 1), 'rcc_exit_code_mismatch');
  assert(rccReceipt.artifactDigest === process.env.EXPECTED_ARTIFACT, 'rcc_artifact_digest_mismatch');

  stage = 'items_get_' + name;
  const item = (await managed('items.get', queue, { item_id: enqueued.item.id })).item;
  assert(
    item.queue_state === (pass ? 'DONE' : 'FAILED')
      && item.claim === null
      && item.lease_deadline_ms === null
      && item.delivery_count === 1
      && item.child_ids.length === 0
      && JSON.stringify(item.run_ids) === JSON.stringify([execution.runId]),
    'item_terminal_mismatch',
  );

  const retained = {
    case: name,
    appId,
    queue,
    snapshot,
    claim,
    itemId: item.id,
    runId: execution.runId,
    execution,
    run,
    item,
    artifactSha256,
  };
  await writeFile(resolve(root, 'sync-' + name + '.json'), JSON.stringify(retained, null, 2));
  record('case_complete', {
    case: name,
    run_id: execution.runId,
    execution_state: execution.state,
    queue_state: item.queue_state,
    authorized_artifacts: Object.keys(blobs).length,
    rcc_exit_code: rccReceipt.exitCode,
  });
}

async function restartRead() {
  for (const name of ['pass', 'fail']) {
    const saved = JSON.parse(await readFile(resolve(root, 'sync-' + name + '.json'), 'utf8'));
    stage = 'restart_run_' + name;
    const run = (await managed('runs.get', saved.queue, { run_id: saved.runId })).run;
    assert(JSON.stringify(run) === JSON.stringify(saved.run), 'restart_run_changed_' + name);
    stage = 'restart_item_' + name;
    const item = (await managed('items.get', saved.queue, { item_id: saved.itemId })).item;
    assert(JSON.stringify(item) === JSON.stringify(saved.item), 'restart_item_changed_' + name);
    const refs = Object.fromEntries(run.artifacts.map((artifact) => [artifact.handle, artifact]));
    stage = 'restart_artifacts_' + name;
    let verified = 0;
    for (const output of run.result.outputs) {
      const ref = refs[outputHandle(output.ref)];
      assert(ref, 'restart_artifact_ref_missing_' + name);
      const bytes = await readArtifact(saved.queue, ref);
      assert(createHash('sha256').update(bytes).digest('hex') === saved.artifactSha256[output.name], 'restart_artifact_changed_' + name);
      verified += 1;
    }
    assert(verified === 4, 'restart_artifact_count_' + name);
    record('restart_read_complete', { case: name, run_id: saved.runId, queue_state: item.queue_state, artifacts_verified: verified });
  }
}

async function main() {
  const sdkRoot = process.env.NODE_SDK_ROOT;
  const metadata = JSON.parse(await readFile(resolve(sdkRoot, 'package.json'), 'utf8'));
  assert(metadata.name === '@modelcontextprotocol/client' && metadata.version === '2.0.0', 'sdk_identity');
  const sdk = await import(pathToFileURL(resolve(sdkRoot, 'dist/index.mjs')).href);
  const endpoint = new URL(process.env.RUNTIME_ENDPOINT);
  assert(endpoint.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(endpoint.hostname), 'loopback_http_required');
  const phase = process.env.PROBE_PHASE;
  record('client_config', {
    sdk_version: metadata.version,
    node_version: process.version,
    undici_version: process.versions.undici,
    phase,
    version_negotiation: 'auto',
  });
  client = new sdk.Client(
    { name: 'actions-node-a56-modern-generic-gate', version: '1.0.0' },
    { versionNegotiation: { mode: 'auto' } },
  );
  transport = new sdk.StreamableHTTPClientTransport(endpoint, {
    requestInit: {
      headers: { Authorization: 'Bearer ' + process.env.RUNTIME_BEARER },
      redirect: 'error',
    },
  });
  stage = 'connect';
  await client.connect(transport, { timeout: 25_000 });
  const negotiated = transport.protocolVersion;
  assert(negotiated === '2026-07-28', 'unexpected_protocol_version');
  record('protocol_negotiated', { version: negotiated });

  stage = 'tools_list';
  const catalog = await client.listTools({ timeout: 20_000 });
  assert(
    catalog.tools.some((tool) => tool.name === 'capability_invoke')
      && catalog.tools.some((tool) => tool.name === 'canvas_get'),
    'expected_tools_missing',
  );
  record('catalog_ready', { canvas_get_present: true, capability_invoke_present: true });

  if (phase === 'execute') {
    await executeCase('pass');
    await executeCase('fail');
  } else if (phase === 'restart') {
    await restartRead();
  } else {
    throw new Error('unknown_phase');
  }
  record('phase_complete', { phase });
}

try {
  await main();
} catch (error) {
  record('client_failure', { stage, exception_class: error?.name ?? 'Error' });
  process.exitCode = 1;
} finally {
  for (const [label, object] of [['client', client], ['transport', transport]]) {
    if (object) {
      try {
        await object.close();
        record(label + '_close_complete');
      } catch (error) {
        record(label + '_close_failed', { exception_class: error?.name ?? 'Error' });
        process.exitCode = 1;
      }
    }
  }
}

process.once('beforeExit', (code) => record('natural_before_exit', { code }));
