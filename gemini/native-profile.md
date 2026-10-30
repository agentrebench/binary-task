# Supported standard Harbor tool profile

Use Harbor 0.25.0 with its built-in `gemini-cli` agent and
`--agent-kwarg version=0.66.0`. Each task's `task.toml` registers its own `static`
stdio MCP server. The task Dockerfile installs all server dependencies and copies
`environment/gemini-system-settings.json` into root-owned
`/etc/gemini-cli/settings.json`; no separate settings installation is needed.

The system settings use `tools.core = []`, disable skills and hooks, and set a
nonempty extension allowlist that matches no extension. They override conflicting
user/project settings. Tool registration is independent of Harbor's normal
`--yolo` approval flag. The model sees the eight approved analysis tools plus
`final_answer`; the CLI may prefix their names with `mcp_static_`.

Python and shell binaries exist for trusted Harbor setup and the tool service.
They are not model-callable tools in this supported profile. The MCP service
validates typed arguments, confines file access to the target, runs fixed commands,
and accepts a single bounded structured submission. No arbitrary command or
script endpoint is exposed. The tool log is evidence, not a tamper-proof boundary
against a different agent that has filesystem access.

Other agents require their own verified built-in-tool restrictions. Task MCP
registration does not disable their other tools. In particular, stock Harbor
0.25.0 `antigravity-sdk` has an allow-all policy and does not reproduce this profile.
Gemini CLI outcomes must not be labeled Antigravity outcomes.

Only API-key access to `generativelanguage.googleapis.com` is configured during
the agent phase. Setup has internet access for standard agent installation.
Verifier execution uses Harbor's `no-network` policy, which retains native
DNS/local/ICMP exceptions. OAuth, Vertex, and custom API endpoints need
their own reviewed network settings and are not covered by this profile.

The `validation/` records distinguish offline component checks from complete
Harbor trials:

- `native-profile-control.json`: published CLI settings loader and tool registry,
  with conflicting lower-precedence settings and a schema-only MCP control.
- `native-profile-production.json`: the same registry with the actual packaged
  MCP implementation and an inert prototype target. This checks tool discovery,
  not a model solve of the new artifacts.
- `mcp-offline-tests.json`: tool schemas, validation, bounded output, forbidden
  calls, atomic submission, and actual stdio protocol tests.
- `native-profile-release.json`: pinned public CLI/core package identities.
- `harbor-controls.json`: final task runtime controls, once completed.

The original TCP-connect-only network probe was inconclusive because Harbor's
transparent proxy accepts the local connection before checking the destination.
Application-level DNS, HTTP, and TLS checks are recorded separately; the original
observations are retained. Only a valid remote response establishes egress.

Component reports preserve original authoring paths in their hash bindings.
Those paths are provenance, not runtime dependencies or recipient commands.
The package does not claim an independently reproduced live model run, full
cross-architecture validation, or a measured difficulty range. Use the normal
Harbor commands in `README.md` for recipient oracle and no-op checks.
