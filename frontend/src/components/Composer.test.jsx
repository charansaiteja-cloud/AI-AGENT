import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Composer from "./Composer";

function renderComposer(overrides = {}) {
  const props = {
    value: "",
    onChange: vi.fn(),
    onSend: vi.fn(),
    onAttach: vi.fn(),
    attachments: [],
    onRemoveAttachment: vi.fn(),
    disabled: false,
    sending: false,
    uploading: false,
    placeholder: "Message Sarah…",
    focusToken: 0,
    ...overrides,
  };

  render(<Composer {...props} />);
  return props;
}

describe("Composer", () => {
  it("sends on Enter but not on Shift+Enter", async () => {
    const user = userEvent.setup();
    const props = renderComposer({ value: "Hello" });
    const input = screen.getByRole("textbox", { name: "Message" });

    await user.click(input);
    await user.keyboard("{Enter}");
    expect(props.onSend).toHaveBeenCalledTimes(1);

    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(props.onSend).toHaveBeenCalledTimes(1);
  });

  it("does not send blank messages", async () => {
    const user = userEvent.setup();
    const props = renderComposer({ value: "   " });
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(props.onSend).not.toHaveBeenCalled();
  });

  it("renders draft attachments and removes them", async () => {
    const user = userEvent.setup();
    const onRemoveAttachment = vi.fn();
    renderComposer({
      value: "See attached",
      onRemoveAttachment,
      attachments: [
        {
          id: 4,
          original_filename: "wifi-log.txt",
          content_type: "text/plain",
          file_size: 2048,
        },
      ],
    });

    expect(screen.getByText("wifi-log.txt")).toBeInTheDocument();
    expect(screen.getByText("2 KB")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove wifi-log.txt" }));
    expect(onRemoveAttachment).toHaveBeenCalledWith(
      expect.objectContaining({ id: 4 }),
    );
  });

  it("disables the composer when no customer is selected", () => {
    renderComposer({ disabled: true, placeholder: "Add a customer" });
    expect(screen.getByRole("textbox", { name: "Message" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
});
