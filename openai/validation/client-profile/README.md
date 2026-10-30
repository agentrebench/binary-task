# OpenAI provider through stock Harbor OpenCode

This overlay uses Harbor **0.25.0**'s built-in `opencode` agent and official
OpenCode **1.19.5**. It is an OpenAI API profile, not a Codex CLI profile.
The seven binaries, questions, answer schemas, graders, and static MCP server
remain unchanged. Do not apply it to the sealed team snapshot; use a separate
provider copy.

Copy `opencode-managed.json` into each task's `environment/`. Remove the Gemini
settings file and its Docker COPY. Add the supplied `Dockerfile.fragment` while
the Docker build still runs as root. Replace the settings filename in
`.dockerignore`. Preserve the existing final `USER 1000:1000`, target permissions,
and canonical `/workspace/target.bin` path. Root ownership and read-only managed
settings are required. The six environment switches disable auxiliary downloads,
default plugins, external skills and Claude configuration discovery.

Keep native `[[environment.mcp_servers]]` with server name `static`. Change the
agent network allowlist to `api.openai.com` and the supported-profile metadata to
`opencode-1.19.5-managed-static-only`. Setup needs public download access for the
pinned npm installation. Preserve Harbor's separate verifier and its network
policy. Harbor's native network exceptions remain as documented in the dataset.

From a writable work directory, use ordinary Harbor:

```sh
harbor run -p /path/to/openai/tasks --jobs-dir /path/to/runs \
  -a opencode -m openai/REVIEWER_MODEL_ID --agent-kwarg version=1.19.5
```

Supply `OPENAI_API_KEY` using the evaluator's normal secret configuration. Select
an OpenAI API model available to that project that supports tool calls. No model
ID or credential is stored in the managed policy. Stock Harbor registers the
selected model and task MCP server. No custom Harbor agent, host runner, proxy,
or patched CLI is needed. The offline fixture's model string is only a test label;
it does not fix the model used by this profile.

The managed policy denies all tools and permits exactly the nine `static_` MCP
names. The same rule applies to the built-in `build` agent; auxiliary agents are
disabled. This removes shell, script execution, file reads/writes, web, skills,
delegation, and other built-in tools from the model's request. The public prompt
already contains the answer shape. The model submits through `static_final_answer`.
The permission rules remain effective with the `--dangerously-skip-permissions`
flag that stock Harbor supplies. Conflicting ordinary configuration was tested.

`release.json` records public npm identities and the tested arm64 binary hash.
`validation.json` binds the actual tests. `evidence/` contains request captures
against a loopback fake Responses endpoint inside Docker `--network none`, with
a dummy credential. The real CLI discovered the production MCP server. An
unlisted shell call did not execute; `static_file` and `static_final_answer` did.
Every captured request exposed exactly nine tools. Synthetic usage/cost fields
in those fake responses are not billing or live model measurements.

To reproduce after building one provider task environment, download the official
pinned platform package identified in `release.json`, verify its npm integrity,
and run:

```sh
python3 test_profile.py --image YOUR_BUILT_TASK_IMAGE \
  --binary /path/to/official/opencode \
  --task-environment /path/to/task/environment \
  --target-filename sysbridge.elf --output /tmp/openai-profile-evidence
```

This is a developer validation helper, not a runtime dependency. The recorded
test used Linux arm64; x86-64 packaging and live model execution need their own
checks. Oracle/no-op controls and live difficulty measurements are reported
separately. No 20–40% success claim follows from tool-policy validation.

References: [OpenCode managed configuration](https://docs.opencode.ai/docs/config/),
[tool permissions](https://docs.opencode.ai/docs/permissions/),
[MCP configuration](https://docs.opencode.ai/docs/mcp-servers/).
Codex was inspected first using installed Harbor source and
[official OpenAI configuration documentation](https://learn.chatgpt.com/docs/config-file/config-reference).
Its complete built-in restriction profile was not established here; OpenCode
provides the tested native policy for this OpenAI-provider copy.
