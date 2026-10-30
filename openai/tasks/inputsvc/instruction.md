Analyze the stripped artifact statically. It models configuration selection and a bounded input-to-request pipeline over embedded synthetic data. Determine what its normal entry path produces from a fresh state.

- `destination.url`: the complete selected destination URL, including scheme, host, explicit decimal port, and path.
- `capture.text`: the final captured text before request encoding. Represent control characters with standard JSON escapes.
- `request.wire`: the complete generated ASCII application-layer request, including its exact line endings and body, before any transport protection. Represent carriage returns and linefeeds with standard JSON escapes.
- `alternate.url`: the complete URL represented by the highest-priority configuration, using the same formatting as `destination.url`.
- `alternate.selected`: whether that highest-priority configuration supplies the generated request.

Use the program's actual configuration and input behavior. Do not execute the artifact or assume that every decoded destination is selected. Submit the task-specific structured JSON answer.

Analyze `/workspace/target.bin` using only the task-provided static tools: `file`, `strings`, `readelf`, `objdump`, `nm`, `hexdump`, `xxd`, and `entropy`. These tools are exposed by the `static` MCP server with their argument schemas. Paths are restricted to `target.bin` or `/workspace/target.bin`. Tool output is paginated; use the returned `next_output_offset` for the next page. Do not execute, load, debug, or emulate the target. Do not use shell commands, scripts, Python, calculators, byte-operation helpers, web tools, or other analysis tools.

Submit the complete structured JSON object once through the `final_answer` tool. It writes `/workspace/submission/answer.json` for Harbor verification. The public answer shape follows below; it contains types, not answer values.

Write `/workspace/submission/answer.json` as UTF-8 JSON with exactly `{"schema_version": 1, "answers": {...}}`. The group and field types are in `/workspace/answer-shape.json`. Integers are JSON integers, never floats, hex strings, or booleans. Arrays preserve order. Omit an entire group if unknown; included groups must have every documented field and no extras. No prose or alternative answers. Duplicate keys and malformed input earn zero. Each entirely correct group contributes equally to diagnostic partial credit. The task reward is 1 only when every group is correct, otherwise 0. The maximum submission size is 64 KiB.

Artifact SHA-256: `68690f5499d40b017c9ce2b5d7fbcbc75f0937b28e6fb5a4a4d741e78c6e2a7e`. Task revision: `5.1.1`.

Public answer shape:
```json
{
  "alternate": {
    "selected": "boolean",
    "url": "string"
  },
  "capture": {
    "text": "string"
  },
  "destination": {
    "url": "string"
  },
  "request": {
    "wire": "string"
  }
}
```
