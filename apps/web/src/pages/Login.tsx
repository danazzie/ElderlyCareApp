import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Brand } from "../components/Brand";
import { HeroArt } from "../components/Illustration";

const DEMO = [
  { email: "danagul@ahtama.demo", label: "Danagul / owner" },
  { email: "aisha@ahtama.demo", label: "Aisha / member" },
  { email: "fatima@ahtama.demo", label: "Fatima / caregiver" },
];

export default function Login() {
  const { login, register, join } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState<"intro" | "login" | "register" | "join">("intro");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const go = async (fn: () => Promise<void>) => {
    setBusy(true); setError("");
    try { await fn(); nav("/"); } catch (e: any) { setError(e.message); }
    setBusy(false);
  };

  return (
    <div className="hero">
      <div className="hero-brand"><Brand size={36} light /></div>
      <div className="art"><HeroArt /></div>
      <div className="panel">
        <h1>Care and peace of mind for your parents</h1>
        <p>One shared care record for the whole family  -  doctors' letters, daily updates and
          medications, every fact linked to its source.</p>

        {mode === "intro" && (
          <div className="stack">
            <button className="btn dark" onClick={() => setMode("login")}>Get started</button>
            <button className="btn" style={{ color: "#fff" }} onClick={() => setMode("join")}>
              I have an invitation code
            </button>
          </div>
        )}

        {mode !== "intro" && (
          <div className="login-panel stack">
            {mode === "join" && (
              <>
                <h3>Join a care circle</h3>
                <input className="input" placeholder="Invitation code (try AHMED123)" value={code}
                  onChange={(e) => setCode(e.target.value)} />
                <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="member">I'm family (member)</option>
                  <option value="caregiver">I'm a caregiver</option>
                </select>
                <p className="tiny">Sign in first, then the code is applied.</p>
              </>
            )}
            {mode === "register" ? (
              <>
                <h3>Create account</h3>
                <input className="input" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
              </>
            ) : mode === "login" ? <h3>Sign in</h3> : null}
            <input className="input" type="email" placeholder="Email" value={email}
              onChange={(e) => setEmail(e.target.value)} />
            <input className="input" type="password" placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)} />
            {error && <div className="alert-banner">{error}</div>}
            <button className="btn primary" disabled={busy} onClick={() =>
              go(async () => {
                if (mode === "register") await register(email, name, password);
                else await login(email, password);
                if (mode === "join" && code) await join(code.trim(), role);
              })}>
              {busy ? <span className="spin" /> : mode === "register" ? "Create account" : "Continue"}
            </button>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <button className="tiny" style={{ color: "var(--green-dark)", fontWeight: 700 }}
                onClick={() => setMode(mode === "register" ? "login" : "register")}>
                {mode === "register" ? "Have an account? Sign in" : "New here? Create account"}
              </button>
            </div>
            <div className="tiny">Demo accounts (password <b>demo1234</b>):</div>
            <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
              {DEMO.map((d) => (
                <button key={d.email} className="badge green"
                  onClick={() => go(() => login(d.email, "demo1234"))}>{d.label}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
