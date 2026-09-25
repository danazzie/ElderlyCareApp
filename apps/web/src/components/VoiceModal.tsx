import { useRef, useState } from "react";
import { api, CareUpdate } from "../api";
import { useAuth } from "../auth";
import { Icon } from "./Icon";

type Draft = Record<string, any>;

function cloneStructured(s: Draft): Draft {
  return {
    ...s,
    meals: s.meals ?? "",
    mood: s.mood ?? "",
    vitals: { ...(s.vitals ?? {}) },
    medications_given: [...(s.medications_given ?? [])],
    incidents: [...(s.incidents ?? [])],
    appointments: [...(s.appointments ?? [])],
    medication_changes: [...(s.medication_changes ?? [])],
    red_flags: [...(s.red_flags ?? [])],
    needs_clarification: [...(s.needs_clarification ?? [])],
  };
}

export default function VoiceModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const { circle } = useAuth();
  const [phase, setPhase] = useState<"input" | "processing" | "review">("input");
  const [recording, setRecording] = useState(false);
  const [draft, setDraft] = useState<CareUpdate | null>(null);
  const [edit, setEdit] = useState<Draft>({});
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const beginReview = (u: CareUpdate) => {
    setDraft(u);
    setEdit(cloneStructured(u.structured ?? {}));
    setEditing(false);
    setPhase("review");
  };

  const submit = async (audio: Blob | null, filename: string) => {
    if (!circle) return;
    setPhase("processing");
    setError("");
    try {
      const u = await api.createUpdate(circle.id, audio, filename, audio ? "" : text);
      beginReview(u);
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
      setError("Microphone unavailable  -  upload an audio file or type the update instead.");
    }
  };

  const decide = async (action: "confirmed" | "discarded") => {
    if (!draft) return;
    const r = await api.confirmUpdate(draft.id, action, action === "confirmed" ? edit : undefined);
    if (r.status === "confirmed") onSaved();
    onClose();
  };

  const s = editing ? edit : (draft?.structured ?? {});
  const clarifications: string[] = s.needs_clarification ?? [];

  const setField = (key: string, value: any) => setEdit((prev) => ({ ...prev, [key]: value }));
  const setVital = (key: string, value: string) =>
    setEdit((prev) => ({ ...prev, vitals: { ...(prev.vitals ?? {}), [key]: value } }));

  const patchList = (key: string, i: number, field: string, value: string) =>
    setEdit((prev) => {
      const rows = [...(prev[key] ?? [])];
      rows[i] = { ...(rows[i] ?? {}), [field]: value };
      return { ...prev, [key]: rows };
    });

  const addRow = (key: string, row: Record<string, string>) =>
    setEdit((prev) => ({ ...prev, [key]: [...(prev[key] ?? []), row] }));

  const removeRow = (key: string, i: number) =>
    setEdit((prev) => ({ ...prev, [key]: (prev[key] ?? []).filter((_: any, idx: number) => idx !== i) }));

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal stack" onClick={(e) => e.stopPropagation()}>
        <div className="spread">
          <h3>Voice update</h3>
          <button className="btn small ghost icon-only" onClick={onClose} aria-label="Close">
            <Icon name="close" size={16} />
          </button>
        </div>

        {phase === "input" && (
          <>
            <p className="muted">Record what happened during the visit  -  meals, medications given,
              vitals, mood, or a new clinic date. Confirming shares it and updates the plan.</p>
            <button className={`rec-btn${recording ? " recording" : ""}`} onClick={toggleRecord} aria-label={recording ? "Stop" : "Record"}>
              <Icon name={recording ? "stop" : "mic"} size={32} />
            </button>
            <div className="tiny" style={{ textAlign: "center" }}>
              {recording ? "Recording... tap to stop" : "Tap to record"}
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
            <textarea className="input" rows={2} placeholder="...or type the update"
              value={text} onChange={(e) => setText(e.target.value)} />
            {text.trim() && <button className="btn primary" onClick={() => submit(null, "")}>Process text update</button>}
            {error && <div className="alert-banner"><Icon name="alert" size={16} /> {error}</div>}
          </>
        )}

        {phase === "processing" && (
          <div className="empty"><span className="spin dark" /> <div>Transcribing and structuring...</div></div>
        )}

        {phase === "review" && draft && (
          <>
            {draft.red_flags.length > 0 && (
              <div className="alert-banner"><Icon name="alert" size={16} /> {draft.red_flags.join(" · ")}</div>
            )}
            <div className="quote">"{draft.transcript}"</div>

            {!editing ? (
              <div className="stack" style={{ gap: 6 }}>
                {s.meals && <div className="row"><Icon name="utensils" size={16} /> <b>Meals:</b> {s.meals}</div>}
                {(s.medications_given ?? []).length > 0 && (
                  <div className="row"><Icon name="pill" size={16} /> <b>Medications:</b>{" "}
                    {(s.medications_given as any[]).map((m) => `${m.what} (${m.time})`).join(", ")}</div>
                )}
                {Object.keys(s.vitals ?? {}).length > 0 && (
                  <div className="row"><Icon name="stethoscope" size={16} /> <b>Vitals:</b> {Object.entries(s.vitals).map(([k, v]) => `${k} ${v}`).join(", ")}</div>
                )}
                {s.mood && <div className="row"><Icon name="smile" size={16} /> <b>Mood:</b> {s.mood}</div>}
                {(s.incidents ?? []).length > 0 && (
                  <div className="row"><Icon name="circleAlert" size={16} /> <b>Incidents:</b> {(s.incidents as string[]).join("; ")}</div>
                )}
                {(s.appointments ?? []).length > 0 && (
                  <div className="row"><Icon name="calendar" size={16} /> <b>Appointments:</b>{" "}
                    {(s.appointments as any[]).map((a) => `${a.what}${a.when ? ` (${a.when})` : ""}`).join("; ")}</div>
                )}
                {(s.medication_changes ?? []).length > 0 && (
                  <div className="row"><Icon name="pill" size={16} /> <b>Plan changes:</b>{" "}
                    {(s.medication_changes as any[]).map((m) => `${m.change || "CHANGED"} ${m.name}${m.dose ? ` ${m.dose}` : ""}`).join("; ")}</div>
                )}
                {s.has_care_facts === false && <div className="muted">No care facts detected in this note.</div>}
              </div>
            ) : (
              <div className="stack" style={{ gap: 10 }}>
                <label className="tiny">Meals
                  <input className="input" value={edit.meals ?? ""} onChange={(e) => setField("meals", e.target.value)} />
                </label>
                <label className="tiny">Mood
                  <input className="input" value={edit.mood ?? ""} onChange={(e) => setField("mood", e.target.value)} />
                </label>
                <label className="tiny">Blood pressure
                  <input className="input" value={edit.vitals?.bp ?? ""} onChange={(e) => setVital("bp", e.target.value)} placeholder="128/78" />
                </label>
                <div className="tiny">Appointments to add to the plan</div>
                {(edit.appointments ?? []).map((a: any, i: number) => (
                  <div className="row" key={i} style={{ alignItems: "flex-start" }}>
                    <input className="input" placeholder="What" value={a.what ?? ""} onChange={(e) => patchList("appointments", i, "what", e.target.value)} />
                    <input className="input" placeholder="When" value={a.when ?? ""} onChange={(e) => patchList("appointments", i, "when", e.target.value)} />
                    <button className="btn small ghost icon-only" aria-label="Remove appointment" onClick={() => removeRow("appointments", i)}>
                      <Icon name="close" size={14} />
                    </button>
                  </div>
                ))}
                <button className="btn small ghost" onClick={() => addRow("appointments", { what: "", when: "", where: "", with_whom: "" })}>
                  <Icon name="plus" size={14} /> Add appointment
                </button>
                <div className="tiny">Medication plan changes</div>
                {(edit.medication_changes ?? []).map((m: any, i: number) => (
                  <div className="row" key={i} style={{ alignItems: "flex-start" }}>
                    <input className="input" placeholder="STARTED / STOPPED" value={m.change ?? ""} onChange={(e) => patchList("medication_changes", i, "change", e.target.value)} />
                    <input className="input" placeholder="Name" value={m.name ?? ""} onChange={(e) => patchList("medication_changes", i, "name", e.target.value)} />
                    <input className="input" placeholder="Dose" value={m.dose ?? ""} onChange={(e) => patchList("medication_changes", i, "dose", e.target.value)} />
                    <button className="btn small ghost icon-only" aria-label="Remove change" onClick={() => removeRow("medication_changes", i)}>
                      <Icon name="close" size={14} />
                    </button>
                  </div>
                ))}
                <button className="btn small ghost" onClick={() => addRow("medication_changes", { change: "STARTED", name: "", dose: "", frequency: "" })}>
                  <Icon name="plus" size={14} /> Add medication change
                </button>
              </div>
            )}

            {clarifications.length > 0 && (
              <div className="alert-banner" style={{ background: "var(--amber-soft)", borderColor: "var(--amber)", color: "var(--amber-deep)" }}>
                {clarifications.join(" ")}
              </div>
            )}
            <div className="row">
              {!editing ? (
                <>
                  <button className="btn primary" style={{ flex: 1 }} onClick={() => decide("confirmed")}>Confirm & share</button>
                  <button className="btn ghost" onClick={() => setEditing(true)}><Icon name="pencil" size={15} /> Edit</button>
                  <button className="btn ghost" onClick={() => decide("discarded")}>Discard</button>
                </>
              ) : (
                <>
                  <button className="btn primary" style={{ flex: 1 }} onClick={() => { setEditing(false); void decide("confirmed"); }}>
                    Save & share
                  </button>
                  <button className="btn ghost" onClick={() => { setEdit(cloneStructured(draft.structured ?? {})); setEditing(false); }}>
                    Cancel
                  </button>
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
