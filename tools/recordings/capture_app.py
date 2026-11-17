"""Local-only browser harness for screenshots of actual example execution.

From the codex branch: python3 tools/recordings/capture_app.py --milestone 1 --port 8765
The example runs from a temporary copy of the milestone implementation on codex.
The button executes a fixed example command, never caller-supplied shell input.
This harness is documentation tooling, not part of the Retry Kit application.
"""

import argparse
import json
import subprocess
import tarfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Retry Kit — live example</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#eef3f4;color:#173640;font:18px/1.6 system-ui,sans-serif}
main{max-width:1040px;margin:60px auto;padding:36px;background:white;border:1px solid #cbd8dc;border-radius:16px}
h1{font-size:34px;line-height:1.25;margin:8px 0 12px}.eyebrow{color:#356b60;font-weight:700;letter-spacing:.1em;text-transform:uppercase;font-size:14px}
button{background:#205b50;color:white;border:0;border-radius:8px;padding:13px 20px;font:inherit;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#102c34;color:#ecf8ee;padding:24px;border-radius:10px;font:17px/1.8 ui-monospace,monospace}
.meta{font:14px/1.7 ui-monospace,monospace;color:#52646b}.caption{font-size:15px;color:#52646b}#status{margin-left:16px}
</style><main><div class="eyebrow">Retry Kit · application output</div><h1 id="title">Live report consumer</h1>
<p>This browser harness runs the repository’s actual Python example and displays its output.</p>
<div class="meta" id="checkpoint"></div><p class="meta" id="command"></p>
<button id="run">Run the example</button><span id="status" role="status">Ready</span>
<pre id="output">Select “Run the example” to execute the consumer.</pre>
<p class="caption">Application-output capture from a live local run. This is a browser harness, not a terminal screenshot or an explanatory diagram.</p></main>
<script>
fetch('/metadata').then(r=>r.json()).then(d=>{document.querySelector('#title').textContent='Milestone '+d.milestone+' · live report consumer';document.querySelector('#checkpoint').textContent='Codex · '+d.title;document.querySelector('#command').textContent='$ '+d.command;});
document.querySelector('#run').onclick=async()=>{let b=document.querySelector('#run');b.disabled=true;document.querySelector('#status').textContent='Running…';try{let r=await fetch('/run',{method:'POST'});let d=await r.json();document.querySelector('#output').textContent=d.stdout+(d.stderr?'\\n'+d.stderr:'');document.querySelector('#status').textContent='Exit '+d.returncode;}catch(e){document.querySelector('#status').textContent='Execution failed: '+e.message;}finally{b.disabled=false;}};
</script></html>'''


def implementation_revision(subject):
    refs = ['refs/heads/codex', 'refs/remotes/origin/codex']
    available = subprocess.check_output(
        ['git', 'for-each-ref', '--format=%(refname)', *refs], cwd=ROOT, text=True,
    ).splitlines()
    branch = next((ref for ref in refs if ref in available), None)
    if branch is None:
        raise SystemExit('Fetch the codex branch before replaying a milestone.')

    history = subprocess.check_output(
        ['git', 'log', '--first-parent', '--format=%H%x09%s', branch], cwd=ROOT, text=True,
    )
    matches = []
    for entry in history.splitlines():
        revision, title = entry.split('\t', 1)
        if title == subject:
            matches.append(revision)
    if len(matches) != 1:
        raise SystemExit(f'Expected one commit titled “{subject}” on codex, found {len(matches)}.')
    return matches[0]


def main():
    assets = ROOT / 'docs' / 'milestones' / 'assets'
    checkpoints = json.loads((assets / 'checkpoints.json').read_text())
    parser = argparse.ArgumentParser()
    parser.add_argument('--milestone', type=int, choices=[c['number'] for c in checkpoints], required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    example = 'examples/read_with_budget.py' if args.milestone == 3 else 'examples/read_report.py'
    command = ['uv', 'run', '--locked', 'python', example]
    chapter = next(c for c in checkpoints if c['number'] == args.milestone)
    dest = assets / chapter['slug']
    revision = implementation_revision(chapter['subject'])

    class Handler(BaseHTTPRequestHandler):
        def reply(self, payload, kind='application/json'):
            body = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/metadata':
                self.reply(dict(milestone=args.milestone, title=chapter['title'], command=' '.join(command)))
            elif self.path == '/':
                self.reply(PAGE, 'text/html; charset=utf-8')
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != '/run':
                self.send_error(404)
                return
            result = subprocess.run(command, cwd=checkout, capture_output=True, text=True, timeout=30)
            record = dict(command=' '.join(command), milestone=args.milestone, stdout=result.stdout,
                          stderr=result.stderr, returncode=result.returncode)
            (dest / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
            (dest / 'output.txt').write_text(result.stdout)
            self.reply(record)

    with TemporaryDirectory(prefix='retry-kit-capture-') as checkout:
        snapshot = subprocess.check_output(['git', 'archive', revision], cwd=ROOT)
        with tarfile.open(fileobj=BytesIO(snapshot)) as archive:
            archive.extractall(checkout, filter='data')
        subprocess.run(['uv', 'sync', '--locked'], cwd=checkout, check=True)
        with HTTPServer(('127.0.0.1', args.port), Handler) as server:
            server.serve_forever()


if __name__ == '__main__':
    main()
