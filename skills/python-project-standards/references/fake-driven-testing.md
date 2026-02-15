# Fake-Driven Testing Notes

Use this checklist when implementing tests with fake-driven testing (FDT):

- Start from a use-case and define the required dependency interfaces (ports).
- Implement a fake for each external dependency first (database, queue, API, file store, clock).
- Write tests against the fake-backed system to lock behavior before infrastructure code exists.
- Keep domain logic free of framework and I/O details.
- Add a real adapter later and verify it with contract tests using the same expectations as the fake.
- Fail fast on contract mismatches between fake and real adapters.

Reference material:
- https://smithery.ai/skills/dagster-io/fake-driven-testing
