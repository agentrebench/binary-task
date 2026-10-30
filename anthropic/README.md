# Seven static reverse-engineering tasks — anthropic

Task content revision **5.1.1**, provider profile revision **1**.
This folder is an independent Harbor dataset using the stock **claude-code** agent.
Model inference uses the **anthropic API**. Use an available model supported by
that agent and your provider account; selecting a provider does not establish
compatibility with every model identifier or API gateway.

The seven stripped x86-64 Linux ELF binaries, task prompts, answer schemas,
static-analysis MCP server, private ground truths and grader are unchanged from
the original Gemini dataset. These are inert synthetic samples inspired by malware
techniques. Some embed PE-shaped data; they are not native Windows executables.
The supplied runtime never executes the targets.

## Run

Install Python 3.12+, Docker with Compose, and `harbor==0.25.0`. Public dependencies
are downloaded during Docker build and standard agent setup. The base image is
pinned by digest; apt repositories are not snapshot-pinned. Provide `ANTHROPIC_API_KEY`
using your normal secret configuration. Credentials are not included in this folder.

```sh
./run.sh MODEL_ID /absolute/path/to/results
```

`run.sh` only selects the packaged profile and invokes stock `harbor run`; it is not
a custom agent or evaluation runner. It accepts a model ID with or without the
`anthropic/` prefix. `AGENTRE_HARBOR_BIN` can select a Harbor executable in an
external virtual environment. Keep results and virtual environments outside this
dataset. The exact agent version and arguments are in `provider-profile.json`.

Standard controls require no model API key:

```sh
harbor run -p ./tasks --jobs-dir /absolute/path/to/results -a oracle --env docker
harbor run -p ./tasks --jobs-dir /absolute/path/to/results -a nop --env docker
```

The model uses only the task's eight static analysis tools and `final_answer`,
which writes `/workspace/submission/answer.json`. The separate verifier awards
1 only for an entirely correct answer; diagnostic partial credit is recorded
separately. Use the supplied provider profile to preserve these restrictions.

## Files and ground truths

- `tasks/<task-name>/instruction.md`: unchanged prompt and submission format.
- `tasks/<task-name>/task.toml`: Harbor resources, network policy and native MCP registration.
- `tasks/<task-name>/environment/`: Docker build, realistic binary filename, public schema,
  static tools and provider restrictions. Docker copies the binary to `/workspace/target.bin`.
- `tasks/<task-name>/tests/contract.json`: that task's private grading truth and contract.
- `tasks/<task-name>/solution/answer.json`: that task's complete correct answer.
- `GROUND_TRUTHS.json`: all seven answers keyed by binary filename.
- `review/`: evaluator source, fixtures, independent derivations and build evidence.
- `validation/`: provider checks; `validation/gemini-v5.1.1/` contains explicitly
  inherited evidence from the original environment and is not a new-provider run.
- `BINARY_NAMES.json`, `inventory.json`, `provider-profile.json`, `MANIFEST.json`:
  identity, provenance, execution profile and file integrity.

Source code, correct answers, private verification files and evaluator evidence
are excluded from the agent image. Give the complete folder to the evaluator;
Harbor supplies the model only the public instruction and task environment.

## Validation scope

Read `PROFILE_STATUS.md` and the reports in `validation/` for completed checks and
their limitations. Offline client tests use scripted local API responses; they
establish tool registration and plumbing, not model reasoning performance.
Oracle/no-op checks establish runtime and grading behavior. Live provider access,
model-specific success rates and Argon/Antigravity calibration are separate.

This folder targets direct API-key access to `api.anthropic.com`.
OAuth, Azure, Bedrock, Vertex and custom gateways require separate configuration
and validation. Agent setup has public network access; inference uses the task's
allowlist and the separate verifier uses Harbor's no-network policy, including
Harbor's native DNS/local/ICMP exceptions. See `native-profile.md` for details.

## Task directories

`tasks/sysbridge/`, `tasks/modulehost/`, `tasks/inputsvc/`, `tasks/update_agent/`, `tasks/compat_host/`, `tasks/stage_builder/`, `tasks/profile_sync/`.

Each directory matches its binary filename. `TASK_NAMES.json` maps the former identifiers
retained in historical validation evidence to the current names.
