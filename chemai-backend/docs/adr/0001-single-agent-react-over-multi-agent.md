# Single Agent ReAct over Multi-Agent

We chose LangGraph `create_agent` (single ReAct Agent + Persona YAML filtering) over the v1 Multi-Agent architecture (Coordinator + Router + 6 Sub-Agents).

v1 achieved ~75% routing accuracy because the Coordinator LLM had to pick one of6 sub-agents in a single decision — coarse granularity led to misrouting ("出题" went to search_expert instead of exam_expert). v2 achieves ~87% because the LLM directly selects from15-30 tools filtered by Persona, with tool docstrings providing fine-grained guidance. v2 also eliminates the Coordinator→Router round-trip, reducing latency by ~40% (P50 ~1.5s).

The v1 multi-Agent code is preserved as a fallback, switchable via API parameter.
