cd ~/customer-support-agent

cat > article.md <<'EOF'
# How I Gave a Customer Support Agent Memory With Hindsight

A customer support agent can answer the current question correctly and still feel like it has forgotten the customer. I wanted mine to remember useful customer preferences across conversations, not just replay the previous chat window.

I built the system around FastAPI, Ollama with Qwen3 8B, SQLite for conversation persistence, and Hindsight for long-term customer memory.

## The problem with ordinary conversation history

Conversation history is useful, but it is not the same thing as customer memory.

A conversation can contain dozens of messages, while a customer preference may be expressed once and become relevant much later. Sending the entire history to the language model every time is also not a good substitute for deciding which facts actually matter.

For customer support, the distinction matters.

If Sarah says during one conversation that she prefers concise answers, I don't want the next conversation to start from zero. The agent should be able to retrieve that preference when Sarah returns.

That became the core design problem.

## Where Hindsight fits

The application has a small Hindsight client in `backend/app/services/hindsight.py`.

The client exposes three important operations: health checking, retaining a conversation turn, and recalling relevant memory.

When a conversation is stored, the application sends the customer message and assistant response to Hindsight:

```python
await hindsight.retain(
    content=(
        f"Customer: {message_text}\n"
        f"Assistant: {response}"
    ),
    conversation_id=str(conversation.id),
    tags=["customer-support"],
    context="customer support conversation",
)
