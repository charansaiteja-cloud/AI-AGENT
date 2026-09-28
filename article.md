cd ~/customer-support-agent

cat > article.md <<'EOF'
# How I Gave a Customer Support Agent Long-Term Memory With Hindsight

A customer support agent can answer the current question correctly and still feel like it has forgotten the customer.

That was the problem I wanted to solve.

I built a full-stack customer support application combining React, FastAPI, SQLite, Ollama, Qwen3 8B, and Hindsight. The application maintains normal conversation history while also retaining useful information that can be recalled in future conversations.

The goal was not simply to build another chatbot. I wanted to explore what happens when customer support becomes a stateful system: one that can remember previous interactions, preferences, and useful context instead of starting from zero every time.

## The Problem With Ordinary Conversation History

Conversation history and long-term memory solve different problems.

A conversation may contain dozens of messages, but only a few pieces of information may remain useful later. A customer might mention a preference, explain a recurring issue, or provide context that becomes important several days later.

Sending the entire conversation history back to the language model is possible, but it does not automatically create useful long-term memory. It can also become increasingly noisy as conversations grow.

For example, imagine a customer says:

"I prefer concise responses and usually contact support from my phone."

That information may not matter for the current question, but it could be useful during a future support interaction.

I wanted the agent to recover that kind of context without requiring the customer to repeat it.

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

## Implementation

The backend separates API handling, model generation, database persistence, and long-term memory. FastAPI receives the customer request, loads the relevant conversation context, recalls useful information from Hindsight, and sends the resulting prompt to Ollama running Qwen3 8B. The generated response is then stored in SQLite and the conversation turn is retained for future recall.

A small Hindsight integration keeps the memory layer separate from the rest of the application:

```python
await hindsight.retain(
    content=f"Customer: {message_text}\\nAssistant: {response}",
    conversation_id=str(conversation.id),
    tags=["customer-support"],
    context="customer support conversation",
)
```

This separation is important because ordinary conversation history and long-term memory serve different purposes. SQLite remains responsible for application records, while Hindsight provides a way to retrieve useful customer context later.

## Local AI With Ollama and Qwen3 8B

Ollama provides the local model runtime and Qwen3 8B handles response generation. Keeping inference local made development simpler and avoided adding another hosted inference service. The model integration is isolated in the backend service layer, so the rest of the application does not need to know how the model is called.

## Attachments and Error Handling

Customer support is not always text-only, so I added attachment support to the backend. Attachments can be associated with conversations and messages, giving the application a more realistic support workflow.

I also improved frontend error handling. Instead of allowing failed API requests to silently break the experience, the interface can surface errors to the user. This made both debugging and normal interaction more predictable.

## Testing

The backend was tested with Pytest. The final test run completed with four passing tests:

```text
4 passed in 0.65s
```

The React frontend was also built successfully with Vite, confirming that the production frontend bundle could be generated without build errors.

## Challenges and Lessons

One of the main challenges was understanding that memory should not simply mean storing more conversation history. A useful memory system needs a way to retain information and later retrieve information that is relevant to the current interaction.

Another challenge was keeping the architecture understandable. SQLite handles structured application data, Ollama handles model inference, and Hindsight handles long-term memory. Separating these responsibilities makes the system easier to debug and gives each component a clear purpose.

The project also highlighted the importance of the surrounding engineering work. Async API tests, frontend error handling, attachment processing, database models, and environment configuration are all necessary parts of a reliable AI application.

## Visuals

Three visuals would make the article easier to follow: a screenshot of the customer support interface, a screenshot showing a later conversation using remembered context, and the architecture diagram included earlier in this article.

## Resources

Hindsight GitHub: https://github.com/vectorize-io/hindsight

Hindsight documentation: https://hindsight.vectorize.io/

Vectorize agent memory: https://vectorize.io/

## Takeaways

This project showed me that a useful customer support agent needs more than a capable language model. The surrounding application determines whether the agent can persist information, retrieve relevant context, handle attachments, communicate errors clearly, and maintain reliable application state.

The combination of React, FastAPI, SQLite, Ollama, Qwen3 8B, and Hindsight provides a practical foundation for experimenting with persistent customer context. The key architectural lesson is to treat long-term memory as a separate concern rather than simply making the chat history longer.

Future improvements could include better memory retrieval, authentication, richer ticket workflows, and production deployment. For me, the most valuable part of the project was seeing how these components work together to turn a basic chatbot into a more stateful customer support system.
