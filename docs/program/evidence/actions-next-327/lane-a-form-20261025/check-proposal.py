import json
from pathlib import Path
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[5]
proposal = (root / 'docs/program/evidence/actions-next-327/lane-a-form-20261025/semantic-extension-proposal.md').read_text()
definitions = json.loads(proposal.split('```json\n')[1].split('```')[0])
schema = json.loads((root / 'docs/contracts/canvas/canvas-spec-v1.schema.json').read_text())
schema['$id'] = 'urn:actions:canvas-spec:2'
schema['properties']['schemaVersion']['const'] = 'actions.canvas-spec/v2'
schema['$defs'].update(definitions)
schema['$defs']['CanvasNode']['oneOf'].extend({'$ref': f'#/$defs/{name}'} for name in ('CanvasCard', 'CanvasChart', 'CanvasLog', 'CanvasInspector'))
Draft202012Validator.check_schema(schema)
document = {
 'schemaVersion': 'actions.canvas-spec/v2', 'title': 'Proposal only',
 'visibility': ['app'], 'bindingIds': ['result'],
 'root': {'type': 'card', 'id': 'summary', 'title': 'Result', 'children': [
   {'type': 'chart', 'id': 'chart', 'title': 'Values', 'bindingId': 'result', 'rowsKey': 'rows', 'chartType': 'bar', 'labelKey': 'label', 'valueKey': 'value'},
   {'type': 'log', 'id': 'log', 'title': 'Messages', 'bindingId': 'result', 'rowsKey': 'logs', 'messageKey': 'message'},
   {'type': 'inspector', 'id': 'inspector', 'title': 'Details', 'bindingId': 'result', 'valueKey': 'details', 'fields': [{'key': 'value', 'label': 'Value'}]}
 ]}}
Draft202012Validator(schema).validate(document)
(root / 'docs/program/evidence/actions-next-327/lane-a-form-20261025/v2-proposal.fixture.json').write_text(json.dumps(document, indent=2) + '\n')
print('PASS: proposal schema is valid draft-2020-12; four-node example validates. No production schema changed or runtime acceptance claimed.')
