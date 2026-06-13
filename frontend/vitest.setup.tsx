import "@testing-library/jest-dom/vitest";
import * as React from "react";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

// next/image and next/link need no Next runtime in unit tests — render the
// underlying elements so component tests stay focused on behaviour.
vi.mock("next/image", () => ({
  default: ({
    src,
    alt,
    width,
    height,
  }: {
    src: string;
    alt: string;
    width?: number;
    height?: number;
  }) =>
    React.createElement("img", {
      src: typeof src === "string" ? src : "",
      alt,
      width,
      height,
    }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) =>
    React.createElement(
      "a",
      { href: typeof href === "string" ? href : "#", ...rest },
      children,
    ),
}));
