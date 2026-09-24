import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { boot } from "./lib/boot";
import { FrappeError } from "./lib/frappe";
import { applyBranding } from "./lib/theme";
import "./index.css";

// Paint the school's colours before React renders, so there is no flash of default colours.
if (boot.branding) applyBranding(boot.branding);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Permission errors won't fix themselves on retry.
      retry: (count, error) => !(error instanceof FrappeError && [401, 403, 404, 417].includes(error.status)) && count < 2,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
