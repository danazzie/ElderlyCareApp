import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, Today } from "../api";
import { useAuth } from "../auth";
import VoiceModal from "../components/VoiceModal";

function Ring({ done, total }: { done: number; total: number }) {
  const pct = total ? done / total : 0;
  const r = 26, c = 2 * Math.PI * r;
  return (
    <div className="ring">
      <svg width="62" height="62">
        <circle cx="31" cy="31" r={r} fill="none" stroke="var(--line)" strokeWidth="6" />
        <circle cx="31" cy="31" r={r} fill="none" stroke="var(--green)" strokeWidth="6"
          strokeDasharray={`${c * pct} ${c}`} strokeLinecap="round" />
      </svg>
      <div className="ring-label">{done}/{total}<small>meds</small></div>
    </div>
  );
}

export default function Home() {
  const { circle, user, role } = useAuth();
  const nav = useNavigate();
  const [today, setToday] = useState<Today | null>(null);
  const [voice, setVoice] = useState(false);
  const [plan, setPlan] = useState<any>(null);

  const load = () => {
    if (!circle) return;
    api.today(circle.id).then(setToday).catch(() => {});
    api.plan(circle.id).then(setPlan).catch(() => {});
  };
  useEffect(load, [circle?.id]);

  if (!circle || !today) return <div className="empty"><span className="spin dark" /></div>;

  const vitals = today.latest_update?.structured?.vitals ?? {};
  const bp = vitals.bp as string | undefined;
  const openTasks = (plan?.tasks ?? []).filter((t: any) => t.status === "open").slice(0, 4);
  const doneTasks = (plan?.tasks ?? []).filter((t: any) => t.status === "done").slice(0, 2);

  return (
    <div>
      <div className="spread" style={{ marginBottom: 14 }}>
        <div>
          <div className="muted">Good morning, {user?.name}</div>
          <h2>{today.recipient_name}'s care today</h2>
        </div>
        <div className="row" style={{ display: window.innerWidth >= 768 ? "flex" : "none" }}>
          <button className="btn primary" onClick={() => setVoice(true)}>🎤 Voice update</button>
          <button className="btn ghost" onClick={() => nav("/records?upload=1")}>📄 Upload document</button>
        </div>
      </div>

      {today.alerts.length > 0 && (
        <div className="alert-banner" style={{ marginBottom: 14 }}>⚠ {today.alerts[0]}</div>
      )}

      <div className="grid cols-main">
        <div className="stack">
          {/* recipient card */}
          <div className="card row" style={{ gap: 14 }}>
            <div className="avatar big">{today.recipient_name[0]}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <b>{today.recipient_name}</b>
              <div className="muted">{circle.recipient_notes || "Care circle"}</div>
              <div className="row" style={{ marginTop: 6, flexWrap: "wrap", gap: 6 }}>
                {bp && <span className="badge green">🩺 BP {bp}</span>}
                {today.next_appointment && (
                  <span className="badge amber">📅 {today.next_appointment.when}</span>
                )}
                {today.latest_update && <span className="badge grey">updated {new Date(today.latest_update.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>}
              </div>
            </div>
            <Ring done={today.medications_count} total={Math.max(today.medications_count, 1) } />
          </div>

          {/* quick actions (mobile emphasis, matches the mock) */}
          <div className="quick-actions">
            <button className="qa-btn" onClick={() => setVoice(true)}>
              <span className="icon green">🎤</span>Voice</button>
            <button className="qa-btn" onClick={() => nav("/records?upload=1")}>
              <span className="icon blue">📷</span>Scan</button>
            <button className="qa-btn" onClick={() => nav("/ask")}>
              <span className="icon amber">✳️</span>Ask</button>
            <a className="qa-btn" href="tel:999">
              <span className="icon coral">🆘</span>Emergency</a>
          </div>

          {/* approvals */}
          <div className="section-title">
            Needs your approval
            <span className="muted">{today.approvals_waiting.length} items →</span>
          </div>
          {today.approvals_waiting.length === 0 ? (
            <div className="card muted">Nothing waiting — all changes approved. ✓</div>
          ) : (
            today.approvals_waiting.map((d) => (
              <Link to={`/records/${d.id}`} key={d.id} className="card spread">
                <div className="row">
                  <div className="avatar">📄</div>
                  <div>
                    <b>{d.filename}</b>
                    <div className="muted" style={{ maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.summary || d.doc_type}</div>
                  </div>
                </div>
                <span className={`badge ${d.status === "needs_clarification" ? "amber" : "coral"}`}>
                  {d.status === "needs_clarification" ? "clarify" : "review"}
                </span>
              </Link>
            ))
          )}

          {/* today's plan */}
          <div className="section-title">Today's plan <Link className="muted" to="/plan">See all →</Link></div>
          <div className="card">
            {openTasks.length + doneTasks.length === 0 && (
              <div className="muted">No tasks yet — approve a document to build the plan.</div>
            )}
            {[...doneTasks, ...openTasks].map((t: any) => (
              <div className="list-item" key={t.id}>
                <button className={`check${t.status === "done" ? " done" : ""}`}
                  onClick={() => api.toggleTask(t.id).then(load)}>✓</button>
                <div style={{ flex: 1 }}>
                  <div style={{ textDecoration: t.status === "done" ? "line-through" : "none" }}>{t.title}</div>
                  {t.due && <div className="tiny">{t.due}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* right column (desktop) */}
        <div className="stack">
          <div className="card stack">
            <b>Latest from the circle</b>
            {today.latest_update ? (
              <div className="row">
                <div className="avatar coral">🎙</div>
                <div className="muted">
                  {Object.entries(today.latest_update.structured?.vitals ?? {}).map(([k, v]) => `${k} ${v}`).join(", ") ||
                    today.latest_update.structured?.meals || "Care update received"}
                </div>
              </div>
            ) : (
              <div className="muted">No confirmed updates yet.</div>
            )}
            <Link to="/circle" className="tiny" style={{ color: "var(--green-dark)", fontWeight: 700 }}>View all activity →</Link>
          </div>
          <div className="card stack">
            <b>Next appointment</b>
            {today.next_appointment ? (
              <div className="row">
                <div className="avatar amber">📅</div>
                <div>
                  <b>{today.next_appointment.what}</b>
                  <div className="muted">{today.next_appointment.when}{today.next_appointment.where ? ` · ${today.next_appointment.where}` : ""}</div>
                </div>
              </div>
            ) : <div className="muted">Nothing scheduled.</div>}
          </div>
          <div className="card stack">
            <b>Medications ({today.medications_count})</b>
            {today.medications.slice(0, 5).map((m, i) => (
              <div className="spread" key={i}>
                <span>💊 {m.name} <span className="muted">{m.dose}</span></span>
                <span className="tiny">{m.schedule}</span>
              </div>
            ))}
            {today.medications_count === 0 && <div className="muted">Approve a prescription to fill this list.</div>}
          </div>
          {role === "caregiver" && (
            <div className="card stack">
              <b>You're on shift</b>
              <button className="btn primary" onClick={() => setVoice(true)}>🎤 Record visit update</button>
            </div>
          )}
        </div>
      </div>

      {voice && <VoiceModal onClose={() => setVoice(false)} onSaved={load} />}
    </div>
  );
}
