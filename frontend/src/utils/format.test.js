import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  formatFileSize,
  formatRelativeTime,
  initials,
  isImage,
  kindLabel,
  memoryGroup,
  truncate,
} from "./format";

describe("format helpers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-28T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("formats recent and older relative times", () => {
    expect(formatRelativeTime("2026-10-28T11:59:40Z")).toBe("just now");
    expect(formatRelativeTime("2026-10-28T11:55:00Z")).toBe("5 minutes ago");
    expect(formatRelativeTime("2026-10-27T12:00:00Z")).toBe("yesterday");
    expect(formatRelativeTime(null)).toBe("");
  });

  it("formats file sizes", () => {
    expect(formatFileSize(0)).toBe("0 B");
    expect(formatFileSize(900)).toBe("900 B");
    expect(formatFileSize(2048)).toBe("2 KB");
    expect(formatFileSize(10 * 1024 * 1024)).toBe("10 MB");
  });

  it("derives initials safely", () => {
    expect(initials("Sarah Chen")).toBe("SC");
    expect(initials("Support")).toBe("SU");
    expect(initials("")).toBe("?");
  });

  it("truncates long text without breaking short text", () => {
    expect(truncate("short", 20)).toBe("short");
    expect(truncate("a much longer sentence", 10)).toBe("a much lo…");
    expect(truncate("  many   spaces  ", 30)).toBe("many spaces");
  });

  it("classifies memory kinds and images", () => {
    expect(kindLabel("operating_system")).toBe("System");
    expect(kindLabel("unknown")).toBe("Memory");
    expect(memoryGroup("issue")).toBe("issues");
    expect(memoryGroup("preference")).toBe("preferences");
    expect(memoryGroup("interaction")).toBe("conversations");
    expect(memoryGroup("name")).toBe("profile");
    expect(isImage("image/png")).toBe(true);
    expect(isImage("application/pdf")).toBe(false);
  });
});
