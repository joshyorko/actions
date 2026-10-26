import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.env.PROBE_ROOT;
const events = [];
let stage = 'sdk_metadata';
let client;
let transport;
function record(event, fields = {}) {
  const row = { event, stage, elapsed_ms: Math.round(performance.now()), ...fields };
  events.push(row);
  console.log(JSON.stringify(row));
}
function assert(condition, code) {
  if (!condition) throw new Error(code);
}
function sha(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}
function hasNone(object, keys) {
  return keys.every((key) => !Object.hasOwn(object ?? {}, key));
}

async function main() {
  const sdkRoot = process.env.NODE_SDK_ROOT;
  const metadata = JSON.parse(await readFile(resolve(sdkRoot, 'package.json'), 'utf8'));
  assert(metadata.name === '@modelcontextprotocol/client' && metadata.version === '2.0.0', 'sdk_identity');
  const sdk = await import(pathToFileURL(resolve(sdkRoot, 'dist/index.mjs')).href);
  const endpoint = new URL(process.env.RUNTIME_ENDPOINT);
  assert(endpoint.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(endpoint.hostname), 'loopback_http_required');
  record('client_config', { sdk_version: metadata.version, node_version: process.version, undici_version: process.versions.undici, version_negotiation: 'auto' });
  client = new sdk.Client({ name: 'actions-a57-canvas-library-protocol', version: '1.0.0' }, { versionNegotiation: { mode: 'auto' } });
  transport = new sdk.StreamableHTTPClientTransport(endpoint, {
    requestInit: { headers: { Authorization: 'Bearer ' + process.env.RUNTIME_BEARER }, redirect: 'error' },
  });

  stage = 'connect';
  await client.connect(transport, { timeout: 25_000 });
  const negotiated = transport.protocolVersion;
  assert(negotiated === '2026-07-28', 'unexpected_protocol_version');
  record('protocol_negotiated', { protocol_version: negotiated });

  stage = 'tools_list';
  const catalog = await client.listTools({ timeout: 20_000 });
  const tools = Object.fromEntries(catalog.tools.map((tool) => [tool.name, tool]));
  assert(tools.canvas_get && tools.canvas_open && tools.canvas_create, 'canvas_tools_missing');
  const uri = 'ui://action-canvas/v1/canvas.html';
  const refs = ['canvas_get', 'canvas_open', 'canvas_create'].map((name) => tools[name]?._meta?.ui?.resourceUri);
  assert(refs.every((value) => value === uri), 'tool_resource_uri_mismatch');
  record('catalog_ready', { canvas_get: true, canvas_open: true, canvas_create: true, same_ui_resource: true });

  stage = 'canvas_open_initial';
  const initialOpen = await client.callTool({ name: 'canvas_open', arguments: {} }, { timeout: 20_000 });
  assert(initialOpen.isError !== true && initialOpen.structuredContent, 'initial_canvas_open_error');
  assert(Array.isArray(initialOpen.structuredContent.applications) && initialOpen.structuredContent.applications.length === 0, 'initial_library_not_empty');
  const initialMeta = initialOpen._meta ?? {};
  assert(initialMeta['actions.canvas'] && JSON.stringify(initialMeta['actions.canvas']) === JSON.stringify(initialOpen.structuredContent), 'initial_library_view_mismatch');
  record('initial_library_verified_empty', { application_count: 0, view_matches_structured: true });

  stage = 'canvas_create';
  const create = await client.callTool({
    name: 'canvas_create',
    arguments: { idempotencyKey: 'a57-library-protocol-default-canvas' },
  }, { timeout: 20_000 });
  assert(create.isError !== true && create.structuredContent, 'canvas_create_error');
  const appId = create.structuredContent.applicationId;
  assert(typeof appId === 'string' && /^[0-9a-f-]{36}$/i.test(appId), 'created_app_id_missing');
  const createMeta = create._meta?.['actions.canvas'];
  assert(createMeta && createMeta.spec && !createMeta.spec.backend, 'created_canvas_has_backend');
  const defaultSpec = createMeta.spec;
  assert(defaultSpec.schemaVersion === 'actions.canvas-spec/v1' && defaultSpec.title === 'New Canvas'
    && Array.isArray(defaultSpec.bindingIds) && defaultSpec.bindingIds.length === 0
    && defaultSpec.root?.type === 'stack', 'default_canvas_spec_invalid');
  record('default_canvas_created', { application_id: appId, default_title: defaultSpec.title, binding_count: defaultSpec.bindingIds.length, has_backend: false });

  stage = 'canvas_get_before_open';
  const firstGet = await client.callTool({ name: 'canvas_get', arguments: { appId } }, { timeout: 20_000 });
  assert(firstGet.isError !== true && firstGet.structuredContent, 'canvas_get_error');
  const active = firstGet.structuredContent;
  assert(active.applicationId === appId && typeof active.revisionId === 'string' && active.spec?.title === 'New Canvas', 'canvas_get_app_spec_mismatch');
  const activeMeta = firstGet._meta ?? {};
  const appMetadata = activeMeta['actions.canvas'] ?? {};
  // Keep tokens and private metadata in memory only; report booleans and key names.
  const structuredHasPrivateExtras = ['appSession', 'genericExecution', 'reviewedExecution', 'execution', 'review']
    .some((key) => Object.hasOwn(active, key));
  record('canvas_get_metadata', {
    application_id_matches: true,
    revision_present: true,
    active: active.active,
    structured_private_extras: structuredHasPrivateExtras,
    canvas_metadata_present: Object.keys(appMetadata).length > 0,
    session_metadata_present: Object.hasOwn(activeMeta, 'actions.appSession'),
    generic_metadata_present: Object.hasOwn(activeMeta, 'actions.genericExecution'),
    reviewed_metadata_present: Object.hasOwn(activeMeta, 'actions.reviewedExecution'),
  });
  assert(!structuredHasPrivateExtras, 'private_metadata_in_structured_content');

  stage = 'canvas_open';
  const opened = await client.callTool({ name: 'canvas_open', arguments: {} }, { timeout: 20_000 });
  assert(opened.isError !== true && opened.structuredContent, 'canvas_open_error');
  const library = opened.structuredContent.applications;
  assert(Array.isArray(library) && library.length === 1, 'library_applications_missing_or_unexpected_count');
  const entry = library.find((app) => app.applicationId === appId);
  assert(entry && Object.keys(entry).sort().join(',') === 'activeRevisionId,applicationId,title', 'library_app_metadata_invalid');
  assert(typeof entry.title === 'string' && entry.title === 'New Canvas'
    && (entry.activeRevisionId === null || /^sha256:[0-9a-f]{64}$/i.test(entry.activeRevisionId)), 'library_app_values_invalid');
  const openMeta = opened._meta ?? {};
  const openCanvas = openMeta['actions.canvas'];
  assert(openCanvas && JSON.stringify(openCanvas) === JSON.stringify(opened.structuredContent), 'library_view_metadata_mismatch');
  const forbiddenOpen = ['actions.appSession', 'actions.genericExecution', 'actions.reviewedExecution', 'actions.execution', 'actions.review', 'actions.artifact', 'actions.projection'];
  assert(hasNone(openMeta, forbiddenOpen), 'library_open_contains_private_or_execution_metadata');
  record('library_metadata', { requested_application_present: true, application_count: library.length, active_revision_nullable: true, view_matches_structured: true, forbidden_metadata_absent: true });

  stage = 'canvas_get_after_open';
  const secondGet = await client.callTool({ name: 'canvas_get', arguments: { appId } }, { timeout: 20_000 });
  assert(secondGet.isError !== true && secondGet.structuredContent, 'canvas_get_after_open_error');
  const after = secondGet.structuredContent;
  assert(after.applicationId === active.applicationId && after.revisionId === active.revisionId
    && JSON.stringify(after.spec) === JSON.stringify(active.spec), 'canvas_get_changed_after_open');
  record('canvas_get_after_open_verified', { application_id_matches: true, revision_unchanged: true, spec_unchanged: true });

  stage = 'resource_read';
  const resource = await client.readResource({ uri }, { timeout: 20_000 });
  assert(resource.contents?.length === 1 && resource.contents[0].uri === uri && typeof resource.contents[0].text === 'string', 'ui_resource_shape_invalid');
  const bytes = Buffer.from(resource.contents[0].text, 'utf8');
  assert(sha(bytes) === process.env.EXPECTED_HTML_SHA256, 'ui_resource_hash_mismatch');
  assert(bytes.toString('utf8').includes('Action Canvas library'), 'library_heading_missing');
  record('ui_resource_verified', { uri, byte_length: bytes.length, sha256: sha(bytes), library_heading_present: true });
  await writeFile(resolve(root, 'result.json'), JSON.stringify({
    protocol_version: negotiated,
    application_id: appId,
    title: entry.title,
    active_revision_id: entry.activeRevisionId,
    revision_id: active.revisionId,
    default_spec_schema: defaultSpec.schemaVersion,
    default_binding_count: defaultSpec.bindingIds.length,
    library_application_count: library.length,
    resource_uri: uri,
    resource_byte_length: bytes.length,
    resource_sha256: sha(bytes),
  }, null, 2) + '\n');
  record('phase_complete');
}

try {
  await main();
} catch (error) {
  record('client_failure', { exception_class: error?.name ?? 'Error' });
  process.exitCode = 1;
} finally {
  for (const [label, object] of [['client', client], ['transport', transport]]) {
    if (!object) continue;
    try {
      await object.close();
      record(label + '_close_complete');
    } catch (error) {
      record(label + '_close_failed', { exception_class: error?.name ?? 'Error' });
      process.exitCode = 1;
    }
  }
}
process.once('beforeExit', (code) => record('natural_before_exit', { code }));
