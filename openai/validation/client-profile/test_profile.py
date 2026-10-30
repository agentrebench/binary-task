"""Reproduce the offline profile test in a disposable container.

Requires an already built task image and the pinned official OpenCode binary.
No repository-specific Python package, credential, or inference service is used.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True, help='A built task image containing Python, MCP, and analyst UID 1000')
    parser.add_argument('--binary', required=True, type=Path, help='Official opencode-linux-<arch> 1.19.5 binary')
    parser.add_argument('--task-environment', required=True, type=Path)
    parser.add_argument('--target-filename', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    environment = args.task_environment.resolve()
    binary = args.binary.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    for scenario in ('capture', 'dispatch'):
        destination = output / scenario
        destination.mkdir()
        command = ['docker', 'run', '--rm', '--network', 'none', '--user', 'root',
                   '--env', 'OFFLINE_SCENARIO=' + scenario]
        for source, target, readonly in (
            (binary, '/opt/opencode', True), (destination, '/capture', False),
            (HERE, '/evidence', True), (environment / 'runtime', '/opt/static-tools', True),
            (environment / args.target_filename, '/workspace/target.bin', True),
        ):
            command += ['--mount', f'type=bind,src={source},dst={target}' + (',readonly' if readonly else '')]
        command += [args.image, 'sh', '-c',
                    'mkdir -p /etc/opencode /workspace/submission /logs/agent; '
                    'cp /evidence/opencode-managed.json /etc/opencode/opencode.json; '
                    'chown -R root:root /etc/opencode; chmod 0555 /etc/opencode; chmod 0444 /etc/opencode/opencode.json; '
                    'chown -R 1000:1000 /capture /workspace/submission /logs/agent; '
                    'runuser -u analyst -- python3 -I /evidence/offline_capture.py']
        subprocess.run(command, check=True, timeout=90)
        result = json.loads((destination / 'capture-summary.json').read_text())
        assert result['all_passed'], result
    report = {'all_passed': True, 'scenarios': ['capture', 'dispatch'],
              'model_calls': 0, 'target_executions': 0, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
              'managed_settings_sha256': hashlib.sha256((HERE / 'opencode-managed.json').read_bytes()).hexdigest()}
    (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
