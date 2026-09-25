import { useRef, useState } from "react";
import { api, CareUpdate } from "../api";
import { useAuth } from "../auth";

/** Voice care update: record (MediaRecorder) or upload an audio file ?
 * transcript + structured draft ? caregiver confirms (Graph B interrupt). */
export default function VoiceModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const { circle } = useAuth();
  const [phase, setPhase] = useState<"input" | "processing" | "review">("input");
  const [recording, setRecording] = useState(false);
  const [draft, setDraft] = useState<CareUpdate | null>(null);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const submit = async (audio: Blob | null, filename: string) => {
    if (!circle) return;
    setPhase("processing");
    setError("");
    try {
      const u = await api.createUpdate(circle.id, audio, filename, audio ? "" : text);
      setDraft(u);
      setPhase("review");
    } catch (e: any) {
      setError(e.message);
      setPhase("input");
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
        submit(blob, "recording.webm");
      };
      rec.start();
      recRef.current = rec;
      setRecording(true);
    } catch {
      setError("Microphone unavailable — upload an audio file or type the update instead.");
    }
  };

  const decide = async (action: "confirmed" | "discarded") => {
    if (!draft) return;
    const r = await api.confirmUpdate(draft.id, action);
    if (r.status === "confirmed") onSaved();
    onClose();
  };

  const s = draft?.structured ?? {};
  const clarifications: string[] = s.needs_clarification ?? [];

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal stack" onClick={(e) => e.stopPropagation()}>
        <div className="spread">
          <h3>🎙 Voice update</h3>
          <button className="btn small ghost" onClick={onClose}>✕</button>
        </div>

        {phase === "input" && (
          <>
            <p className="muted">Record what happened during the visit — meals, medications given,
              vitals, mood. Ahtama structures it for the family.</p>
            <button className={`rec-btn${recording ? " recording" : ""}`} onClick={toggleRecord}>
              {recording ? "■" : "🎤"}
            </button>
            <div className="tiny" style={{ textAlign: "center" }}>
              {recording ? "Recording… tap to stop" : "Tap to record"}
            </div>
            <div className="row" style={{ justifyContent: "center", gap: 14 }}>
              <label className="btn small ghost">
                Upload audio
                <input type="file" accept="audio/*,.m4a" hidden
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) submit(f, f.name);
                  }} />
              </label>
            </div>
            <textarea className="input" rows={2} placeholder="…or type the update"
              value={text} onChange={(e) => setText(e.target.value)} />
            {text.trim() && <button className="btn primary" onClick={() => submit(null, "")}>Process text update</button>}
            {error && <div className="alert-banner">{error}</div>}
          </>
        )}

        {phase === "processing" && (
          <div className="empty"><span className="spin dark" /> <div>Transcribing and structuring…</div></div>
        )}

        {phase === "review" && draft && (
          <>
            {draft.red_flags.length > 0 && (
              <div className="alert-banner">⚠ {draft.red_flags.join(" · ")}</div>
            )}
            <div className="quote">“{draft.transcript}”</div>
            <div className="stack" style={{ gap: 6 }}>
              {s.meals && <div><b>🍽 Meals:</b> {s.meals}</div>}
              {(s.medications_given ?? []).length > 0 && (
                <div><b>💊 Medications:</b>{" "}
                  {(s.medications_given as any[]).map((m) => `${m.what} (${m.time})`).join(", ")}</div>
              )}
              {Object.keys(s.vitals ?? {}).length > 0 && (
                <div><b>🩺 Vitals:</b> {Object.entries(s.vitals).map(([k, v]) => `${k} ${v}`).join(", ")}</div>
              )}
              {s.mood && <div><b>🙂 Mood:</b> {s.mood}</div>}
              {(s.incidents ?? []).length > 0 && <div><b>❗ Incidents:</b> {(s.incidents as string[]).join("; ")}</div>}
              {s.has_care_facts === false && <div className="muted">No care facts detected in this note.</div>}
            </div>
            {clarifications.length > 0 && (
              <div className="alert-banner" style={{ background: "var(--amber-soft)", borderColor: "var(--amber)", color: "#9a7112" }}>
                {clarifications.join(" ")}
              </div>
            )}
            <div className="row">
              <button className="btn primary" style={{ flex: 1 }} onClick={() => decide("confirmed")}>Confirm & share</button>
              <button className="btn ghost" onClick={() => decide("discarded")}>Discard</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
