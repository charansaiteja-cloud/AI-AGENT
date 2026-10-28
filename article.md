# How I Gave a Customer Support Agent Long-Term Memory With Hindsight

A customer support agent can answer the current question correctly and still
feel like it has forgotten the customer.

That was the problem I wanted to solve.

I built a full-stack customer support application with React, FastAPI, SQLite,
Ollama, Qwen3 8B, and Hindsight. It keeps normal conversation history, but it
also retains useful customer facts that can be recalled in a future
conversation.

The goal was not another chatbot. I wanted to explore what customer support
looks like when it becomes stateful: a system that remembers a customer's
device, preferences, and recurring problems instead of starting from zero every
time.

## Conversation History Is Not Memory

Conversation history and long-term memory solve different problems.

A single conversation may contain dozens of messages, but only a few pieces of
information remain useful later. A customer might mention a preference, explain
a recurring issue, or describe the device they use. Sending the entire
transcript back to the model does not automatically turn that into useful
memory; it mostly adds noise and cost.

For example, a customer says:

> My name is Sarah. I work at Acme Corp. I use Ubuntu 24.04 on a Dell XPS 15,
> and my Wi-Fi keeps disconnecting.

The current answer should address the Wi-Fi problem. The durable facts — name,
company, operating system, device, and recurring issue — are what should
survive the conversation.

I wanted the agent to recover that context later without asking the customer to
repeat it.

## Architecture

The application is split into a React/Vite console, a FastAPI backend, SQLite
for application state, Ollama for local inference, and Hindsight for long-term
memory.

```text
                    React + Vite
                         |
                         v
                    FastAPI API
                    /         \
                   /           \
                  v             v
             SQLite         Ollama
                               |
                            Qwen3 8B
                               |
                               v
                           Hindsight
                               |
                        Long-term memory
```

The boundaries matter. SQLite is the source of truth for customers,
conversations, messages, and attachments. Hindsight is the source of truth for
durable customer context. Ollama is replaceable: the model integration lives in
one service, and the rest of the application does not know how inference
happens.

## One Isolated Memory Bank per Customer

The most important design decision was to give every customer a dedicated
Hindsight bank.

When a customer is created, the backend generates a random `memory_key`. The
bank name is `support-customer-<memory_key>`. Recall always uses that bank, so
scoping is structural rather than a filter that a future query might forget.
Deleting a customer can also delete their complete memory history in one
operation.

That choice makes privacy concrete:

- clearing a customer's memory deletes the whole bank;
- deleting a customer is refused if the bank cannot be erased;
- a bug in one customer's recall cannot expose another customer's facts.

## Explicit Facts, Not Blind Extraction

Hindsight can extract memories on its own, but I wanted the application to
decide which facts are durable enough to keep.

The flow is:

1. Qwen3 receives a strict JSON prompt asking for a small list of durable
   customer facts: name, company, product, operating system, issue, preference,
   or other.
2. The backend validates the response, normalizes capitalization and
   punctuation, removes duplicates, caps each fact at 240 characters, and keeps
   at most eight facts.
3. The selected facts are stored in Hindsight with
   `retain_extraction_mode="chunks"` and observations disabled.

That last part is subtle. Chunk mode tells Hindsight to preserve the exact
facts the application selected instead of running another extraction pass over
them. Hindsight still owns the part that matters most at read time: semantic
recall. The result is deterministic writes with flexible reads.

The conversation itself is retained as a short summary as well. Extracted facts
are useful, but the human context around them — what the customer asked and
what support recommended — is often what makes a later answer feel continuous.

## The Chat Path

A support request moves through several layers:

1. React sends the message and optional attachment IDs to `POST /api/chat`.
2. FastAPI resolves the customer and conversation, validates attachments, and
   loads recent history.
3. Two Hindsight recall queries run in parallel: one focused on the current
   request, one on preferences and recurring context.
4. Recalled facts are deduplicated, capped, and inserted into the system prompt
   with an explicit instruction to treat them as data, never as instructions.
5. Qwen3 generates the reply.
6. The turn is persisted to SQLite and retained in Hindsight.
7. The API returns the reply, recalled memories, message IDs, whether memory was
   used or saved, and the measured latency.

