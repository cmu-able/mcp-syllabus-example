Excellent — here’s the teaching-guide version of your Markdown slide deck.
Each major slide group now includes Instructor Notes sections that tell you how to teach, demo, and emphasize key takeaways.
It’s ready to use in Marp, Quarto, or Reveal.js.

⸻

Distributed API Design in the Age of LLMs and MCP

17-679 — Fall 2025

Instructor: Bradley Schmerl
Duration: 80 minutes

⸻

Agenda
	1.	Traditional API design patterns
	2.	How LLMs change API requirements
	3.	The Model Context Protocol (MCP)
	4.	Case Study: Syllabus → Calendar → Reminders
	5.	Designing for distributed, agent-driven APIs
	6.	Discussion & implications

⸻

💬 Instructor Notes
	•	Use this slide to frame the 80 minutes: “Today we’ll see how APIs evolve once LLMs become clients.”
	•	Ask: “Who here has built or called an API?” to gauge the baseline.
	•	Mention that this lecture bridges classic distributed design and AI-native systems.

⸻

1. Traditional APIs: The “Human-First” Era

Core types:
	•	REST (HTTP + JSON)
	•	GraphQL
	•	gRPC

Typical focus:
	•	Clear resources (/users/123)
	•	Deterministic schemas
	•	Versioning & documentation for humans
	•	Client libraries for developers

⸻

Example

GET /weather?city=Pittsburgh
→ { "temp": 82, "humidity": 74 }

✅ Designed for human developers
❌ Brittle for LLMs — relies on context (“°F” implied, terse keys, no schema)

⸻

Key Properties

Concern	Traditional Focus
Discovery	Human-readable docs
Validation	SDK, type system
Evolution	Semantic versioning
Usage	Hand-written clients
Observability	Logging, metrics


⸻

💬 Instructor Notes
	•	Keep this brisk (8–10 minutes total).
	•	Ask students: “What’s the last REST or gRPC service you used?”
	•	Emphasize assumed human intuition: humans read docs, interpret parameter meanings, handle errors.
	•	Lead into: “What if our client can’t read the docs?”

⸻

2. The Shift: LLMs as API Consumers

From DZone: ￼The New API Economy With LLMs￼:

“The rise of LLMs is creating a new API economy where natural language replaces structured code as the interface.”

⸻

What Changes When the Consumer Is an LLM?
	•	LLMs call APIs dynamically, not through SDKs.
	•	They infer context rather than read docs.
	•	Need machine-interpretable schemas (JSON Schema / MCP).
	•	Chain tools together to complete goals.
	•	Require validation, guardrails, idempotency to stay safe.

⸻

API Qualities Now Matter Differently

Quality	Human	LLM / Agent
Discoverability	Docs	JSON schema / MCP registry
Input tolerance	Manual debugging	Strict schema validation
Idempotency	Optional	Essential
Error handling	Read logs	Machine-parseable codes
Versioning	SDK updates	Schema negotiation


⸻

💬 Instructor Notes
	•	10 minutes total including short discussion.
	•	Use a relatable example: “ChatGPT calling a travel API.”
	•	Ask: “What happens if the API expects a field name dest but the model sends destination?”
	•	Connect to the DZone quote: “Natural language is not enough without structure.”

⸻

3. Model Context Protocol (MCP)

From Glama.ai — ￼MCP vs API￼:

“MCP isn’t replacing APIs — it makes them consumable by models and agents.”

⸻

Traditional API vs MCP

Aspect	API	MCP
Audience	Humans	Agents / LLMs
Interface	Endpoints	Tools (JSON Schema)
Discovery	Docs / OpenAPI	Runtime registry
Transport	HTTP / gRPC	Any (WebSocket, local, etc.)
Invocation	Manual / SDK	Model-selected
Contract	Developer-written	Machine-interpretable


⸻

Why MCP Matters
	•	Agents can discover tools dynamically.
	•	Tools define strict input/output schemas.
	•	Example tool definition:

{ "type": "function",
  "function": { "name": "create_event", "parameters": {...} } }


	•	Enables orchestration across services: parse → plan → create events.

⸻

💬 Instructor Notes
	•	Spend ~10 minutes here.
	•	Draw parallels to OpenAPI, but emphasize runtime discovery and agent autonomy.
	•	Quote the Glama.ai article directly; students appreciate concrete industry context.
	•	Ask: “Why might a human API design still not be usable by an LLM even with OpenAPI?”

⸻

4. Case Study: Multi-Service Syllabus Planner

Goal:
Turn syllabi PDFs → structured course data → calendar events & reminders.

⸻

Architecture Overview

User/CLI
  ↓
Orchestrator (LLM + MCP client)
  ├─> Syllabus MCP Server  (parse_syllabus)
  ├─> Calendar MCP Server  (create_calendar_event)
  └─> Reminders MCP Server (create_reminder)

Each MCP server exposes JSON-schema tools;
the orchestrator discovers and chains them.

⸻

Tool Registry Example

