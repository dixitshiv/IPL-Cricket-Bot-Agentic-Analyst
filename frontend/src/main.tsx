import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { FiltersProvider } from "./state/FiltersContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <FiltersProvider>
      <App />
    </FiltersProvider>
  </React.StrictMode>
);
