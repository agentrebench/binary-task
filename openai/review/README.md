# Evaluator-only evidence

These files are not copied into task environments. Source and independent truth
are supplied for review. Reference/build artifacts describe separate native ARM
validation; x86 target binaries were never executed. Historical review bindings
use original repository-relative paths. `source-map.json` maps packaged evidence
to its original path and SHA-256. Not every historical intermediate build file is
distributed. Missing historical bindings are not runtime dependencies.

The authoring build script is provided as evidence, not as a recipient requirement:
it references the original private compiler setup. The ready-made stripped binary
and native Harbor environment Dockerfile are sufficient to run each task. These
source files cannot be substituted for a clean rebuild claim on another host.
