# Acceptance

- A complete proposal follows the five-node trace and accepts in one iteration.
- An incomplete proposal repairs, then a complete proposal accepts in two iterations.
- A repair with no remaining budget terminates as repair with exhaustion flagged.
- A graph interrupted before finalize resumes from its checkpoint to completion.
- Two thread IDs retain isolated run IDs and statuses.
- No execution adapter or shell call exists in orchestration source.
- Dependency lock contains LangGraph 1.x.
