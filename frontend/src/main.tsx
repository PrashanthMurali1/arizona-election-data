import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import ElectionPage from "./pages/ElectionPage";
import Methodology from "./pages/Methodology";
import "./styles.css";
function Layout() {
  return (
    <>
      <header className="site-header">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            AZ<span>↗</span>
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
          <Route
            path="*"
            element={
              <div className="empty">
                <h1>Page not found</h1>
                <Link to="/">Back to the catalog</Link>
              </div>
            }
          />
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
