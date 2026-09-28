# Implementation notes

These are local implementation gaps. Frozen architecture/schema docs are unchanged.

## Incomplete v0 types

The typed Action and Condition taxonomies include `NAVIGATE`, `WAIT`, and `ROUTE_MATCHES`. Their executable payload fields are not fully specified by the frozen docs.

- **NAVIGATE:** the schema names the action type and constrains it to allowlisted entry points / stable navigation contexts. It does not define a serialized payload. `NavigateAction` currently carries only `type`.
- **WAIT:** the schema and D020 require a condition to become true within a wait policy. Condition vs WaitPolicy ownership in the serialized action/step is not fully specified. `WaitAction` currently carries only `type`. A typed `Condition` must be bound later without inventing timing fields now.
- **ROUTE_MATCHES:** the condition type exists in the hierarchy. No comparison/pattern field is documented. `RouteMatchesCondition` currently carries only `type`.
- **BusinessOutcome.result_payload:** the frozen schema lists an optional `result_payload` conceptually. Its serialized shape is not defined. It is not implemented.

No replacement schema is being invented until implementation actually requires resolution.
