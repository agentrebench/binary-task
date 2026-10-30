Analyze the stripped artifact statically. It models configuration selection and a bounded input-to-request pipeline over embedded synthetic data. Determine what its normal entry path produces from a fresh state.

- `destination.url`: the complete selected destination URL, including scheme, host, explicit decimal port, and path.
- `capture.text`: the final captured text before request encoding. Represent control characters with standard JSON escapes.
- `request.wire`: the complete generated ASCII application-layer request, including its exact line endings and body, before any transport protection. Represent carriage returns and linefeeds with standard JSON escapes.
- `alternate.url`: the complete URL represented by the highest-priority configuration, using the same formatting as `destination.url`.
- `alternate.selected`: whether that highest-priority configuration supplies the generated request.

Use the program's actual configuration and input behavior. Do not execute the artifact or assume that every decoded destination is selected. Submit the task-specific structured JSON answer.
