import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const mocks = vi.hoisted(() => ({
  health: vi.fn(),
  listCustomers: vi.fn(),
  listConversations: vi.fn(),
  listMemories: vi.fn(),
  listMessages: vi.fn(),
  demoScenario: vi.fn(),
}));

vi.mock("./api", () => ({
  api: {
    health: mocks.health,
    models: vi.fn(),
    customers: {
      list: mocks.listCustomers,
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      conversations: mocks.listConversations,
      memories: mocks.listMemories,
      clearMemories: vi.fn(),
    },
    conversations: {
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      messages: mocks.listMessages,
      attachments: vi.fn(),
      upload: vi.fn(),
      deleteAttachment: vi.fn(),
    },
    chat: vi.fn(),
    demo: {
      seed: vi.fn(),
      scenario: mocks.demoScenario,
    },
  },
  getErrorMessage: (error) => error?.message || "Something went wrong.",
}));

const customer = {
  id: 7,
  name: "Sarah Chen",
  email: "sarah@acme.example",
  created_at: "2026-10-28T10:00:00Z",
  conversation_count: 1,
  last_activity_at: "2026-10-28T10:05:00Z",
};

const conversation = {
  id: 11,
  customer_id: 7,
  title: "Wi-Fi keeps disconnecting",
  status: "active",
  created_at: "2026-10-28T10:00:00Z",
  updated_at: "2026-10-28T10:05:00Z",
  message_count: 0,
  last_message: null,
  last_message_at: null,
};

function primeApi() {
  mocks.health.mockResolvedValue({
    status: "ok",
    service: "Support AI",
    version: "1.0.0",
    database: "connected",
    ollama: "available",
    hindsight: "available",
    model: "qwen3:8b",
  });
  mocks.listCustomers.mockResolvedValue([customer]);
  mocks.listConversations.mockResolvedValue([conversation]);
  mocks.listMemories.mockResolvedValue({
    customer_id: 7,
    available: true,
    count: 1,
    memories: [
      {
        id: "m1",
        text: "Customer name is Sarah.",
        kind: "name",
        source: "profile_extraction",
        created_at: "2026-10-28T10:00:00Z",
        score: 0.8,
      },
    ],
  });
  mocks.listMessages.mockResolvedValue({ conversation_id: 11, messages: [] });
  mocks.demoScenario.mockResolvedValue({
    first_message: "My name is Sarah.",
    follow_up: "The Wi-Fi problem is back.",
  });
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("App", () => {
  it("loads the selected customer, conversations, and memory", async () => {
    primeApi();
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /welcome back, sarah/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Sarah Chen").length).toBeGreaterThan(0);
    expect(
      (await screen.findAllByText("Wi-Fi keeps disconnecting")).length,
    ).toBeGreaterThan(0);
    await waitFor(() => {
      expect(mocks.listMemories).toHaveBeenCalledWith(7);
    });
  });

  it("shows onboarding when there are no customers", async () => {
    primeApi();
    mocks.listCustomers.mockResolvedValue([]);
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /give every customer a memory/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create a customer/i }),
    ).toBeInTheDocument();
  });
});
