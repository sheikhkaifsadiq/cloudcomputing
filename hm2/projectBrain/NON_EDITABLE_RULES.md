# NON-EDITABLE ENGINEERING RULES

These rules are the permanent engineering contract for HM2. They must NOT be silently removed or weakened during later development.

1. HM2 MUST use FastAPI for the backend.
2. HM2 MUST use LangGraph for agent orchestration.
3. HM2 MUST use an LLM.
4. HM2 MUST use LLM tool calling.
5. HM2 MUST use Supabase/PostgreSQL as persistent database storage.
6. CRUD operations MUST be performed through backend tools.
7. The frontend MUST NOT directly perform privileged CRUD operations.
8. Destructive operations MUST use Human-in-the-Loop approval.
9. The LLM MUST determine the intended CRUD operation from natural language.
10. Missing information MUST result in a clarification request.
11. Ambiguous requests MUST NOT execute database mutations.
12. The system MUST show the user the interpreted action before destructive execution.
13. Approval MUST explicitly authorize the pending action.
14. Decline MUST cancel the pending action safely.
15. Additional details MUST return the request to the reasoning/validation loop.
16. The system MUST preserve conversation/agent state sufficiently to resume HITL operations.
17. Database errors MUST be handled gracefully.
18. LLM errors MUST be handled gracefully.
19. Tool errors MUST be handled gracefully.
20. API validation errors MUST be handled gracefully.
21. Frontend errors MUST be handled gracefully.
22. No silent exception swallowing.
23. No fake/mock CRUD in the final implementation.
24. No hardcoded user-specific CRUD logic.
25. "Ali" is ONLY an example.
26. The system must work with arbitrary valid database records.
27. CRUD tools must be generic and reusable.
28. All important execution paths must be tested.
29. The application must be verified iteratively after each major change.
30. Do not declare the task complete without running the available tests and verification.
31. Do not knowingly leave TypeScript errors.
32. Do not knowingly leave Python errors.
33. Do not knowingly leave FastAPI startup errors.
34. Do not knowingly leave database/schema errors.
35. Do not knowingly leave API contract mismatches.
36. Do not knowingly leave frontend runtime errors.
37. Do not knowingly leave console errors caused by HM2.
38. Do not knowingly leave broken loading/error/empty states.
39. Do not invent successful test results.
40. Every modification must be reflected in TASK_LOG.md.
41. The final PROJECT_BRAIN.md must describe the actual implementation.
42. Prefer simple, maintainable architecture over unnecessary complexity.
43. Never expose Supabase service-role credentials to the frontend.
44. Validate all tool arguments before database execution.
45. Never execute a destructive action merely because the LLM generated a tool call.
46. Destructive tool execution must be gated by explicit HITL approval.
47. Tool calls must be auditable.
48. CRUD results must be returned to the LLM/frontend in structured form.
49. The system must remain extensible to additional tools and database entities.
50. Never claim "complete" until verification has passed.
