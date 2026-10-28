import Icon from "./Icon";

const fallbackPrompts = [
  {
    icon: "user",
    label: "Introduce a customer",
    text: "My name is Sarah. I work at Acme Corp. I use Ubuntu 24.04 on a Dell XPS 15, and my Wi-Fi keeps disconnecting.",
  },
  {
    icon: "wifi",
    label: "Return to an issue",
    text: "The Wi-Fi problem is back. What should I check first?",
  },
  {
    icon: "sparkles",
    label: "Set a preference",
    text: "I prefer concise answers with one clear next step.",
  },
];

export default function Welcome({
  customer,
  scenario,
  health,
  onPrompt,
  onAddCustomer,
  onLoadDemo,
  demoBusy,
}) {
  const prompts = scenario?.first_message
    ? [
        {
          icon: "user",
          label: "Introduce a customer",
          text: scenario.first_message,
        },
        {
          icon: "wifi",
          label: "Return to an issue",
          text: scenario.follow_up || fallbackPrompts[1].text,
        },
        {
          icon: "sparkles",
          label: "Set a preference",
          text: "I prefer concise answers with one clear next step.",
        },
      ]
    : fallbackPrompts;

  if (!customer) {
    return (
      <section className="welcome welcome-empty">
        <div className="welcome-orb" aria-hidden="true">
          <span />
          <Icon name="brain" size={34} strokeWidth={1.5} />
        </div>
        <span className="welcome-kicker">Long-term memory for support</span>
        <h2>Give every customer a memory.</h2>
        <p className="welcome-lede">
          Support AI keeps a separate Hindsight memory bank for each customer.
          Return in a new conversation and the useful context is already there.
        </p>
        <div className="welcome-actions">
          <button type="button" className="button button-primary" onClick={onAddCustomer}>
            <Icon name="plus" size={17} />
            Create a customer
          </button>
          <button
            type="button"
            className="button button-secondary"
            onClick={onLoadDemo}
            disabled={demoBusy}
          >
            <Icon name="sparkles" size={17} />
            {demoBusy ? "Loading demo…" : "Load demo customer"}
          </button>
        </div>
        <div className="feature-strip">
          <div>
            <Icon name="shield" size={17} />
            <span>
              <strong>Isolated banks</strong>
              One customer per memory bank.
            </span>
          </div>
          <div>
            <Icon name="brain" size={17} />
            <span>
              <strong>Transparent recall</strong>
              See exactly what was remembered.
            </span>
          </div>
          <div>
            <Icon name="file" size={17} />
            <span>
              <strong>Useful attachments</strong>
              Text and PDFs reach the model.
            </span>
          </div>
        </div>
      </section>
    );
  }

  const firstName = customer.name.split(/\s+/)[0];
  const memoryOnline = health?.hindsight === "available";

  return (
    <section className="welcome">
      <div className="welcome-heading">
        <span className="welcome-kicker">
          <Icon name="sparkles" size={14} />
          New conversation
        </span>
        <h2>
          Welcome back, <span>{firstName}</span>.
        </h2>
        <p className="welcome-lede">
          Ask a question or pick a starting point. Relevant details from earlier
          conversations are recalled automatically.
        </p>
      </div>

      {!memoryOnline ? (
        <div className="memory-offline-note">
          <Icon name="cloudOff" size={17} />
          <span>
            Hindsight is offline, so this conversation will work without
            long-term recall. Start the memory service to restore it.
          </span>
        </div>
      ) : null}

      <div className="prompt-grid">
        {prompts.map((prompt) => (
          <button
            key={prompt.label}
            type="button"
            className="prompt-card"
            onClick={() => onPrompt(prompt.text)}
          >
            <span className="prompt-icon">
              <Icon name={prompt.icon} size={18} />
            </span>
            <span className="prompt-label">{prompt.label}</span>
            <span className="prompt-text">{prompt.text}</span>
            <span className="prompt-arrow">
              <Icon name="arrowUp" size={14} />
            </span>
          </button>
        ))}
      </div>

      <div className="demo-card">
        <div className="demo-card-icon">
          <Icon name="memory" size={22} />
        </div>
        <div className="demo-card-copy">
          <span className="demo-eyebrow">Two-conversation demo</span>
          <h3>Show memory doing its job</h3>
          <p>
            Send the introduction, wait for <strong>Memory saved</strong>, then
            start a new conversation and ask about the Wi-Fi issue again.
          </p>
        </div>
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={() => onPrompt(prompts[0].text)}
        >
          Use intro
          <Icon name="chevronRight" size={14} />
        </button>
      </div>
    </section>
  );
}
