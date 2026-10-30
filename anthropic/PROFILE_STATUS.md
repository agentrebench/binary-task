# Provider profile status — anthropic

Configured for stock Harbor 0.25.0 with Claude Code npm 2.1.112.

Completed checks: seven oracle rewards of 1, seven no-op rewards of 0, four
representative MCP/sandbox/reset/network controls, one installation-only check,
per-task Harbor lint, launcher argument checks, unchanged-content comparison,
and the client profile's exact-tool and forbidden-call checks.

Client checks used a scripted local API with dummy credentials in disconnected
Docker containers. They are not model trajectories or paid inference. Runtime
controls executed no targets. The two provider clients and their system prompts
differ; preserve the profile identity when comparing model outcomes.

Live authentication, account-specific model availability and difficulty have not
been measured. Testing used an ARM64 Docker host. Other architectures and API
gateways require their own verification. The original 20–40% Argon target remains
a separate calibration objective, and no current sample success rate is claimed.

Ground truths remain both per task and consolidated; all reviewer-only materials
are outside the agent image. The inherited Gemini reports are explicitly under
validation/gemini-v5.1.1 and are not new-provider measurements.

The parent INDEPENDENT_REVIEW.json records final manifest verification.
