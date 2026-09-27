import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "";

function CyberPet({ thinking = false }) {
  const [pos, setPos] = useState({ x: window.innerWidth - 80, y: window.innerHeight - 120 });

  useEffect(() => {
    let targetX = window.innerWidth - 80;
    let targetY = window.innerHeight - 120;
    let x = targetX;
    let y = targetY;
    let frame;

    const move = (e) => {
      targetX = e.clientX + 22;
      targetY = e.clientY + 22;
    };

    const animate = () => {
      x += (targetX - x) * 0.09;
      y += (targetY - y) * 0.09;
      setPos({ x, y });
      frame = requestAnimationFrame(animate);
    };

    window.addEventListener("mousemove", move);
    frame = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", move);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div
      className={`cyber-pet ${thinking ? "thinking" : ""}`}
      style={{ left: pos.x, top: pos.y }}
      aria-hidden="true"
    >
      <div className="pet-glow" />
      <div className="pet-antenna"><span /></div>
      <div className="pet-head">
        <span className="pet-ear left" />
        <span className="pet-ear right" />
        <span className="pet-eye left" />
        <span className="pet-eye right" />
        <span className="pet-mouth" />
      </div>
      <div className="pet-body"><span className="pet-core" /></div>
      <div className="pet-shadow" />
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your customer support assistant. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendMessage(event) {
    event.preventDefault();

    const message = input.trim();

    if (!message || loading) return;

    setMessages((current) => [
      ...current,
      { role: "user", content: message },
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error("Unable to contact the support agent.");
      }

      const data = await response.json();

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.response,
        },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't connect to the support service. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <CyberPet thinking={loading} />

      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <div>
            <h1>Support AI</h1>
            <span>Customer Support Agent</span>
          </div>
        </div>

        <div className="system-status">
          <span className="status-light" />
          SYSTEM ONLINE
        </div>
      </header>

      <main className="chat-container">
        <section className="welcome">
          <div className="eyebrow">
            <span />
            AI ASSISTANT
          </div>

          <h2>How can we help?</h2>
          <p>
            Ask a question and our AI support agent will help you find the
            right answer.
          </p>
        </section>

        <section className="messages">
          {messages.map((message, index) => (
            <div
              className={`message-row ${message.role}`}
              key={`${message.role}-${index}`}
            >
              <div className="message-avatar">
                {message.role === "assistant" ? "✦" : "YOU"}
              </div>

              <div className="message-content">
                <div className="message-meta">
                  {message.role === "assistant" ? "SUPPORT AI" : "YOU"}
                </div>
                <div className="message-bubble">{message.content}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="message-avatar">✦</div>
              <div className="message-content">
                <div className="message-meta">SUPPORT AI</div>
                <div className="message-bubble thinking-text">
                  <span />
                  <span />
                  <span />
                  Thinking
                </div>
              </div>
            </div>
          )}
        </section>

        <form className="composer" onSubmit={sendMessage}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Message Support AI..."
            disabled={loading}
          />

          <button
            type="submit"
            disabled={!input.trim() || loading}
            aria-label="Send message"
          >
            <span>→</span>
          </button>
        </form>

        <div className="composer-hint">
          <span>ENTER</span> to send · AI responses may contain mistakes
        </div>
      </main>

      <footer className="footer">
        <span>SUPPORT AI</span>
        <span>•</span>
        <span>SECURE SESSION</span>
        <span>•</span>
        <span>v0.2.0</span>
      </footer>
    </div>
  );
}

export default App;
