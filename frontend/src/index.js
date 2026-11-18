import React from "react";
import { createRoot } from "react-dom/client";
import "@/index.css";
import "@/styles/darkmode.css";
import App from "@/App";
import { register as registerSW } from "@/serviceWorkerRegistration";

const rootElement = document.getElementById("root");
// O servidor coloca no #root um bloco de HTML inicial (H1 + links, ver
// backend/services/seo_html.py). createRoot limpa esse bloco e monta o app;
// hydrateRoot daria erro de hidratação, pois o bloco não é a árvore do React.
createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

registerSW();
