import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button, ErrorNotice, PageHeader } from "../components/ui";
import { ApiError } from "../lib/api";

describe("design system", () => {
  it("renders a primary button", () => {
    render(<Button>Send</Button>);
    expect(screen.getByRole("button", { name: "Send" })).toHaveClass("nexa-btn-primary");
  });

  it("shows the required environment variable for missing integrations", () => {
    render(<ErrorNotice error={new ApiError("Tavily is not configured", 503, { code: "integration_not_configured", env_var: "TAVILY_API_KEY" })} />);
    expect(screen.getByRole("alert")).toHaveTextContent("TAVILY_API_KEY");
    expect(screen.getByRole("alert")).toHaveTextContent("Tavily is not configured");
  });

  it("renders page headers with subtitle", () => {
    render(<PageHeader title="My Media" subtitle="Gallery" />);
    expect(screen.getByRole("heading", { level: 1, name: "My Media" })).toBeInTheDocument();
    expect(screen.getByText("Gallery")).toBeInTheDocument();
  });
});
