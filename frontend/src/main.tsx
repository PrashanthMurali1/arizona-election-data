import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import { NotFound } from "./components";
import ElectionPage from "./pages/ElectionPage";
import Methodology from "./pages/Methodology";
import "./styles.css";
function Layout() {
  return (
    <>
      <header className="site-header">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" focusable="false">
              {/* Census county boundaries merged into a state outline; Mercator projection. */}
              <path d="M5.49 37.12 L29.49 46.00 L42.48 46.00 L42.51 2.04 L10.41 2.03 L10.45 8.48 L9.95 9.14 L9.84 9.72 L9.18 9.89 L8.72 9.54 L8.76 9.36 L8.36 8.88 L8.11 8.85 L7.88 9.02 L7.49 9.00 L7.43 8.82 L6.69 8.88 L5.89 9.34 L6.10 9.78 L5.98 10.21 L6.49 11.03 L6.20 11.21 L6.16 11.55 L6.31 12.78 L6.54 13.09 L6.38 13.97 L6.85 15.08 L7.08 16.45 L7.02 16.88 L6.58 17.09 L6.86 17.35 L6.65 17.67 L6.66 18.87 L7.19 19.71 L7.71 20.15 L7.93 21.05 L8.29 21.56 L8.25 22.12 L8.58 22.18 L9.60 22.96 L9.89 23.64 L9.67 23.67 L9.26 24.22 L8.06 24.84 L7.92 25.50 L7.30 26.18 L7.47 26.42 L7.34 27.10 L7.56 27.93 L7.32 28.18 L7.37 29.13 L6.60 30.17 L6.08 30.26 L6.25 30.66 L6.04 31.05 L6.42 31.38 L6.20 32.69 L6.48 33.11 L6.59 32.99 L6.76 33.16 L7.45 33.18 L7.73 33.62 L7.72 34.55 L7.34 34.92 L7.27 35.27 L6.76 35.44 L6.23 35.31 L5.83 36.09 L5.55 36.25 L5.51 36.71 L5.65 36.74 Z" />
              <text className="brand-mark-label" x="22" y="29">
                AZ
              </text>
              <text className="brand-mark-arrow" x="33" y="15">
                ↗
              </text>
            </svg>
          </span>
          <span>
            Arizona<span className="brand-sub">Election Explorer</span>
          </span>
        </Link>
        <nav aria-label="Main navigation">
          <NavLink to="/" end>
            Election catalog
          </NavLink>
          <NavLink to="/methodology">About the data</NavLink>
        </nav>
        <span className="local-label">
          <span />
          PUBLIC RECORDS, CLEARER
        </span>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/elections/:id" element={<ElectionPage />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer>
        <Link to="/">Arizona Election Explorer</Link>
        <span>An independent project. Official records. Open exploration.</span>
        <Link to="/methodology">Sources & methodology ↗</Link>
      </footer>
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Layout />
    </BrowserRouter>
  </React.StrictMode>,
);
