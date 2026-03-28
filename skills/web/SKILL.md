---
name: web
description: "Orchestrates parallel browser automation by dispatching sub-agents to independent Chrome tabs. Use when the task can be decomposed into multiple independent browser workflows that benefit from parallel execution across separate tabs."
---

Decompose the user's task into independent tab-bounded work units — each unit is one site, page, or browser workflow that does not depend on the others. Call `tabs_context_mcp` once to get or create the MCP tab group. Dispatch one sub-agent per work unit in parallel. Each sub-agent's prompt must instruct it to call `tabs_create_mcp` to create its own tab, operate exclusively on its own `tabId` for all subsequent browser calls (`navigate`, `read_page`, `get_page_text`, `javascript_tool`, `form_input`, etc.), and return structured results (not raw HTML dumps). If some units depend on others' output, sequence them into waves: wave 1 runs in parallel, wave 2 receives wave 1 results and runs its own parallel batch, and so on. When all sub-agents return, merge their structured results into a unified response that directly addresses the user's original task.
