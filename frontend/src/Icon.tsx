import type { SVGProps } from "react";

const shapes = {
  arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
  check: <path d="m5 12 4 4L19 6" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6m0-10v1" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 6v6l4 2" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
    </>
  ),
  moon: <path d="M20.5 13.2A8.6 8.6 0 0 1 10.8 3a8.6 8.6 0 1 0 9.7 10.2Z" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  location: (
    <>
      <path d="M12 21s7-6 7-12A7 7 0 1 0 5 9c0 6 7 12 7 12Z" />
      <circle cx="12" cy="9" r="2" />
    </>
  ),
  sort: <path d="M8 18V5m-3 3 3-3 3 3m5-2v13m-3-3 3 3 3-3" />,
  up: <path d="M12 19V5m-5 5 5-5 5 5" />,
  down: <path d="M12 5v14m-5-5 5 5 5-5" />,
};

export default function Icon({
  name = "arrow",
  ...props
}: SVGProps<SVGSVGElement> & { name?: keyof typeof shapes }) {
  return (
    <svg
      className="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {shapes[name]}
    </svg>
  );
}
