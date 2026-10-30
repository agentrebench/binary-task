Analyze the stripped artifact's compatibility gate and embedded request stream. Recover the API name selected by its name lookup and the process/native machine identifiers required by that selected descriptor. Give exact API spelling and decimal machine values in `platform`.

In `transition_data`, report the entry and return segment selectors, the transition-marker bytes as lowercase hexadecimal, and the context width in bytes used by the selected path.

In `requests`, report each request's acceptance decision and the effective full-width target value, in processing order. Rejected requests have effective target zero. Use JSON booleans and decimal integers.

This artifact interprets architecture descriptors and transition markers as inert data. It performs no process injection or architecture transition. Determine its behavior with static analysis only.
