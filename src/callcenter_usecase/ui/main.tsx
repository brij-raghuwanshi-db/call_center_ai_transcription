import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@/styles/globals.css";
import CallCenterUseCaseApp from "@/components/callcenter-usecase-app";

const rootElement = document.getElementById("root")!;

if (!rootElement.innerHTML) {
  const root = createRoot(rootElement);
  root.render(
    <StrictMode>
      <CallCenterUseCaseApp />
    </StrictMode>,
  );
}
