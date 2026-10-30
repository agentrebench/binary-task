Analyze the stripped artifact's embedded export-resolution requests. Determine the module and the API exports actually selected, the service token obtained for each request, and the bytes from which it is recovered. Use request-processing order for every array.

Report `resolver.module` and `resolver.selected_exports` as exact names present in the artifact. Report the resulting numeric tokens in `service_tokens.values`.

For `recovery`, report whether another stub supplies the token (`used_neighbor`), whether that supplying stub is at a higher address than the selected export's stub (`higher_address`), its export name (`witness_exports`), and the absolute byte distance between the two stub starts (`distance_bytes`). For a direct result, use false for both booleans, the selected export as the witness, and distance zero.

The artifact is an inert model over embedded bytes. It does not issue system calls. Infer its data behavior statically; do not execute it. Submit the complete documented JSON answer using decimal integers and JSON booleans.

Analyze `/workspace/target.bin` using only the task-provided static tools: `file`, `strings`, `readelf`, `objdump`, `nm`, `hexdump`, `xxd`, and `entropy`. These tools are exposed by the `static` MCP server with their argument schemas. Paths are restricted to `target.bin` or `/workspace/target.bin`. Tool output is paginated; use the returned `next_output_offset` for the next page. Do not execute, load, debug, or emulate the target. Do not use shell commands, scripts, Python, calculators, byte-operation helpers, web tools, or other analysis tools.

Submit the complete structured JSON object once through the `final_answer` tool. It writes `/workspace/submission/answer.json` for Harbor verification. The public answer shape follows below; it contains types, not answer values.

Write `/workspace/submission/answer.json` as UTF-8 JSON with exactly `{"schema_version": 1, "answers": {...}}`. The group and field types are in `/workspace/answer-shape.json`. Integers are JSON integers, never floats, hex strings, or booleans. Arrays preserve order. Omit an entire group if unknown; included groups must have every documented field and no extras. No prose or alternative answers. Duplicate keys and malformed input earn zero. Each entirely correct group contributes equally to diagnostic partial credit. The task reward is 1 only when every group is correct, otherwise 0. The maximum submission size is 64 KiB.

Artifact SHA-256: `2d77c0004d872242cfb47140ada051e47a8cf8aa3b08978109b33f2501956731`. Task revision: `5.1.1`.

Public answer shape:
```json
{
  "recovery": {
    "distance_bytes": [
      "integer"
    ],
    "higher_address": [
      "boolean"
    ],
    "used_neighbor": [
      "boolean"
    ],
    "witness_exports": [
      "string"
    ]
  },
  "resolver": {
    "module": "string",
    "selected_exports": [
      "string"
    ]
  },
  "service_tokens": {
    "values": [
      "integer"
    ]
  }
}
```
