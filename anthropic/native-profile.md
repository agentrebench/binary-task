The configuration described below is already applied to this folder. Referenced client test scripts, release records and evidence are under `validation/client-profile/`; these are reviewer materials, not runtime dependencies.

# Anthropic profile for the seven Harbor tasks

Use **stock Harbor 0.25.0** with its built-in **claude-code** agent and the
official **Claude Code npm release 2.1.112**. The binary artifacts, prompts,
answer shapes, benchmark MCP runtime, private reference answers, and verifier
are unchanged from the seven-task source dataset.

This profile changes only provider execution settings. The agent-phase network
allowlist is `api.anthropic.com`. Use an `ANTHROPIC_API_KEY` supplied through the
recipient's normal secret configuration; no credential belongs in the dataset.
Model selection is intentionally left to the reviewer and their account.

```sh
harbor run -p /path/to/anthropic/tasks --jobs-dir /path/to/writable/runs \
  -a claude-code -m anthropic/REVIEWER_MODEL_ID --env docker \
  --agent-kwarg version=2.1.112 --agent-kwarg permission_mode=dontAsk
```

No AgentRE host package, custom Harbor agent, or separate model loop is needed.
The model uses the task-declared stdio MCP server and calls `final_answer` to
write the same structured submission that all profiles grade.

## Image changes

- Replace `environment/gemini-system-settings.json` with
  `environment/claude-managed-settings.json` and update `.dockerignore`.
- In the task Dockerfile, create `/etc/claude-code` instead of `/etc/gemini-cli`.
  Copy the new file to `/etc/claude-code/managed-settings.json`; keep it owned by
  root and remove its write permissions before switching to user `1000:1000`.
- Preinstall the exact tested official CLI while building as root:
  `RUN npm install --global --omit=optional --ignore-scripts @anthropic-ai/claude-code@2.1.112`.
  Stock Harbor checks `claude --version`, sees the matching version, and skips
  its normal native-binary bootstrap. This binds the profile to the npm CLI
  used in the offline validation. There is no wrapper around `claude`.
- In `task.toml`, set `supported_agent_profile` to
  `claude-code-2.1.112-managed-static-only` and the agent's `allowed_hosts` to
  `["api.anthropic.com"]`. Preserve the environment and verifier network phases.

The existing public Docker base, tools, hidden verifier image, target permissions,
nonroot user, capability drops, and no-new-privileges configuration remain intact.

## Tool restrictions

The root-owned managed settings deny every builtin present in the pinned
release. This includes shell execution, filesystem reading and writing,
search, web, scheduling, skill invocation, and subagent invocation. Permission
allow rules list precisely the eight benchmark analysis tools plus `final_answer`.
MCP is limited to the exact task command, hooks are disabled, external plugin
marketplaces are disallowed, automatic memory is disabled, and MCP tool search
is disabled so all nine schemas are available directly.

The CLI exposes exactly these tool names to the model:

`mcp__static__file`, `mcp__static__strings`, `mcp__static__readelf`,
`mcp__static__objdump`, `mcp__static__nm`, `mcp__static__hexdump`,
`mcp__static__xxd`, `mcp__static__entropy`, `mcp__static__final_answer`.

Managed rules override conflicting user/project/CLI permission rules. A request
for bypass mode is downgraded to `dontAsk` by this release. Its init metadata can
still list bundled skill and agent names; those entries are not callable tools.
The offline check verifies the actual API tool definitions and forces forbidden
`Skill` and `Agent` calls, both of which are rejected.

## Validation and limits

`test_profile.py` runs the unmodified official CLI against a scripted localhost
Messages API in a Docker container with `--network none`. It uses a dummy key,
the production MCP server, and the actual stripped `profile_sync.elf` bytes.
It checks exact tool registration, permitted `file` and `final_answer` calls,
rejection of eight forbidden builtin calls, conflicting user/project settings
and hooks, and a requested bypass mode. `validation.json` contains observations
and hashes. No target execution, paid inference, real provider request, or
credential inspection occurs. Token/cost fields the CLI derives from scripted
responses are illustrative and are not provider charges.

This establishes the configured local tool and submission path. Real provider
authentication, model availability, model trajectories, and difficulty are not
tested by the scripted checks. The recipient must use an account-supported
model. A different CLI version requires renewed capability validation. OAuth,
Bedrock, Vertex, custom endpoints, and third-party agents are not this profile.

The private `solution/`, `tests/`, `review/`, and consolidated ground truths stay
outside the agent-visible image. Keep all evaluation results outside the frozen
task directory.

## Official references

- [Managed settings deployment](https://code.claude.com/docs/en/managed-settings)
  documents the Linux policy location and precedence.
- [Permission configuration](https://code.claude.com/docs/en/permissions)
  documents tool denial and managed-rule enforcement.
- [CLI reference](https://code.claude.com/docs/en/cli-reference)
  distinguishes allowed calls from available tools.
- [MCP configuration](https://code.claude.com/docs/en/mcp)
  documents stdio servers and policy controls.

Current documentation may describe newer behavior. The pinned release's actual
offline behavior and package hashes are the authority for the claims above.
