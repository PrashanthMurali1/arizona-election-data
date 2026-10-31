// Cursor light for glass panels: publishes the pointer position inside each panel
// as --mx/--my and a --lit intensity that the stylesheet turns into a soft
// spotlight and a lit rim. Presentation only; it never touches state or data.
export const GLASS_SELECTOR = [
  ".result-summary",
  ".table-region",
  ".selection-panel",
  ".snapshot-notice",
  ".map-region",
  ".map-panel",
  ".statewide-participation",
  ".archive-row",
  ".notice",
].join(",");

// How far outside a panel the pointer still lights its rim, in px.
const REACH = 140;

export function lightFor(
  rect: { left: number; top: number; width: number; height: number },
  x: number,
  y: number,
) {
  const dx = Math.max(rect.left - x, 0, x - (rect.left + rect.width));
  const dy = Math.max(rect.top - y, 0, y - (rect.top + rect.height));
  const distance = Math.hypot(dx, dy);
  return {
    mx: x - rect.left,
    my: y - rect.top,
    lit: distance >= REACH ? 0 : 1 - distance / REACH,
  };
}

export function startGlassLight(root: Document = document) {
  const win = root.defaultView;
  if (
    !win ||
    !win.matchMedia("(hover: hover) and (pointer: fine)").matches ||
    win.matchMedia("(prefers-reduced-motion: reduce)").matches
  ) {
    return () => {};
  }
  let frame = 0;
  let x = 0;
  let y = 0;
  const paint = () => {
    frame = 0;
    root.querySelectorAll<HTMLElement>(GLASS_SELECTOR).forEach((el) => {
      const { mx, my, lit } = lightFor(el.getBoundingClientRect(), x, y);
      el.style.setProperty("--mx", `${mx.toFixed(1)}px`);
      el.style.setProperty("--my", `${my.toFixed(1)}px`);
      el.style.setProperty("--lit", lit.toFixed(2));
    });
  };
  const move = (event: PointerEvent) => {
    x = event.clientX;
    y = event.clientY;
    if (!frame) frame = win.requestAnimationFrame(paint);
  };
  const leave = () => {
    x = -10000;
    y = -10000;
    if (!frame) frame = win.requestAnimationFrame(paint);
  };
  root.addEventListener("pointermove", move, { passive: true });
  root.documentElement.addEventListener("pointerleave", leave);
  return () => {
    root.removeEventListener("pointermove", move);
    root.documentElement.removeEventListener("pointerleave", leave);
    if (frame) win.cancelAnimationFrame(frame);
  };
}
