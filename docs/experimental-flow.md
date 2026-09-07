# Experimental flow format

The AI agent outputs experimental procedures as a JSON "experimental flow" — an
intermediate representation connecting the natural-language experimental objective
with the control code actually executed. Constraining the LLM output to structured
JSON suppresses generation variability and enables mechanical validation before
execution.

A flow includes: devices to be used, order of operations, setting parameters,
waiting times, and measurement conditions.

<!-- TODO: document the actual JSON schema with a full example (e.g., the ZIF-8
     two-solution mixing flow), and the validation rules applied before execution. -->
