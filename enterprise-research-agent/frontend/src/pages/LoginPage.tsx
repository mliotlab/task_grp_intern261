import { FormEvent, useState } from "react";

import { api, auth } from "../api/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api<{ access_token: string }>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      auth.token = res.access_token;
      // TODO(FR-01): redirect to /collections and add a register form.
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <section className="card narrow">
      <h1>Sign in</h1>
      <form onSubmit={onSubmit}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit">Sign in</button>
      </form>
    </section>
  );
}
