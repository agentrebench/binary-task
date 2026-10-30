# Seven inert reverse-engineering tasks for Harbor

Handoff revision **5.1.1**. `GROUND_TRUTHS.json` contains all seven complete
answer keys; individual keys remain in each task's private `solution/answer.json`
and `tests/contract.json`. The source and derivations are in `review/`.

| Binary filename | Harbor task directory |
| --- | --- |
| `sysbridge.elf` | `tasks/re-55a4b5ca278d/` |
| `modulehost.elf` | `tasks/re-adeefd1c539e/` |
| `inputsvc.elf` | `tasks/re-d628c5a314d6/` |
| `update_agent.elf` | `tasks/re-67cbf1857130/` |
| `compat_host.elf` | `tasks/re-ee5729dca243/` |
| `stage_builder.elf` | `tasks/re-240249cc0123/` |
| `profile_sync.elf` | `tasks/re-703605596814/` |

These are stripped x86-64 ELF files. Realistic external filenames do not change
their bytes. Every Dockerfile maps its named artifact to `/workspace/target.bin`,
so the model's standard tool interface remains the same.

The team handoff is a read-only snapshot. Use the separately writable calibration
copy for new runs or edits, and put Harbor jobs outside the dataset directory with
`--jobs-dir /path/to/runs`. Do not publish calibration edits over the team snapshot.


This is an evaluator-owned Harbor dataset. Each directory in `tasks/` contains
`instruction.md`, `task.toml`, a self-contained `environment/` build, hidden
`tests/`, and an authorized `solution/`. No AgentRE installation, custom Harbor
agent, private campaign controller, host source checkout, or local image tag is
required. Standard Harbor owns execution, artifact collection, logs, and grading.

The seven stripped x86-64 ELF artifacts model bounded behavior using fictional
embedded data. They do not capture input, access a browser, contact destinations,
load executable payloads, inject into processes, or perform architecture switches.
The x86-64 target binaries are never executed by the supplied tools. Original
operational source samples are not included. C, C++, and Rust source and private
derivations are provided separately under `review/` for evaluator inspection.

## Run with standard Harbor

Requirements: Python 3.12+, Docker with Compose, and Harbor 0.25.0. Docker builds
download public dependencies; this is not an offline image archive. The public
Python base image is pinned by multi-architecture registry digest. Build package
versions are recorded during validation; apt repositories are not snapshot-pinned.

```sh
python3.12 -m venv /tmp/harbor-review-venv
/tmp/harbor-review-venv/bin/pip install 'harbor==0.25.0'
/tmp/harbor-review-venv/bin/harbor run -p /path/to/dataset/tasks --jobs-dir /path/to/writable/runs -a oracle --env docker --job-name oracle-check
/tmp/harbor-review-venv/bin/harbor run -p /path/to/dataset/tasks --jobs-dir /path/to/writable/runs -a nop --env docker --job-name nop-check
```

Oracle is an authorized verification control and intentionally receives the
correct answer. Nop submits nothing. Neither is a model rollout. Only environment
files and the public instruction are supplied during a normal model trial.

## Model tool profile

Each task declares its own stdio MCP server through native Harbor
`[[environment.mcp_servers]]` configuration. The image includes the server and
all analysis dependencies. It exposes exactly:

`file`, `strings`, `readelf`, `objdump`, `nm`, `hexdump`, `xxd`, `entropy`, and
structured `final_answer` submission.

The supported stock profile is **Gemini CLI 0.66.0**. Its root-owned system
settings remove all built-in tools and disable skills, hooks, and extensions.
Only the task MCP tools remain available. Public instructions include the answer
shape, so no file-reading helper is needed to inspect it.

```sh
# Supply GEMINI_API_KEY through the evaluator's normal secret configuration.
/tmp/harbor-review-venv/bin/harbor run -p /path/to/dataset/tasks --jobs-dir /path/to/writable/runs -a gemini-cli \
  -m gemini/REVIEWER_MODEL_ID --agent-kwarg version=0.66.0 \
  --env docker --job-name model-review
```

Replace `REVIEWER_MODEL_ID` with a model supported by the evaluator's Gemini API
project. This command uses Gemini CLI; it is not an Antigravity SDK or IDE run.
There are no credentials in this package. Setup may download agent dependencies;
the agent phase uses Harbor's Gemini-host allowlist. Verification uses Harbor's
`no-network` policy. Harbor retains its documented DNS/local/ICMP exceptions;
these policies are not a claim of an entirely disconnected network namespace.

Other marketplace agents can consume the same native MCP task definition, but
must independently disable shell, scripting, file-writing, web, and other
analysis capabilities to satisfy this profile. Harbor has no universal
task-level switch that disables every agent's built-in tools. Merely selecting
an arbitrary shell-capable agent changes the evaluation conditions. Stock Harbor
0.25.0 `antigravity-sdk` uses an allow-all policy and is not certified here as a
static-only substitute.

## Submission and grading

The model calls `final_answer` once with `{"schema_version":1,"answers":{...}}`.
The MCP service writes `/workspace/submission/answer.json`. Harbor collects it and
restores it in a fresh, separate verifier container. Reference values and verifier
code are never copied into the agent image.

The reward is binary: 1 only when all answer groups are exactly correct, otherwise
0. `grade.json` reports diagnostic partial credit separately. Missing, malformed,
contradictory, oversized, duplicate-key, and invalidly typed submissions are
handled deterministically. The verifier reads data and never executes submissions.

## Review and measurement

`inventory.json` binds the binary and answer hashes. `review/` contains private
source, independent derivations, and build/review evidence. `validation/` contains
the checks actually performed for this export. `MANIFEST.json` binds distributed
files. Keep the complete evaluator package out of model-visible workspaces.

These are new behavior-focused task revisions. Previous rollouts describe older
binaries or different execution profiles and do not establish difficulty here.
**No 20–40% pass-rate claim is made for this release.** New fixed, independently
reviewed model runs are required before making that claim. Runtime/control success
does not demonstrate model difficulty.

The supported profile and tool limits are documented in `native-profile.md`.
Upstream task mechanisms: [Harbor configuration](https://docs.harborframework.com/tasks/configuration),
[separate verification](https://docs.harborframework.com/tasks/separate-verifier).
