import { useEffect, useRef, useState } from "react";
import { api, ChatMsg } from "../api";
import { useAuth } from "../auth";

const SUGGESTIONS = [
  "What's due tonight?",
  "What did the doctor say about the follow-up?",
  "What was the blood pressure in the last update?",
  "Which painkillers should he avoid?",
];

export default function Ask() {
  const { circle } = useAuth();
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (circle) api.messages(circle.id).then(setMsgs).catch(() => {}); }, [circle?.id]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs.length, busy]);

  const send = async (q: string) => {
    if (!circle || !q.trim() || busy) return;
    setBusy(true);
    setInput("");
    setMsgs((m) => [...m, { id: "tmp", role: "user", content: q, citations: [], route: "", created_at: "" }]);
    try {
      const r = await api.ask(circle.id, q);
      setMsgs((m) => [...m.filter((x) => x.id !== "tmp"),
        { id: "u" + Date.now(), role: "user", content: q, citations: [], route: "", created_at: "" },
        { id: r.id, role: "assistant", content: r.answer, citations: r.citations, route: r.route, created_at: "" }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { id: "err", role: "assistant", content: e.message, citations: [], route: "", created_at: "" }]);
    }
    setBusy(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "calc(100dvh - 140px)" }}>
      <h2 style={{ marginBottom: 4 }}>Ask Ahtama</h2>
      <p className="muted" style={{ marginTop: 2 }}>
        Answers come only from this circle's approved records, with the source cited.
        Medical decisions are always redirected to the doctor.
      </p>

      <div className="chat" style={{ flex: 1 }}>
        {msgs.length === 0 && (
          <div className="stack" style={{ marginTop: 12 }}>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="card" style={{ textAlign: "left", color: "var(--green-dark)", fontWeight: 600 }}
                onClick={() => send(s)}>✳ {s}</button>
            ))}
          </div>
        )}
        {msgs.map((m) => (
          <div key={m.id} className={`bubble ${m.role}${m.route === "clinical" ? " clinical" : ""}`}>
            {m.route === "clinical" && <div className="tiny" style={{ marginBottom: 4 }}>🩺 A question for the doctor</div>}
            {m.content}
            {m.citations.length > 0 && (
              <div>
                {m.citations.map((c, i) => (
                  <span key={i} className="cite-chip" title={c.quote}>📄 {c.doc_name} · p.{c.page}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant"><span className="spin dark" /></div>}
        <div ref={endRef} />
      </div>

      <div className="row" style={{ position: "sticky", bottom: 84, background: "var(--bg)", paddingTop: 8 }}>
        <input className="input" placeholder="Ask about the care record…" value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)} />
        <button className="btn primary" style={{ borderRadius: "50%", width: 46, height: 46, padding: 0, flexShrink: 0 }}
          onClick={() => send(input)} disabled={busy}>➤</button>
      </div>
    </div>
  );
}
