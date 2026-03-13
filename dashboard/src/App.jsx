import { useState, useEffect } from "react";
import Dashboard from "./components/Dashboard.jsx";
import LoginPage from "./components/LoginPage.jsx";
import { api, setAuthRequiredCallback } from "./lib/api";

export default function App() {
  // null = checking, true = authed, false = need login
  const [authed, setAuthed] = useState(null);

  useEffect(() => {
    // Register global 401 handler
    setAuthRequiredCallback(() => setAuthed(false));

    // Check if already authenticated
    api.authCheck()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
  }, []);

  if (authed === null) {
    return null; // brief loading state
  }

  if (!authed) {
    return (
      <div className="min-h-full bg-bg text-text">
        <LoginPage onSuccess={() => setAuthed(true)} />
      </div>
    );
  }

  return (
    <div className="min-h-full bg-bg text-text">
      <Dashboard />
    </div>
  );
}
