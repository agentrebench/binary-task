Analyze how the stripped artifact selects a loader-data template and constructs its final byte buffer from the embedded inputs.

Report the payload's PE machine value, optional-header magic, and selected loader width in `selection`. In `layout`, report the selected loader size, payload size, parameter offset, total buffer size, and entry offset. All offsets are zero-based relative to the final combined buffer; total size includes any terminating parameter NUL.

In `patches`, report the values actually written for payload offset, payload size, entry-relative displacement, and parameter-relative displacement. Each relative displacement is measured from immediately after its own four-byte patch location. In `parameter.ascii`, give the final parameter text without its terminating NUL. Use decimal JSON integers.

The payload and loader templates are deliberately inert data. The artifact constructs bytes without loading or executing them. Use static analysis only.

Analyze `/workspace/target.bin` using only the task-provided static tools: `file`, `strings`, `readelf`, `objdump`, `nm`, `hexdump`, `xxd`, and `entropy`. These tools are exposed by the `static` MCP server with their argument schemas. Paths are restricted to `target.bin` or `/workspace/target.bin`. Tool output is paginated; use the returned `next_output_offset` for the next page. Do not execute, load, debug, or emulate the target. Do not use shell commands, scripts, Python, calculators, byte-operation helpers, web tools, or other analysis tools.

Submit the complete structured JSON object once through the `final_answer` tool. It writes `/workspace/submission/answer.json` for Harbor verification. The public answer shape follows below; it contains types, not answer values.

Write `/workspace/submission/answer.json` as UTF-8 JSON with exactly `{"schema_version": 1, "answers": {...}}`. The group and field types are in `/workspace/answer-shape.json`. Integers are JSON integers, never floats, hex strings, or booleans. Arrays preserve order. Omit an entire group if unknown; included groups must have every documented field and no extras. No prose or alternative answers. Duplicate keys and malformed input earn zero. Each entirely correct group contributes equally to diagnostic partial credit. The task reward is 1 only when every group is correct, otherwise 0. The maximum submission size is 64 KiB.

Artifact SHA-256: `8ef14277868a3964e5002699f3a0829a058c549e14a2bc54ff425693cc9cafd0`. Task revision: `5.1.1`.

Public answer shape:
```json
{
  "layout": {
    "entry_offset": "integer",
    "loader_size": "integer",
    "parameter_offset": "integer",
    "payload_size": "integer",
    "total_size": "integer"
  },
  "parameter": {
    "ascii": "string"
  },
  "patches": {
    "entry_relative_displacement": "integer",
    "parameter_relative_displacement": "integer",
    "payload_offset": "integer",
    "payload_size": "integer"
  },
  "selection": {
    "loader_bits": "integer",
    "optional_header_magic": "integer",
    "pe_machine": "integer"
  }
}
```
