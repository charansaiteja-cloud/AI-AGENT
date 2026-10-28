import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import MemoryPanel from "./MemoryPanel";

const customer = { id: 1, name: "Sarah Chen", email: "sarah@acme.example" };

const memories = [
  {
    id: "m1",
    text: "Customer name is Sarah.",
    kind: "name",
    source: "profile_extraction",
    created_at: "2026-10-28T10:00:00Z",
    score: 0.9,
  },
  {
    id: "m2",
    text: "Customer has a recurring issue: Wi-Fi keeps disconnecting.",
    kind: "issue",
    source: "profile_extraction",
    created_at: "2026-10-28T10:01:00Z",
  },
  {
    id: "m3",
    text: "Customer prefers concise answers.",
    kind: "preference",
    source: "profile_extraction",
    created_at: "2026-10-28T10:02:00Z",
  },
];

function renderPanel(overrides = {}) {
  const props = {
    open: true,
    onClose: vi.fn(),
    customer,
    memories,
    loading: false,
    available: true,
    error: null,
    onRefresh: vi.fn(),
    onClear: vi.fn(),
    clearing: false,
    ...overrides,
  };
  render(<MemoryPanel {...props} />);
  return props;
}

describe("MemoryPanel", () => {
  it("shows memory cards and filters by category", async () => {
    const user = userEvent.setup();
    renderPanel();

    expect(screen.getByText("memories").parentElement).toHaveTextContent(
      /3\s*memories/,
    );
    expect(screen.getByText("Customer name is Sarah.")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Issues" }));
    expect(
      screen.getByText("Customer has a recurring issue: Wi-Fi keeps disconnecting."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Customer name is Sarah.")).not.toBeInTheDocument();
  });

  it("searches memory text", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.type(screen.getByRole("searchbox", { name: "Filter memories" }), "concise");
    expect(screen.getByText("Customer prefers concise answers.")).toBeInTheDocument();
    expect(screen.queryByText("Customer name is Sarah.")).not.toBeInTheDocument();
  });

  it("shows an offline state with retry", async () => {
    const user = userEvent.setup();
    const props = renderPanel({
      available: false,
      memories: [],
      error: "Hindsight is unavailable.",
    });

    expect(screen.getByText("Memory is offline")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(props.onRefresh).toHaveBeenCalled();
  });

  it("shows an empty state for a new customer", () => {
    renderPanel({ memories: [] });
    expect(screen.getByText("Nothing remembered yet")).toBeInTheDocument();
  });
});
