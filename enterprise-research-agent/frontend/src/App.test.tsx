import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "./App";

describe("App", () => {
  it("renders navigation and the collections page by default", () => {
    render(
      <MemoryRouter initialEntries={["/collections"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("Enterprise Research Agent")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Collections" })).toBeInTheDocument();
  });

  it("renders the sign-in form", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });
});
