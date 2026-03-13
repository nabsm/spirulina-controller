import { useState } from "react";
import { api } from "../lib/api";

export default function LoginPage({ onSuccess }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.authLogin(password);
      onSuccess();
    } catch (err) {
      const msg = err.message || "";
      if (msg.includes("429")) {
        setError("Too many attempts. Try again in a few minutes.");
      } else if (msg.includes("401")) {
        setError("Wrong password");
      } else {
        setError("Connection error");
      }
      setPassword("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl2 bg-panel shadow-soft border border-line p-6"
      >
        <h1 className="text-lg font-semibold text-text mb-1">
          Spirulina Controller
        </h1>
        <p className="text-sm text-text2 mb-6">Enter password to continue</p>

        <input
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="w-full rounded-xl2 border border-line bg-surface px-3 py-3 text-sm text-text placeholder-text2 outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 mb-3"
        />

        {error && (
          <p className="text-sm text-red-400 mb-3">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading || !password}
          className="w-full rounded-xl2 border border-primary bg-primary px-3 py-3 text-sm font-semibold text-white transition-all hover:bg-primaryHover hover:shadow-soft disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Checking..." : "Log in"}
        </button>
      </form>
    </div>
  );
}
