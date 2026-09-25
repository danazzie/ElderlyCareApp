import { useEffect, useState } from "react";
import { api, Plan as PlanT } from "../api";
import { useAuth } from "../auth";

export default function Plan() {
  const { circle } = useAuth();
  const [plan, setPlan] = useState<PlanT | null>(null);
  const [newTask, setNewTask] = useState("");

  const load = () => { if (circle) api.plan(circle.id).then(setPlan).catch(() => {}); };
  useEffect(load, [circle?.id]);

  if (!plan) return <div className="empty"><span className="spin dark" /></div>;

  return (
    <div>
      <h2 style={{ marginBottom: 14 }}>Care plan</h2>
      <p className="muted" style={{ marginTop: -8 }}>
        Only family-approved items appear here. Doses are shown exactly as written in the source document.
      </p>
      <div className="grid cols-2">
        <div className="stack">
          <div className="section-title">💊 Medications</div>
          <div className="card">
            {plan.medications.length === 0 && <div className="muted">No approved medications yet.</div>}
            {plan.medications.map((m) => (
              <div className="list-item" key={m.id}>
                <div className="avatar">💊</div>
                <div style={{ flex: 1 }}>
                  <b>{m.name}</b> <span className="muted">{m.dose}</span>
                  <div className="tiny">{m.schedule}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="section-title">📅 Appointments</div>
          <div className="card">
            {plan.appointments.length === 0 && <div className="muted">No appointments yet.</div>}
            {plan.appointments.map((a) => (
              <div className="list-item" key={a.id}>
                <div className="avatar amber">📅</div>
                <div style={{ flex: 1 }}>
                  <b>{a.what || "Appointment"}</b>
                  <div className="muted">{a.when}{a.where ? ` · ${a.where}` : ""}</div>
                </div>
                {a.status === "rescheduled" && <span className="badge amber">moved</span>}
              </div>
            ))}
          </div>
        </div>

        <div className="stack">
          <div className="section-title">✅ Tasks & instructions</div>
          <div className="card">
            <div className="row" style={{ marginBottom: 8 }}>
              <input className="input" placeholder="Add a task…" value={newTask}
                onChange={(e) => setNewTask(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newTask.trim() && circle) {
                    api.addTask(circle.id, newTask.trim()).then(() => { setNewTask(""); load(); });
                  }
                }} />
            </div>
            {plan.tasks.map((t) => (
              <div className="list-item" key={t.id}>
                <button className={`check${t.status === "done" ? " done" : ""}`}
                  onClick={() => api.toggleTask(t.id).then(load)}>✓</button>
                <div style={{ flex: 1 }}>
                  <div style={{ textDecoration: t.status === "done" ? "line-through" : "none" }}>{t.title}</div>
                  <div className="tiny">{t.source.startsWith("document") ? "from document" : t.source}{t.due ? ` · ${t.due}` : ""}</div>
                </div>
              </div>
            ))}
            {plan.tasks.length === 0 && <div className="muted">No tasks yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
