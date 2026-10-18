import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormErrors } from "@/components/form-errors";
import { Pagination } from "@/components/pagination";
import { ActionBadge, StatusBadge, VerifiedBadge } from "@/components/status-badge";

describe("badges", () => {
  it("names each status in plain words", () => {
    render(<StatusBadge status="AWAITING_APPROVAL" />);
    expect(screen.getByText("Needs review")).toHaveAttribute("title", expect.stringContaining("reviewer"));
  });

  it("shows a dash when there is no action yet", () => {
    render(<ActionBadge action={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("distinguishes verified from unverified drafts", () => {
    const { rerender } = render(<VerifiedBadge verified />);
    expect(screen.getByText("Verified")).toBeInTheDocument();
    rerender(<VerifiedBadge verified={false} />);
    expect(screen.getByText("Unverified")).toBeInTheDocument();
  });
});

describe("FormErrors", () => {
  it("renders nothing without errors", () => {
    const { container } = render(<FormErrors errors={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists several errors", () => {
    render(<FormErrors errors={["first problem", "second problem"]} />);
    expect(screen.getByRole("alert")).toHaveTextContent("first problem");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("Pagination", () => {
  it("links to the neighbouring pages and disables the ends", () => {
    render(<Pagination page={1} pageSize={20} total={45} hrefFor={(page) => `/cases?page=${page}`} />);

    expect(screen.getByText("1–20 of 45")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Next/ })).toHaveAttribute("href", "/cases?page=2");
    expect(screen.queryByRole("link", { name: /Previous/ })).not.toBeInTheDocument();
  });
});
