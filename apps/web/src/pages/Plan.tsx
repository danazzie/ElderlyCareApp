import { useEffect, useState } from "react";
import { api, Plan as PlanT } from "../api";
import { useAuth } from "../auth";
import { Icon, IconTile } from "../components/Icon";

export default function Plan() {
  const { circle, role } = useAuth();
  const [plan, setPlan] = useState<PlanT | null>(null);
  const [newTask, setNewTask] = useState("");
  const [newMed, setNewMed] = useState({ name: "", dose: "", schedule: "" });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [edit, setEdit] = useState({ name: "", dose: "", schedule: "" });
  const [error, setError] = useState("");
  const canEditMeds = ["owner", "member"].includes(role);

  const load = () => { if (circle) api.plan(circle.id).then(setPlan).catch(() => {}); };
  useEffect(load, [circle?.id]);

  const addMed = async () => {
    if (!circle || !newMed.name.trim()) return;
    setError("");
    try {
      await api.addMedication(circle.id, newMed.name.trim(), newMed.dose.trim(), newMed.schedule.trim());
      setNewMed({ name: "", dose: "", schedule: "" });
      load();
    } catch (e: any) { setError(e.message); }
  };

  const saveMed = async (id: string) => {
    if (!edit.name.trim()) return;
    setError("");
    try {
      await api.editMedication(id, edit.name.trim(), edit.dose.trim(), edit.schedule.trim());
      setEditingId(null);
      load();
    } catch (e: any) { setError(e.message); }
  };

  const stopMed = async (id: string, name: string) => {
    if (!window.confirm(`Stop ${name} on the plan?`)) return;
    setError("");
    try {
      await api.stopMedication(id);
      setEditingId(null);
      load();
    } catch (e: any) { setError(e.message); }
  };

  if (!plan) return <div className="empty"><span className="spin dark" /></div>;

  return (
    <div>
      <h2 style={{ marginBottom: 14 }}>Care plan</h2>
      <p className="muted" style={{ marginTop: -8 }}>
        Family can add or correct medications here. Doses stay as written  -  never normalised.
      </p>
      {error && <div className="alert-banner" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div>}
      <div className="grid cols-2">
        <div className="stack">
          <div className="section-title">Medications</div>
          <div className="card">
            {canEditMeds && (
              <div className="stack" style={{ gap: 8, marginBottom: 10 }}>
                <input className="input" placeholder="Medicine name" value={newMed.name}
                  onChange={(e) => setNewMed({ ...newMed, name: e.target.value })} />
                <div className="row">
                  <input className="input" placeholder="Dose as written" value={newMed.dose}
                    onChange={(e) => setNewMed({ ...newMed, dose: e.target.value })} />
                  <input className="input" placeholder="Schedule" value={newMed.schedule}
                    onChange={(e) => setNewMed({ ...newMed, schedule: e.target.value })} />
                </div>
                <button className="btn small ghost" onClick={addMed} disabled={!newMed.name.trim()}>
                  <Icon name="plus" size={14} /> Add medication
                </button>
              </div>
            )}
            {plan.medications.length === 0 && <div className="muted">No medications on the plan yet.</div>}
            {plan.medications.map((m) => (
              <div className="list-item" key={m.id}>
                <IconTile name="pill" tone="green" />
                {editingId === m.id ? (
                  <div style={{ flex: 1 }} className="stack" >
                    <input className="input" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} />
                    <div className="row">
                      <input className="input" value={edit.dose} onChange={(e) => setEdit({ ...edit, dose: e.target.value })} />
                      <input className="input" value={edit.schedule} onChange={(e) => setEdit({ ...edit, schedule: e.target.value })} />
                    </div>
                    <div className="row">
                      <button className="btn small primary" onClick={() => saveMed(m.id)}>Save</button>
                      <button className="btn small ghost" onClick={() => setEditingId(null)}>Cancel</button>
                      <button className="btn small coral" onClick={() => stopMed(m.id, m.name)}>Stop</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ flex: 1 }}>
                      <b>{m.name}</b> <span className="muted">{m.dose}</span>
                      <div className="tiny">{m.schedule}</div>
                    </div>
                    {canEditMeds && (
                      <button className="btn small ghost" onClick={() => { setEditingId(m.id); setEdit({ name: m.name, dose: m.dose, schedule: m.schedule }); }}>
                        <Icon name="pencil" size={14} /> Edit
                      </button>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>

          <div className="section-title">Appointments</div>
          <div className="card">
            {plan.appointments.length === 0 && <div className="muted">No appointments yet.</div>}
            {plan.appointments.map((a) => (
              <div className="list-item" key={a.id}>
                <IconTile name="calendar" tone="amber" />
                <div style={{ flex: 1 }}>
                  <b>{a.what || "Appointment"}</b>
                  <div className="muted">{a.when}{a.where ? ` ù ${a.where}` : ""}</div>
                </div>
                {a.status === "rescheduled" && <span className="badge amber">moved</span>}
              </div>
            ))}
          </div>
        </div>

        <div className="stack">
          <div className="section-title">Tasks and instructions</div>
          <div className="card">
            <div className="row" style={{ marginBottom: 8 }}>
              <input className="input" placeholder="Add a task..." value={newTask}
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
                  onClick={() => api.toggleTask(t.id).then(load)}>
                  <Icon name="check" size={13} stroke={2.5} />
                </button>
                <div style={{ flex: 1 }}>
                  <div style={{ textDecoration: t.status === "done" ? "line-through" : "none" }}>{t.title}</div>
                  <div className="tiny">{t.source.startsWith("document") ? "from document" : t.source}{t.due ? ` ∑ ${t.due}` : ""}</div>
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
