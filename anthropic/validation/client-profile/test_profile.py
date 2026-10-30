"""Exercise the unmodified pinned Claude CLI against a local scripted API.

Run only inside the isolated test container with Docker --network none. No real
API credential is accepted or needed; no real model is called. The production
MCP server and an inert ELF are supplied by the task image.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path('/evidence')
EXPECTED = sorted('mcp__static__' + name for name in (
    'file', 'strings', 'readelf', 'objdump', 'nm', 'hexdump', 'xxd', 'entropy', 'final_answer'))
FORBIDDEN = ['Bash', 'Read', 'Write', 'Agent', 'Skill', 'WebFetch', 'WebSearch', 'ToolSearch']


def main() -> None:
    ROOT.mkdir(exist_ok=True)
    observations = []
    for case in ['allowed', 'forbidden', 'conflicting-settings', 'bypass-rejected']:
        submission = Path('/workspace/submission/answer.json')
        submission.unlink(missing_ok=True)
        Path('/logs/agent/static-tools.jsonl').unlink(missing_ok=True)
        config = Path('/tmp') / ('claude-profile-' + case)
        config.mkdir()
        project = config / 'project'
        project.mkdir()
        (config / '.claude.json').write_text(json.dumps({'mcpServers': {'static': {
            'type': 'stdio', 'command': 'python3', 'args': ['-I', '/opt/static-tools/server.py']}}}))
        denied_marker = config / 'forbidden-marker'
        hook_marker = config / 'hook-marker'
        if case == 'conflicting-settings':
            conflicting = {
                'permissions': {'allow': ['Bash', 'Read', 'Write', 'Agent', 'Skill', 'WebFetch', 'WebSearch'],
                                'deny': [], 'defaultMode': 'bypassPermissions'},
                'disableAllHooks': False,
                'hooks': {'SessionStart': [{'hooks': [{'type': 'command',
                    'command': 'touch ' + str(hook_marker)}]}]},
            }
            (config / 'settings.json').write_text(json.dumps(conflicting))
            (project / '.claude').mkdir()
            (project / '.claude' / 'settings.json').write_text(json.dumps(conflicting))

        requests: list[dict] = []
        script_turn = 0

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                nonlocal script_turn
                body = json.loads(self.rfile.read(int(self.headers['content-length'])))
                requests.append({'path': self.path, 'body': body})
                if 'count_tokens' in self.path:
                    payload = json.dumps({'input_tokens': 100}).encode()
                    self.send_response(200)
                    self.send_header('content-type', 'application/json')
                    self.send_header('content-length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                if case in ['forbidden', 'conflicting-settings', 'bypass-rejected'] and script_turn == 0:
                    forbidden_inputs = {
                        'Bash': {'command': 'touch ' + str(denied_marker)},
                        'Read': {'file_path': '/etc/passwd'},
                        'Write': {'file_path': str(denied_marker), 'content': 'FORBIDDEN'},
                        'Agent': {'description': 'forbidden delegation', 'prompt': 'create ' + str(denied_marker), 'subagent_type': 'general-purpose'},
                        'Skill': {'skill': 'test-forbidden'},
                        'WebFetch': {'url': 'https://example.com', 'prompt': 'fetch'},
                        'WebSearch': {'query': 'forbidden request'},
                        'ToolSearch': {'query': 'Bash'},
                    }
                    content = [{'type': 'tool_use', 'id': 'tool-forbidden-' + name,
                                'name': name, 'input': forbidden_inputs[name]} for name in FORBIDDEN]
                    stop = 'tool_use'
                elif case == 'allowed' and script_turn == 0:
                    content = [{'type': 'tool_use', 'id': 'tool-file', 'name': 'mcp__static__file',
                                'input': {'path': '/workspace/target.bin'}}]
                    stop = 'tool_use'
                elif case == 'allowed' and script_turn == 1:
                    content = [{'type': 'tool_use', 'id': 'tool-final', 'name': 'mcp__static__final_answer',
                                'input': {'schema_version': 1, 'answers': {}}}]
                    stop = 'tool_use'
                else:
                    content = [{'type': 'text', 'text': 'Offline transport check complete.'}]
                    stop = 'end_turn'
                script_turn += 1
                msg = {'id': 'msg-offline-' + str(script_turn), 'type': 'message', 'role': 'assistant',
                       'model': 'claude-sonnet-4-6', 'content': content, 'stop_reason': stop,
                       'stop_sequence': None, 'usage': {'input_tokens': 100, 'output_tokens': 20}}
                self.send_response(200)
                if body.get('stream'):
                    self.send_header('content-type', 'text/event-stream')
                    self.end_headers()
                    def event(name, data):
                        self.wfile.write(('event: ' + name + '\ndata: ' + json.dumps(data) + '\n\n').encode())
                    initial = dict(msg, content=[], stop_reason=None, usage={'input_tokens': 100, 'output_tokens': 0})
                    event('message_start', {'type': 'message_start', 'message': initial})
                    for i, block in enumerate(content):
                        if block['type'] == 'tool_use':
                            event('content_block_start', {'type': 'content_block_start', 'index': i,
                                'content_block': dict(block, input={})})
                            event('content_block_delta', {'type': 'content_block_delta', 'index': i,
                                'delta': {'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}})
                        else:
                            event('content_block_start', {'type': 'content_block_start', 'index': i,
                                'content_block': {'type': 'text', 'text': ''}})
                            event('content_block_delta', {'type': 'content_block_delta', 'index': i,
                                'delta': {'type': 'text_delta', 'text': block['text']}})
                        event('content_block_stop', {'type': 'content_block_stop', 'index': i})
                    event('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': stop, 'stop_sequence': None}, 'usage': {'output_tokens': 20}})
                    event('message_stop', {'type': 'message_stop'})
                    self.wfile.flush()
                else:
                    self.send_header('content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(msg).encode())

        httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        # Explicitly construct the environment; no host credentials are inherited.
        env = {
            'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/analyst',
            'CLAUDE_CONFIG_DIR': str(config), 'ANTHROPIC_API_KEY': 'offline-test-not-a-real-key',
            'ANTHROPIC_BASE_URL': 'http://127.0.0.1:' + str(httpd.server_port),
            'ANTHROPIC_MODEL': 'claude-sonnet-4-6', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
            'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1', 'ENABLE_TOOL_SEARCH': 'false',
            'DISABLE_AUTOUPDATER': '1', 'IS_SANDBOX': '1',
            'PYTHONDONTWRITEBYTECODE': '1',
        }
        mode = 'bypassPermissions' if case == 'bypass-rejected' else 'dontAsk'
        command = ['claude', '--verbose', '--output-format=stream-json', '--permission-mode=' + mode,
                   '--max-turns', '5', '--print']
        if case == 'conflicting-settings':
            command += ['--allowedTools', ','.join(FORBIDDEN)]
        completed = subprocess.run(command, input='Offline test. Follow the scripted tool calls.',
                                   text=True, capture_output=True, env=env, cwd=project, timeout=60)
        httpd.shutdown()
        records = []
        for line in completed.stdout.splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        init = next((r for r in records if r.get('type') == 'system' and r.get('subtype') == 'init'), {})
        api_requests = [r for r in requests if '/v1/messages' in r['path'] and 'count_tokens' not in r['path']]
        tool_lists = [sorted(t['name'] for t in r['body'].get('tools', [])) for r in api_requests]
        tool_results = [b for r in api_requests for m in r['body'].get('messages', [])
                        if isinstance(m.get('content'), list) for b in m['content']
                        if isinstance(b, dict) and b.get('type') == 'tool_result']
        errors = {b['tool_use_id']: b.get('is_error', False) for b in tool_results}
        observation = {
            'case': case, 'exit_code': completed.returncode,
            'init_tools': sorted(init.get('tools', [])), 'request_tool_lists': tool_lists,
            'effective_permission_mode': init.get('permissionMode'),
            'init_skills': init.get('skills'),
            'api_request_count': len(api_requests),
            'forbidden_marker_absent': not denied_marker.exists(),
            'hook_marker_absent': not hook_marker.exists(),
            'tool_result_errors': errors,
            'submission': json.loads(submission.read_text()) if submission.exists() else None,
            'stderr': completed.stderr[-4000:],
            'stdout': completed.stdout[-20000:],
        }
        if case == 'bypass-rejected':
            checks = {'bypass_downgraded_to_dontAsk': init.get('permissionMode') == 'dontAsk',
                      'exact_nine_api_tools': bool(tool_lists) and all(v == EXPECTED for v in tool_lists),
                      'all_forbidden_calls_rejected': all(errors.get('tool-forbidden-' + name) is True for name in FORBIDDEN),
                      'no_forbidden_write': not denied_marker.exists()}
        else:
            checks = {
                'completed': completed.returncode == 0,
                'exact_nine_init_tools': sorted(init.get('tools', [])) == EXPECTED,
                'exact_nine_api_tools': bool(tool_lists) and all(v == EXPECTED for v in tool_lists),
                'no_forbidden_write': not denied_marker.exists(),
                'no_hook_execution': not hook_marker.exists(),
                'no_skill_tool_exposed': all('Skill' not in v for v in tool_lists),
            }
            if case == 'allowed':
                checks['file_call_succeeded'] = errors.get('tool-file') is False
                checks['final_call_succeeded'] = errors.get('tool-final') is False
                checks['submission_created'] = observation['submission'] == {'schema_version': 1, 'answers': {}}
            else:
                checks['all_forbidden_calls_rejected'] = all(errors.get('tool-forbidden-' + name) is True for name in FORBIDDEN)
        observation['checks'] = checks
        observation['passed'] = all(checks.values())
        observations.append(observation)
        print(json.dumps({'case': case, 'checks': checks}), flush=True)
    report = {
        'all_passed': all(o['passed'] for o in observations),
        'test_kind': 'official-pinned-cli-local-scripted-api-production-mcp',
        'cli_version': '2.1.112', 'real_provider_requests': 0, 'paid_model_calls': 0,
        'target_executions': 0, 'container_network': 'none',
        'expected_tools': EXPECTED, 'observations': observations,
        'bindings': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            Path('/etc/claude-code/managed-settings.json'), Path('/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js'),
            Path('/opt/static-tools/server.py'), Path('/workspace/target.bin'), Path(__file__)]},
        'limitations': ['Scripted local transport responses are not real model rollouts or measured difficulty.',
                        'No real provider authentication or model availability was tested.',
                        'CLI init metadata lists bundled skill/agent names even when their invocation tools are absent. Forced Skill and Agent calls are rejected.',
                        'The CLI computes illustrative token cost from the local fixtures; those reported amounts are not actual provider charges.'],
    }
    (ROOT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if not report['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
