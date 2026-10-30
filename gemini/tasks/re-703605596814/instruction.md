Analyze this artifact statically. Recover which browser-profile database it selects from its embedded data, which cookie records it retains, and the export request it constructs in memory.

Submit three groups using the supplied answer shape. `profile.database` is the complete selected database path. `cookies.records` lists the final retained records in export order, with their domain, name, value and expiry in Unix seconds. `export` gives the effective method, URL and exact request body; preserve tabs and trailing newlines. Report the implemented selection and decoding behavior for the selected artifacts. The supplied records are fictional; do not execute the artifact or contact any destination.

Analyze `/workspace/target.bin` using only the task-provided static tools: `file`, `strings`, `readelf`, `objdump`, `nm`, `hexdump`, `xxd`, and `entropy`. These tools are exposed by the `static` MCP server with their argument schemas. Paths are restricted to `target.bin` or `/workspace/target.bin`. Tool output is paginated; use the returned `next_output_offset` for the next page. Do not execute, load, debug, or emulate the target. Do not use shell commands, scripts, Python, calculators, byte-operation helpers, web tools, or other analysis tools.

Submit the complete structured JSON object once through the `final_answer` tool. It writes `/workspace/submission/answer.json` for Harbor verification. The public answer shape follows below; it contains types, not answer values.

Write `/workspace/submission/answer.json` as UTF-8 JSON with exactly `{"schema_version": 1, "answers": {...}}`. The group and field types are in `/workspace/answer-shape.json`. Integers are JSON integers, never floats, hex strings, or booleans. Arrays preserve order. Omit an entire group if unknown; included groups must have every documented field and no extras. No prose or alternative answers. Duplicate keys and malformed input earn zero. Each entirely correct group contributes equally to diagnostic partial credit. The task reward is 1 only when every group is correct, otherwise 0. The maximum submission size is 64 KiB.

Artifact SHA-256: `199ade95ff247402852db4bdc53c1382a01ab87abe4035353960592101a864db`. Task revision: `5.1.1`.

Public answer shape:
```json
{
  "cookies": {
    "records": [
      {
        "domain": "string",
        "expires": "integer",
        "name": "string",
        "value": "string"
      }
    ]
  },
  "export": {
    "body": "string",
    "method": "string",
    "url": "string"
  },
  "profile": {
    "database": "string"
  }
}
```
