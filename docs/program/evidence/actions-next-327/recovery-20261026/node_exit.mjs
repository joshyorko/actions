// Diagnostic only. External supervisor must bound process lifetime and record exit.
// NODE_SDK_ROOT must name the installed @modelcontextprotocol/client 2.0.0 directory.
// RUNTIME_ENDPOINT and RUNTIME_BEARER select an already-running owned Runtime.
// Optional PROBE_CALL_FILE contains {"name": "...", "arguments": {...}}.
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const start = performance.now();
function record(event, fields = {}) {
  console.log(JSON.stringify({ event, elapsed_ms: Math.round(performance.now() - start), ...fields }));
}
function resources(event) {
  const counts = {};
  for (const kind of process.getActiveResourcesInfo()) counts[kind] = (counts[kind] ?? 0) + 1;
  record(event, { resources: counts });
}
let client;
let transport;
let requestNumber = 0;
const abortListeners = [];
const nativeFetch = globalThis.fetch;
async function observedFetch(input, init) {
  const id = ++requestNumber;
  const signal = init?.signal ?? (input instanceof Request ? input.signal : undefined);
  const method = init?.method ?? (input instanceof Request ? input.method : 'GET');
  record('http_start', { id, method, has_signal: Boolean(signal) });
  if (signal) {
    const listener = () => record('http_abort', { id });
    signal.addEventListener('abort', listener, { once: true });
    abortListeners.push([signal, listener]);
  }
  try {
    // Forward the original request and AbortSignal without cloning/overwriting.
    const response = await nativeFetch(input, init);
    record('http_headers', { id, status: response.status, content_type: response.headers.get('content-type') });
    return response;
  } catch (error) {
    record('http_error', { id, error_name: error?.name ?? 'Error' });
    throw error;
  }
}
async function bounded(label, operation, milliseconds = 30000) {
  let timer;
  record(`${label}_start`);
  try {
    const result = await Promise.race([
      Promise.resolve().then(operation),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('probe_deadline')), milliseconds);
      }),
    ]);
    record(`${label}_complete`);
    return result;
  } finally {
    clearTimeout(timer);
  }
}
try {
  const root = process.env.NODE_SDK_ROOT;
  if (!root) throw new Error('NODE_SDK_ROOT_required');
  const metadata = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'));
  if (metadata.name !== '@modelcontextprotocol/client' || metadata.version !== '2.0.0') {
    throw new Error('exact_client_2_required');
  }
  // Respect the package's export map rather than assuming a dist layout.
  const exported = metadata.exports?.['.'];
  const entry = typeof exported === 'string' ? exported :
    (typeof exported?.import === 'string' ? exported.import : exported?.import?.default);
  if (!entry) throw new Error('unsupported_export_map');
  const { Client, StreamableHTTPClientTransport } = await import(pathToFileURL(resolve(root, entry)).href);
  const endpoint = new URL(process.env.RUNTIME_ENDPOINT);
  if (!['localhost', '127.0.0.1', '[::1]'].includes(endpoint.hostname) || endpoint.protocol !== 'http:') {
    throw new Error('owned_loopback_http_required');
  }
  const bearer = process.env.RUNTIME_BEARER;
  if (!bearer) throw new Error('RUNTIME_BEARER_required');
  record('configuration', { sdk_version: metadata.version, node_version: process.version });
  resources('before_connect');
  client = new Client({ name: 'actions-node-exit-probe', version: '1.0.0' });
  transport = new StreamableHTTPClientTransport(endpoint, {
    requestInit: { headers: { Authorization: `Bearer ${bearer}` }, redirect: 'error' },
    fetch: observedFetch,
  });
  await bounded('connect', () => client.connect(transport));
  const listed = await bounded('list_tools', () => client.listTools());
  record('catalog_count', { count: listed.tools.length });
  if (process.env.PROBE_CALL_FILE) {
    const call = JSON.parse(await readFile(process.env.PROBE_CALL_FILE, 'utf8'));
    if (typeof call.name !== 'string' || !call.arguments || typeof call.arguments !== 'object' || Array.isArray(call.arguments)) {
      throw new Error('invalid_call_file');
    }
    const result = await bounded('call_tool', () => client.callTool(call), 120000);
    record('call_result', { is_error: result.isError === true });
    if (result.isError === true) process.exitCode = 1;
  }
} catch (error) {
  // Do not log messages/stacks: dependency errors can include request credentials.
  record('probe_failed', { error_name: error?.name ?? 'Error' });
  process.exitCode = 1;
} finally {
  resources('before_close');
  for (const [label, object] of [['client_close', client], ['transport_close', transport]]) {
    if (!object) continue;
    try { await bounded(label, () => object.close()); }
    catch (error) {
      record(`${label}_failed`, { error_name: error?.name ?? 'Error' });
      process.exitCode = 1;
    }
  }
  resources('after_close');
  for (const [signal, listener] of abortListeners) signal.removeEventListener('abort', listener);
  // Unref ensures this observation cannot itself prevent natural process exit.
  setTimeout(() => resources('still_alive_after_2s'), 2000).unref();
  record('main_complete');
}
process.once('beforeExit', (code) => record('before_exit', { code }));
process.once('exit', (code) => record('exit', { code }));
