"""Task-local static analysis tools served over standard MCP stdio.

The MCP surface cannot run arbitrary code. This is not a sandbox for unrelated
tools a client may also offer: the evaluator must disable those tools separately.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
import uuid

# Load only the root-owned sibling module, even with Python isolated mode.
_spec = importlib.util.spec_from_file_location("benchmark_tools", Path(__file__).with_name("benchmark_tools.py"))
benchmark = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(benchmark)

ANALYSIS = frozenset({"file", "strings", "readelf", "objdump", "nm", "hexdump", "xxd", "entropy"})
MAX_BYTES = 65536
PAGE_SIZE = 16000
MAX_OUTPUT = 8388608
POLICY = "agentre-v31-static-only-mcp-v1"

# Trusted transport, matching the existing Harbor adapter's output limits.
RUN_TOOL = r'''
import base64,json,os,resource,subprocess,sys,tempfile
p=json.loads(base64.b64decode(sys.argv[1]));offset=p['offset'];size=p['size']
resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608))
with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
 timed_out=False
 try:
  r=subprocess.run(p['argv'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                   timeout=20,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'},shell=False)
  code=r.returncode
 except subprocess.TimeoutExpired:code=-1;timed_out=True
 total=out.tell();out.seek(offset);page=out.read(size);err.seek(0)
 print(json.dumps({'stdout':page.decode('utf-8','replace'),
  'stderr':err.read(2048).decode('utf-8','replace'),'returncode':code,'timed_out':timed_out,
  'output_offset':offset,'next_output_offset':offset+len(page) if offset+len(page)<total else None,
  'total_bytes':total}))
'''


class Commands(benchmark.BenchmarkCommands):
    def __init__(self, target):
        self.target = target
        self.config = SimpleNamespace(use_docker=True)

    def _resolve_paths(self, path):
        if path not in ("target.bin", "/workspace/target.bin"):
            raise ValueError("Only /workspace/target.bin is readable")
        return str(self.target), self.target


def real_directory(path):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_dir():
        raise ValueError("Runtime directory must be a real directory without symlinks")
    return path


class StaticTools:
    def __init__(self, target=Path("/workspace/target.bin"), submission=Path("/workspace/submission"),
                 audit=Path("/logs/agent/static-tools.jsonl"), max_calls=300):
        self.target = Path(target).absolute()
        if self.target.resolve() != self.target or not self.target.is_file():
            raise ValueError("Target must be a regular file without symlinks")
        header = self.target.read_bytes()[:20]
        if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 62:
            raise ValueError("This task requires a little-endian x86-64 ELF")
        self.target_sha256 = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.submission = real_directory(submission)
        self.audit_path = Path(audit).absolute()
        real_directory(self.audit_path.parent)
        self._audit_fd = os.open(self.audit_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self._count = 0
        self._previous = "0" * 64
        self._submitted = False
        self.max_calls = max_calls
        self._commands = Commands(self.target)
        self._lock = asyncio.Lock()

    def close(self):
        if self._audit_fd is not None:
            os.close(self._audit_fd)
            self._audit_fd = None

    @property
    def schemas(self):
        return benchmark.TOOL_SCHEMAS

    def _record(self, name, arguments, result):
        event = {"sequence": self._count, "policy_version": POLICY,
                 "previous_sha256": self._previous, "tool": name,
                 "arguments": arguments, "result": result}
        raw = json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self._previous = hashlib.sha256(raw.encode()).hexdigest()
        event["event_sha256"] = self._previous
        payload = (json.dumps(event, sort_keys=True, allow_nan=False) + "\n").encode()
        view = memoryview(payload)
        while view:
            view = view[os.write(self._audit_fd, view):]

    def _submit(self, args):
        if (type(args) is not dict or set(args) != {"schema_version", "answers"}
                or type(args["schema_version"]) is not int or args["schema_version"] != 1
                or type(args["answers"]) is not dict):
            raise ValueError("final_answer requires schema_version 1 and an answers object")
        raw = json.dumps(args, allow_nan=False).encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise ValueError("answer exceeds 64 KiB")
        directory = os.open(self.submission, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        temporary = ".answer-" + uuid.uuid4().hex
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=directory)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic no-replace publication: existing files and symlinks fail.
            os.link(temporary, "answer.json", src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            os.fsync(directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            os.close(directory)
        self._submitted = True
        return {"submitted": True, "submission_sha256": hashlib.sha256(raw).hexdigest()}

    def _execute(self, argv, offset):
        encoded = base64.b64encode(json.dumps({"argv": argv, "offset": offset, "size": PAGE_SIZE}).encode()).decode()
        result = subprocess.run([sys.executable, "-I", "-c", RUN_TOOL, encoded],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=30, shell=False,
                                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        if result.returncode:
            raise RuntimeError("Static tool transport failed")
        return json.loads(result.stdout)

    async def call(self, name, arguments):
        async with self._lock:
            if self._count >= self.max_calls:
                return {"error": "tool budget exhausted"}
            self._count += 1
            audit_args = {"rejected_arguments": True}
            audit_name = name if isinstance(name, str) and len(name) <= 1024 else "invalid_tool_name"
            try:
                if self._submitted:
                    raise ValueError("submission already finalized")
                if type(name) is not str or name not in ANALYSIS | {"final_answer"}:
                    raise ValueError("Tool unavailable in the v3.1 static-only profile")
                encoded = json.dumps(arguments, allow_nan=False)
                if type(arguments) is not dict or len(encoded.encode()) > MAX_BYTES * 2:
                    raise ValueError("invalid or oversized arguments")
                if name == "final_answer":
                    result = self._submit(arguments)
                else:
                    error = benchmark.validate_tool_call(name, arguments, set(ANALYSIS))
                    if error:
                        raise ValueError(error["error"])
                    offset = int(arguments.get("output_offset", 0))
                    if offset > MAX_OUTPUT:
                        raise ValueError("output_offset exceeds bounded tool output")
                    argv = self._commands._build_command(name, arguments)
                    if argv[0] == "python3":
                        argv.insert(1, "-I")
                    result = await asyncio.to_thread(self._execute, argv, offset)
                audit_args = arguments
            except (ValueError, TypeError, RecursionError, FileExistsError):
                result = {"error": "Invalid or unavailable tool call; follow the supplied schema and fixed target path"}
            except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError):
                result = {"error": "Static tool transport failed"}
            self._record(audit_name, audit_args, result)
            return result


async def serve(config):
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    session = StaticTools(config.target, config.submission, config.audit)
    async def list_tools(context, params):
        return types.ListToolsResult(tools=[types.Tool(name=s["name"], description=s["description"],
                                                     input_schema=s["input_schema"]) for s in session.schemas])
    async def call_tool(context, params):
        result = await session.call(params.name, params.arguments or {})
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(result, allow_nan=False))],
                                    is_error="error" in result)
    server = Server("static-analysis", version="1.0.0", on_list_tools=list_tools, on_call_tool=call_tool)
    try:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    # Startup arguments are trusted evaluator configuration, never MCP inputs.
    parser.add_argument("--target", type=Path, default=Path("/workspace/target.bin"))
    parser.add_argument("--submission", type=Path, default=Path("/workspace/submission"))
    parser.add_argument("--audit", type=Path, default=Path("/logs/agent/static-tools.jsonl"))
    asyncio.run(serve(parser.parse_args()))