The system prompt also handles a detail that is easy to miss: if the customer
has asked for concise answers in the past, that preference should shape the
current reply. The backend detects preference language in recalled facts and
adds a response-style instruction.

## Making It Feel Fast

Long-term memory adds work to every turn, so latency needed deliberate design.

The first version loaded history, recalled memory, parsed attachments, and
extracted facts one after another. None of those steps actually depend on each
other. The current version runs them concurrently:

- history loading, semantic recall, attachment parsing, fact extraction, and
  Hindsight bank preparation all start together;
- bank creation and the duplicate-fact lookup finish while Qwen3 is generating,
  so the response path only waits for the retain request;
- the user message is written once, after generation, without redundant
  database refreshes;
- history is limited to the most recent configured messages.

The frontend was part of the latency problem too. It used to wait for a full
message refetch and sidebar refresh before showing the reply. Now it renders
the user message immediately, appends the assistant reply as soon as the API
responds, and refreshes the sidebar, memory panel, and service health in the
background.

The result is that memory work overlaps with model generation instead of being
added on top of it.

## The Support Console

The frontend is a three-pane console rather than a single chat box:

- a customer and conversation sidebar with search and lifecycle actions;
- a chat pane with attachments, retryable errors, and per-turn memory badges;
- a memory inspector showing what Hindsight currently knows about the customer.

The memory panel is the part that makes the system legible. It turns "the agent
remembered something" into a list of concrete facts with kinds and timestamps.
It also exposes the clear-memory action, which deletes the customer's bank.

## Attachments

Support is not always text-only, so the chat accepts text, Markdown, CSV, JSON,
and PDF files. Text is extracted and bounded before being added to the model
context. Images are stored and referenced, but the app does not pretend to read
them: if no text preview is available, the prompt says so.

Uploads are validated by extension and size, stored under the conversation ID,
and linked to the user message only after the chat turn succeeds.

## Testing and CI

The backend is tested with Pytest against an isolated in-memory SQLite database.
Fake Ollama and Hindsight services cover the API paths, while `respx` exercises
the real HTTP adapters, including malformed responses and service failures. The
suite currently reaches 92% line and branch coverage with an 85% gate.

The frontend has Vitest and Testing Library tests for the composer, memory
panel, formatting helpers, and the main application flow. ESLint and a
production Vite build run in CI alongside the backend checks and a container
build.

That testing caught several issues that manual clicking would have missed:
duplicate facts, attachment ownership, rollback behavior when the model is
unavailable, and the difference between "memory is disabled" and "memory is
unavailable."

## Challenges and Lessons

The main challenge was not calling Hindsight. It was deciding what memory means
for this product.

Storing every message is easy and mostly useless. Storing a small, explicit set
of durable facts is harder because it requires judgment about what should
survive. Separating fact selection (application) from semantic recall
(Hindsight) made that judgment testable.

The second lesson was that memory is a privacy feature as much as a personalization
feature. A bank per customer, a random key, and deletion that removes the whole
bank are not implementation details; they are the difference between a demo and
something you could responsibly run with real customer data.

The third lesson was about perceived performance. A reply that takes the same
time but appears immediately feels dramatically faster. Overlapping independent
work and rendering optimistically was as valuable as any model-level tuning.

## What I Would Improve Next

The current implementation is intentionally focused on the memory workflow. The
next steps would be:

- authentication and per-user authorization before any real deployment;
- a production database and external rate limiting for multiple instances;
- richer ticket workflows connecting conversations to status and assignment;
- memory editing and expiration controls for customers and support agents;
- observability around recall quality, not just latency and errors.

The architecture is ready for those changes because the frontend, API,
database, model runtime, and memory layer each have a clear responsibility.

## Resources

- Hindsight: <https://github.com/vectorize-io/hindsight>
- Hindsight documentation: <https://hindsight.vectorize.io/>
- Vectorize: <https://vectorize.io/>
- Source code: <https://github.com/charansaiteja-cloud/AI-AGENT>

## Final Thoughts

Building this project changed how I think about AI support systems. The language
model is only one part of the experience. A useful agent also needs
persistence, scoped memory, clear APIs, a legible interface, error handling,
tests, and a deployment path.

The most important result was not getting an AI response on screen. It was
creating a system where information survives beyond a single conversation and
becomes useful later — without losing track of which customer it belongs to.
