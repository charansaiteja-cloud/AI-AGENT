cd ~/customer-support-agent

python -c 'from pathlib import Path; p=Path("article.md"); p.write_text("""# How I Gave a Customer Support Agent Long-Term Memory With Hindsight

A customer support agent can answer the current question correctly and still feel like it has forgotten the customer. That was the problem I wanted to solve.

I built a full-stack customer support application combining React, FastAPI, SQLite, Ollama, Qwen3 8B, and Hindsight. The application maintains normal conversation history while also retaining useful information that can be recalled in future conversations.

The goal was not simply to build another chatbot. I wanted to explore what happens when customer support becomes a stateful system: one that can remember previous interactions, preferences, and useful context instead of starting from zero every time.

## The Problem With Ordinary Conversation History

Conversation history and long-term memory solve different problems.

A conversation may contain dozens of messages, but only a few pieces of information may remain useful later. A customer might mention a preference, explain a recurring issue, or provide context that becomes important several days later.

Sending the entire conversation history back to the language model is possible, but it does not automatically create useful long-term memory. It can also become increasingly noisy as conversations grow.

For example, imagine a customer says:

> "I prefer concise responses and usually contact support from my phone."

That information may not matter for the current question, but it could be useful during a future support interaction. I wanted the agent to recover that kind of context without requiring the customer to repeat it.

That became the central design problem.

## Architecture

The application is divided into a React/Vite frontend and a FastAPI backend.

The frontend provides the customer-facing chat interface. FastAPI handles API requests, conversation persistence, attachments, and communication with the AI services. SQLite with SQLAlchemy provides the application database.

Ollama provides the local model runtime, with Qwen3 8B handling response generation. Hindsight sits alongside the application as the long-term memory layer.

```text
                    React + Vite
                         |
                         v
                    FastAPI API
                    /         \\
                   /           \\
                  v             v
             SQLite         Ollama
                               |
                            Qwen3 8B
                               |
                               v
                           Hindsight
                               |
                        Long-term memory
