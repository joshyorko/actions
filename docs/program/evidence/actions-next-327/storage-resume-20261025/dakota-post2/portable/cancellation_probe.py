"""Exercise the exact nested run() via AST extraction, synthetic child only."""
import ast
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time

source = Path(__file__).with_name('prepare-compiler-managed.py')
tree = ast.parse(source.read_text())
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
run = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
for index, node in enumerate(run.body):
    if isinstance(node, ast.Nonlocal):
        run.body[index] = ast.Global(names=node.names)
selected = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.ClassDef)) or isinstance(n, ast.FunctionDef) and n.name in ('sanitize', 'used')]
selected.append(run)
module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
namespace = {}
exec(compile(module, str(source), 'exec'), namespace)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    guard = namespace['SignalGuard']()
    namespace.update(root=root, env=dict(os.environ), guard=guard, log_bytes=0, LIMIT=1024**2,
                     budget=lambda: 0, sampled_peak=0, minimum_free=1, phases=[])
    guard.install()
    # Exercise repeated signals DURING cleanup, without blocking its reaping.
    original_killpg = os.killpg
    def signalled_killpg(pid, sig):
        os.kill(os.getpid(), signal.SIGTERM)
        os.kill(os.getpid(), signal.SIGINT)
        return original_killpg(pid, sig)
    namespace['os'].killpg = signalled_killpg
    def trigger():
        for _ in range(100):
            if (root/'child.pid').exists():
                os.kill(os.getpid(), signal.SIGTERM)
                return
            time.sleep(.01)
    thread = threading.Thread(target=trigger, daemon=True)
    thread.start()
    try:
        try:
            namespace['run']([sys.executable, '-c', "import os,time,pathlib; pathlib.Path('child.pid').write_text(str(os.getpid())); time.sleep(30)"], 'synthetic', 5)
        except namespace['StopRequested']:
            pass
        else:
            raise AssertionError('stop not propagated')
        child = int((root/'child.pid').read_text())
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError('synthetic child survived')
        try:
            namespace['run']([sys.executable, '-c', "open('forbidden-next-phase','w').close()"], 'next', 5)
        except namespace['StopRequested']:
            pass
        else:
            raise AssertionError('next phase started')
        assert not (root/'forbidden-next-phase').exists()
        assert not namespace['phases'][0]['cleanup_errors']
    finally:
        namespace['os'].killpg = original_killpg
        guard.restore()
        thread.join(timeout=1)
print('PASS: SIGTERM, repeated cleanup signals, child reaped, next phase refused')
