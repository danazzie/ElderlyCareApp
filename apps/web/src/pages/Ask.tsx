import { useEffect, useRef, useState } from "react";
import { api, ChatMsg } from "../api";
import { useAuth } from "../auth";
import { Icon, IconTile } from "../components/Icon";

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

  const clearChat = async () => {
    if (!circle || !msgs.length) return;
    if (!window.confirm("Clear this circle's Ask history? This cannot be undone.")) return;
    try {
      await api.clearMessages(circle.id);
      setMsgs([]);
    } catch (e: any) {
      setMsgs((m) => [...m, { id: "err", role: "assistant", content: e.message, citations: [], route: "", created_at: "" }]);
    }
  };

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
      <div className="page-head" style={{ marginBottom: 4 }}>
        <h2>Ask Ihtama</h2>
        {msgs.length > 0 && (
          <button className="btn small ghost" onClick={clearChat} disabled={busy}>
            <Icon name="trash" size={15} /> Clear chat
          </button>
        )}
      </div>
      <p className="muted" style={{ marginTop: 2 }}>
        Answers come only from this circle's approved records, with the source cited.
        Medical decisions are always redirected to the doctor.
      </p>

      <div className="chat" style={{ flex: 1 }}>
        {msgs.length === 0 && (
          <div className="stack" style={{ marginTop: 12 }}>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="card suggest" onClick={() => send(s)}>
                <IconTile name="sparkles" tone="green" size={32} iconSize={16} />
                {s}
              </button>
            ))}
          </div>
        )}
        {msgs.map((m) => (
          <div key={m.id} className={`bubble ${m.role}${m.route === "clinical" ? " clinical" : ""}`}>
            {m.route === "clinical" && (
              <div className="tiny row" style={{ marginBottom: 4 }}>
                <Icon name="stethoscope" size={13} /> A question for the doctor
              </div>
            )}
            {m.content}
            {m.citations.length > 0 && (
              <div>
                {m.citations.map((c, i) => (
                  <span key={i} className="cite-chip" title={c.quote}>
                    <Icon name="file" size={12} /> {c.doc_name} · p.{c.page}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant"><span className="spin dark" /></div>}
        <div ref={endRef} />
      </div>

      <div className="row composer" style={{ position: "sticky", bottom: 84, background: "var(--bg)", paddingTop: 8 }}>
        <input className="input" placeholder="Ask about the care record..." value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)} />
        <button className="btn primary icon-only" onClick={() => send(input)} disabled={busy} aria-label="Send">
          <Icon name="send" size={18} />
        </button>
      </div>
    </div>
  );
}
