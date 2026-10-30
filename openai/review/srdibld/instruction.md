Analyze how the stripped artifact selects a loader-data template and constructs its final byte buffer from the embedded inputs.

Report the payload's PE machine value, optional-header magic, and selected loader width in `selection`. In `layout`, report the selected loader size, payload size, parameter offset, total buffer size, and entry offset. All offsets are zero-based relative to the final combined buffer; total size includes any terminating parameter NUL.

In `patches`, report the values actually written for payload offset, payload size, entry-relative displacement, and parameter-relative displacement. Each relative displacement is measured from immediately after its own four-byte patch location. In `parameter.ascii`, give the final parameter text without its terminating NUL. Use decimal JSON integers.

The payload and loader templates are deliberately inert data. The artifact constructs bytes without loading or executing them. Use static analysis only.