{
  "name": "create_calendar_event",
  "endpoint": "http://localhost:8002/events",
  "input_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "start": {"type": "string", "format": "date-time"},
      "end": {"type": "string", "format": "date-time"}
    },
    "required": ["title", "start", "end"]
  }
}


⸻

Orchestrator Logic

completion = client.chat.completions.create(
    model="gpt-4o",
    tools=tool_schemas_for_llm(tools),
    messages=[
        {"role": "system", "content": "You can call tools to plan events."},
        {"role": "user", "content": json.dumps(parsed_syllabi)},
    ]
)

Then executes:

call_tool(calendar_tool, event)
call_tool(reminder_tool, reminder)


⸻

Example Output (Truncated)

Total calendar events: 32
Total reminders: 5
 - Event: Formal Methods Lecture (Mon/Wed)
 - Event: Stats Lecture (Tue/Thu)
 - Reminder: HW2 Logic due 2025-09-03T09:30:00


⸻

💬 Instructor Notes
	•	Spend ~25 minutes total on this section; it’s the live-demo centerpiece.
	•	Start with the architecture slide to orient.
	•	Walk through each component quickly, then open your terminal or pre-recorded demo.
	•	Show:
	1.	The tool_registry.json
	2.	A sample parsed syllabus JSON
	3.	The planner output (events + reminders)
	•	Emphasize that each call is schema-driven — no hardcoded endpoints.
	•	Optional discussion: “Where would GraphQL fit?” (data aggregation).

⸻

5. Designing for Distributed, Agent-Driven APIs

New Design Principles
	1.	Schema clarity > documentation prose
	2.	Discovery — publish tools, not endpoints
	3.	Composability — enable orchestration across services
	4.	Safety — validate, constrain, log tool calls
	5.	Observability — track agent actions for auditability

⸻

Developer vs Agent Clients

Design Target	Developer	LLM / Agent
Reads Docs	✅	❌
Intuits intent	✅	❌
Follows schema	Maybe	✅
Chains calls	Manual	Autonomous
Needs guardrails	Less	More


⸻

Practical Implications
	•	APIs must be self-describing and self-discoverable.
	•	Treat registries or MCP manifests as part of your architecture.
	•	Add sandboxing, idempotency, audit trails.
	•	Version tool definitions (v1.create_event).
	•	Integrate LLM behavior into your API governance pipeline.

⸻

💬 Instructor Notes
	•	~10 minutes.
	•	Connect to real-world patterns: internal developer platforms, API gateways, service catalogs.
	•	Ask students: “What happens if an LLM uses the wrong version of a tool?”
	•	Optional analogy: MCP is like Kubernetes CRDs for APIs — discoverable specs that can evolve.

⸻

6. Class Activity (5 minutes)

Exercise:
Design a new tool:

“SlackNotificationTool” – posts reminders to a Slack channel.

Define:
	•	name, endpoint, input_schema, example call.

Discuss:
	•	Validation?
	•	Rate limits?
	•	Security for agent access?

⸻

💬 Instructor Notes
	•	Give them 3 minutes to sketch JSON on paper or laptop.
	•	Pick one student group to share; critique: “Is this schema discoverable? Safe?”
	•	Reinforce the idea that defensive design is essential in AI-facing APIs.

⸻

7. Reflections from Industry

From Medium: Are LLMs the New APIs?￼

“In 2025, AI stopped being an application feature and became infrastructure — a way services talk to each other.”

Takeaway:
	•	The API economy is now an AI economy.
	•	Systems must speak to both humans and agents.

⸻

💬 Instructor Notes
	•	Use this slide to zoom out to industry perspective (5 minutes).
	•	Summarize all three articles:
	•	DZone → API economy shift.
	•	Medium → AI as infrastructure.
	•	Glama → MCP as enabler.
	•	Pose question: “If LLMs are infrastructure, what happens to SDKs?”

⸻

8. Key Takeaways
	1.	APIs are no longer only for humans.
	2.	Schemas are the new documentation.
	3.	MCP enables agent interoperability.
	4.	Distributed systems must expose capabilities as tools.
	5.	Your syllabus planner demo = microcosm of AI-native design.

⸻

💬 Instructor Notes
	•	Wrap-up slide (~3 minutes).
	•	Reinforce the “human → agent” transition.
	•	Mention that their assignment or lab will extend this by adding one more tool or protocol (GraphQL, Slack, etc.).

⸻

9. Closing & Discussion

Reflection Prompt:

How would your company’s API strategy need to change
to support LLMs and agents as clients?

Next week: GraphQL & gRPC — bridging structured APIs and generative interfaces.

⸻

💬 Instructor Notes
	•	Leave 5 minutes buffer for questions.
	•	Encourage practical thinking: “Who owns the schema registry?”
	•	Optionally show a visual of your full architecture again for closure.

⸻

Would you like me to convert this Markdown deck into a Marp / Quarto presentation template (with syntax highlighting and slide styling) so you can drop it into your Git repo or course site?