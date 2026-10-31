import { describe, expect, it } from "vitest";
import { lightFor } from "./glassLight";

const rect = { left: 100, top: 200, width: 400, height: 300 };

describe("lightFor", () => {
  it("reports the pointer offset and full light inside the panel", () => {
    expect(lightFor(rect, 150, 260)).toEqual({ mx: 50, my: 60, lit: 1 });
  });

  it("fades the light out with distance from the panel edge", () => {
    const near = lightFor(rect, 70, 300);
    expect(near.lit).toBeGreaterThan(0);
    expect(near.lit).toBeLessThan(1);
    expect(lightFor(rect, -400, 300).lit).toBe(0);
  });

  it("is dark when the pointer has left the window", () => {
    expect(lightFor(rect, -10000, -10000).lit).toBe(0);
  });
});
