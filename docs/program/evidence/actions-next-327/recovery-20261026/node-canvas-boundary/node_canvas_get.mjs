import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const started = performance.now();
const root = process.env.PROBE_ROOT;
let client;
let transport;
let id = 0;
let stage = 'sdk_metadata';
const originalFetch = globalThis.fetch;

function record(event, fields = {}) {
  console.log(JSON.stringify({ event, elapsed_ms: Math.round(performance.now() - started), ...fields }));
}

async function observedFetch(input, init) {
  const method = init?.method ?? (input instanceof Request ? input.method : 'GET');
  const path = new URL(input instanceof Request ? input.url : input).pathname;
  const requestId = ++id;
  record('http_start', { request_id: requestId, method, path });
  try {
    const response = await originalFetch(input, init);
    record('http_response', { request_id: requestId, status: response.status });
    return response;
  } catch (error) {
    record('http_failure', { request_id: requestId, exception_class: error?.name ?? 'Error' });
    throw error;
  }
}

try {
  const sdkRoot = process.env.NODE_SDK_ROOT;
  const metadata = JSON.parse(await readFile(resolve(sdkRoot, 'package.json'), 'utf8'));
  if (metadata.name !== '@modelcontextprotocol/client' || metadata.version !== '2.0.0') {
    throw new Error('unexpected_sdk_identity');
  }
  record('sdk_package_loaded');
  stage = 'sdk_module_import';
  const sdk = await import(pathToFileURL(resolve(sdkRoot, 'dist/index.mjs')).href);
  record('sdk_module_loaded');
  stage = 'prior_fixture_read';
  const prior = JSON.parse(await readFile(resolve(root, 'prior-pass.json'), 'utf8'));
  record('prior_fixture_loaded');
  const appId = prior.snapshot.canvas_application.app_id;
  stage = 'transport_setup';
  const endpoint = new URL(process.env.RUNTIME_ENDPOINT);
  if (endpoint.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(endpoint.hostname)) {
    throw new Error('loopback_http_required');
  }
  client = new sdk.Client(
    { name: 'node-canvas-boundary-diagnostic', version: '1.0.0' },
    { versionNegotiation: { mode: 'auto' } },
  );
  transport = new sdk.StreamableHTTPClientTransport(endpoint, {
    requestInit: {
      headers: { Authorization: 'Bearer ' + process.env.RUNTIME_BEARER },
      redirect: 'error',
    },
    fetch: observedFetch,
  });
  record('transport_ready');
  stage = 'connect';
  await client.connect(transport);
  record('protocol_negotiated', { version: transport.protocolVersion ?? null });
  stage = 'tools_list';
  const catalog = await client.listTools();
  record('catalog_checked', {
    canvas_get_present: catalog.tools.some((tool) => tool.name === 'canvas_get'),
    capability_invoke_present: catalog.tools.some((tool) => tool.name === 'capability_invoke'),
  });
  stage = 'canvas_get_call';
  record('canvas_get_call_start');
  const result = await client.callTool({ name: 'canvas_get', arguments: { appId } });
  const text = (result?.content ?? []).filter((item) => item?.type === 'text').map((item) => String(item.text ?? '')).join(' ');
  record('canvas_get_response', {
    is_error: result?.isError === true,
    generic_error_text: text === 'Canvas request unavailable, invalid or access denied.',
    has_structured_content: result?.structuredContent != null,
  });
} catch (error) {
  record('client_failure', { stage, exception_class: error?.name ?? 'Error' });
  process.exitCode = 1;
} finally {
  for (const [name, object] of [['client', client], ['transport', transport]]) {
    if (object) {
      try {
        await object.close();
        record(name + '_close_complete');
      } catch (error) {
        record(name + '_close_failed', { exception_class: error?.name ?? 'Error' });
        process.exitCode = 1;
      }
    }
  }
  record('client_probe_done');
}
