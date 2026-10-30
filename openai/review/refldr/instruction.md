Analyze this artifact statically and recover its modeled image-loading behavior from the embedded data. No embedded code is executed by this model.

Report four groups. `mapping` gives the image name, computed entry-point address, accepted section names and rejected section names, each in section-table order. `imports.bindings` gives successful import requests and their final resolved module/API names. `rejected.imports` gives rejected requests and the rejection text produced by the model. Preserve request order within each list. Write names as `module!symbol`; ordinal requests use `module!#number`, with a decimal ordinal and the module spelling stored in the artifact.

`relocations` gives the modified data-pointer RVAs and their resulting values in relocation-record order, plus the RVAs of non-padding entries the model skips. Use decimal JSON integers for addresses and pointer values. Follow the supplied answer shape. Do not execute, load, debug or emulate the artifact.
