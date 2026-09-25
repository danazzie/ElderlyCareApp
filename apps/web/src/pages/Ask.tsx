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
  const [recording, setRecording] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (circle) api.messages(circle.id).then(setMsgs).catch(() => {}); }, [circle?.id]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs.length, busy]);
  useEffect(() => () => { window.speechSynthesis?.cancel(); recRef.current?.state === "recording" && recRef.current.stop(); }, []);

  const clearChat = async () => {
    if (!circle || !msgs.length) return;
    if (!window.confirm("Clear this circle's Ask history? This cannot be undone.")) return;
    window.speechSynthesis?.cancel();
    setSpeakingId(null);
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

  const fromAudio = async (blob: Blob, filename: string) => {
    if (!circle) return;
    setBusy(true);
    try {
      const { transcript } = await api.transcribeAsk(circle.id, blob, filename);
      if (!transcript.trim()) throw new Error("I could not hear a question in that recording.");
      setBusy(false);
      await send(transcript.trim());
    } catch (e: any) {
      setMsgs((m) => [...m, { id: "err", role: "assistant", content: e.message, citations: [], route: "", created_at: "" }]);
      setBusy(false);
    }
  };

  const toggleRecord = async () => {
    if (recording) {
      recRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        fromAudio(blob, "ask.webm");
      };
      rec.start();
      recRef.current = rec;
      setRecording(true);
    } catch {
      fileRef.current?.click();
    }
  };

  const speak = (m: ChatMsg) => {
    if (!window.speechSynthesis) return;
    if (speakingId === m.id) {
      window.speechSynthesis.cancel();
      setSpeakingId(null);
      return;
    }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(m.content);
    u.onend = () => setSpeakingId(null);
    u.onerror = () => setSpeakingId(null);
    setSpeakingId(m.id);
    window.speechSynthesis.speak(u);
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
        Ask by voice or text. I remember this chat until you clear it.
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
            {m.role === "assistant" && m.content && (
              <button className="speak-btn" onClick={() => speak(m)} type="button"
                aria-label={speakingId === m.id ? "Stop reading" : "Listen to answer"}>
                <Icon name={speakingId === m.id ? "volumeOff" : "volume"} size={14} />
                {speakingId === m.id ? "Stop" : "Listen"}
              </button>
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant"><span className="spin dark" /></div>}
        <div ref={endRef} />
      </div>

      <div className="row composer" style={{ position: "sticky", bottom: 84, background: "var(--bg)", paddingTop: 8 }}>
        <input ref={fileRef} type="file" accept="audio/*" className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) fromAudio(f, f.name); e.target.value = ""; }} />
        <button className={`btn icon-only ${recording ? "coral" : "ghost"}`} type="button"
          onClick={toggleRecord} disabled={busy} aria-label={recording ? "Stop recording" : "Ask by voice"}>
          <Icon name={recording ? "stop" : "mic"} size={18} />
        </button>
        <input className="input" placeholder={recording ? "Listening…" : "Ask about the care record..."}
          value={input} disabled={recording}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)} />
        <button className="btn primary icon-only" onClick={() => send(input)} disabled={busy || recording} aria-label="Send">
          <Icon name="send" size={18} />
        </button>
      </div>
    </div>
  );
}
