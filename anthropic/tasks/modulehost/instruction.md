Analyze this artifact statically and recover its modeled image-loading behavior from the embedded data. No embedded code is executed by this model.

Report four groups. `mapping` gives the image name, computed entry-point address, accepted section names and rejected section names, each in section-table order. `imports.bindings` gives successful import requests and their final resolved module/API names. `rejected.imports` gives rejected requests and the rejection text produced by the model. Preserve request order within each list. Write names as `module!symbol`; ordinal requests use `module!#number`, with a decimal ordinal and the module spelling stored in the artifact.

`relocations` gives the modified data-pointer RVAs and their resulting values in relocation-record order, plus the RVAs of non-padding entries the model skips. Use decimal JSON integers for addresses and pointer values. Follow the supplied answer shape. Do not execute, load, debug or emulate the artifact.

Analyze `/workspace/target.bin` using only the task-provided static tools: `file`, `strings`, `readelf`, `objdump`, `nm`, `hexdump`, `xxd`, and `entropy`. These tools are exposed by the `static` MCP server with their argument schemas. Paths are restricted to `target.bin` or `/workspace/target.bin`. Tool output is paginated; use the returned `next_output_offset` for the next page. Do not execute, load, debug, or emulate the target. Do not use shell commands, scripts, Python, calculators, byte-operation helpers, web tools, or other analysis tools.

Submit the complete structured JSON object once through the `final_answer` tool. It writes `/workspace/submission/answer.json` for Harbor verification. The public answer shape follows below; it contains types, not answer values.

Write `/workspace/submission/answer.json` as UTF-8 JSON with exactly `{"schema_version": 1, "answers": {...}}`. The group and field types are in `/workspace/answer-shape.json`. Integers are JSON integers, never floats, hex strings, or booleans. Arrays preserve order. Omit an entire group if unknown; included groups must have every documented field and no extras. No prose or alternative answers. Duplicate keys and malformed input earn zero. Each entirely correct group contributes equally to diagnostic partial credit. The task reward is 1 only when every group is correct, otherwise 0. The maximum submission size is 64 KiB.

Artifact SHA-256: `df00772b0e41fb182e5cb74ec4da4fb7aa1e04d973526241c0d213e224d7add0`. Task revision: `5.1.1`.

Public answer shape:
```json
{
  "imports": {
    "bindings": [
      {
        "requested": "string",
        "resolved": "string"
      }
    ]
  },
  "mapping": {
    "entrypoint": "integer",
    "image": "string",
    "rejected_sections": [
      "string"
    ],
    "sections": [
      "string"
    ]
  },
  "rejected": {
    "imports": [
      {
        "reason": "string",
        "requested": "string"
      }
    ]
  },
  "relocations": {
    "rvas": [
      "integer"
    ],
    "skipped_rvas": [
      "integer"
    ],
    "values": [
      "integer"
    ]
  }
}
```
