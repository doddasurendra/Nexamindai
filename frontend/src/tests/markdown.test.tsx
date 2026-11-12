import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown } from "../components/Markdown";

describe("Markdown", () => {
  it("renders headings, lists and code blocks", () => {
    render(<Markdown>{`# Report\n\n- one\n- two\n\n\`\`\`python\nprint("hi")\n\`\`\``}</Markdown>);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Report");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    const code = screen.getByRole("code");
    expect(code.textContent).toContain('print("hi")');
  });

  it("renders links with markdown syntax", () => {
    render(<Markdown>{"[source](https://example.com)"}</Markdown>);
    const link = screen.getByRole("link", { name: "source" });
    expect(link).toHaveAttribute("href", "https://example.com");
  });
});
