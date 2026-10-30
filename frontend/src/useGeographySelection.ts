import { useCallback, useEffect, useRef } from "react";

// Preserve the initiating control so closing an inline detail can restore focus.
export default function useGeographySelection(selected: string | null) {
  const detailRef = useRef<HTMLElement>(null);
  const origin = useRef<HTMLElement | SVGElement | null>(null);
  const frame = useRef<number | null>(null);
  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    [],
  );
  useEffect(() => {
    if (!selected && origin.current?.isConnected) origin.current.focus();
  }, [selected]);
  const focusSelection = useCallback(() => {
    const active = document.activeElement;
    if (active instanceof HTMLElement || active instanceof SVGElement)
      origin.current = active;
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      detailRef.current?.focus({ preventScroll: true });
      if (matchMedia("(max-width: 900px)").matches)
        detailRef.current?.scrollIntoView({
          block: "start",
          behavior: "instant",
        });
    });
  }, []);
  const restoreFocus = useCallback(
    (fallback?: HTMLElement | SVGElement | null) => {
      requestAnimationFrame(() => {
        const target = origin.current?.isConnected ? origin.current : fallback;
        if (target?.isConnected) target.focus();
      });
    },
    [],
  );
  return { detailRef, focusSelection, restoreFocus };
}
