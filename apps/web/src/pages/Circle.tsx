import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Icon, IconName, IconTile } from "../components/Icon";

const ROLE_BADGE: Record<string, string> = { owner: "green", member: "grey", caregiver: "amber", viewer: "grey" };

function auditIcon(action: string): { name: IconName; tone: "green" | "coral" | "amber" | "ink" } {
  if (action.includes("approved")) return { name: "circleCheck", tone: "green" };
  if (action.includes("rejected")) return { name: "ban", tone: "coral" };
  if (action.includes("red_flag")) return { name: "alert", tone: "amber" };
  return { name: "scroll", tone: "ink" };
}

export default function Circle({ activityOnly = false }: { activityOnly?: boolean }) {
  const { circle, role, refresh } = useAuth();
  const [audit, setAudit] = useState<any[]>([]);
  const [updates, setUpdates] = useState<any[]>([]);
  const [error, setError] = useState("");
  const canManage = ["owner", "member"].includes(role);

  useEffect(() => {
    if (!circle) return;
    api.audit(circle.id).then(setAudit).catch(() => {});
    api.updates(circle.id).then(setUpdates).catch(() => {});
  }, [circle?.id]);

  if (!circle) return null;
  const family = circle.members.filter((m) => ["owner", "member"].includes(m.role));
  const caregivers = circle.members.filter((m) => m.role === "caregiver");
  const pending = circle.pending_members ?? [];

  const review = async (userId: string, action: "approved" | "rejected") => {
    setError("");
    try {
      await api.reviewJoin(circle.id, userId, action);
      await refresh();
    } catch (e: any) { setError(e.message); }
  };

  const removeCaregiver = async (userId: string, name: string) => {
    if (!window.confirm(`Remove ${name} from this circle?`)) return;
    setError("");
    try {
      await api.removeMember(circle.id, userId);
      await refresh();
    } catch (e: any) { setError(e.message); }
  };

  const activity = (
    <>
      <div className="section-title">Care updates</div>
      <div className="card">
        {updates.filter((u) => u.status === "confirmed").map((u) => (
          <div className="list-item" key={u.id}>
            <IconTile name="mic" tone="coral" />
            <div style={{ flex: 1 }}>
              <b>{u.author}</b> <span className="tiny">{new Date(u.created_at).toLocaleString()}</span>
              {u.red_flags?.length > 0 && (
                <div className="alert-banner" style={{ margin: "6px 0" }}>
                  <Icon name="alert" size={14} /> {u.red_flags.join("; ")}
                </div>
              )}
              <div className="muted">{u.transcript?.slice(0, 160)}{u.transcript?.length > 160 ? "..." : ""}</div>
            </div>
          </div>
        ))}
        {updates.filter((u) => u.status === "confirmed").length === 0 && <div className="muted">No confirmed updates yet.</div>}
      </div>

      <div className="section-title">Audit log  -  who did what</div>
      <div className="card">
        {audit.map((e) => {
          const ic = auditIcon(e.action);
          return (
            <div className="list-item" key={e.id}>
              <IconTile name={ic.name} tone={ic.tone} />
              <div style={{ flex: 1 }}>
                <b>{e.actor}</b> <span className="muted">{e.action.replaceAll("_", " ")}</span>
                <div className="tiny">{new Date(e.at).toLocaleString()} · {e.entity}</div>
              </div>
            </div>
          );
        })}
        {audit.length === 0 && <div className="muted">No activity yet.</div>}
      </div>
    </>
  );

  if (activityOnly) return <div><h2 style={{ marginBottom: 14 }}>Activity</h2>{activity}</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 14 }}>{circle.recipient_name}'s circle</h2>
      {error && <div className="alert-banner" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div>}
      <div className="grid cols-2">
        <div className="stack">
          {canManage && pending.length > 0 && (
            <>
              <div className="section-title">Waiting for approval</div>
              <div className="card">
                {pending.map((m) => (
                  <div className="list-item" key={m.user_id}>
                    <div className="avatar amber">{m.name[0]}</div>
                    <div style={{ flex: 1 }}>
                      <b>{m.name}</b>
                      <div className="tiny">{m.email} · wants to join as {m.role}</div>
                    </div>
                    <button className="btn small primary" onClick={() => review(m.user_id, "approved")}>Approve</button>
                    <button className="btn small ghost" onClick={() => review(m.user_id, "rejected")}>Decline</button>
                  </div>
                ))}
              </div>
            </>
          )}
          <div className="section-title">Family</div>
          <div className="card">
            {family.map((m) => (
              <div className="list-item" key={m.user_id}>
                <div className="avatar">{m.name[0]}</div>
                <div style={{ flex: 1 }}>
                  <b>{m.name}</b>
                  <div className="tiny">{m.email}</div>
                </div>
                <span className={`badge ${ROLE_BADGE[m.role]}`}>{m.role}</span>
              </div>
            ))}
          </div>
          <div className="section-title">Caregivers</div>
          <div className="card">
            {caregivers.map((m) => (
              <div className="list-item" key={m.user_id}>
                <div className="avatar amber">{m.name[0]}</div>
                <div style={{ flex: 1 }}>
                  <b>{m.name}</b>
                  <div className="tiny">{m.email}</div>
                </div>
                <span className="badge amber">caregiver</span>
                {canManage && (
                  <button className="btn small ghost" onClick={() => removeCaregiver(m.user_id, m.name)}>Remove</button>
                )}
              </div>
            ))}
            {caregivers.length === 0 && <div className="muted">No caregivers yet  -  share the invite code.</div>}
          </div>
          {role === "owner" && (
            <div className="card stack">
              <b>Invite to this circle</b>
              <div className="muted">Share this code. New people stay pending until family approves:</div>
              <div className="row">
                <code style={{ background: "var(--sunken)", padding: "8px 14px", borderRadius: 10, fontWeight: 800, letterSpacing: 1 }}>{circle.invite_code}</code>
                <button className="btn small ghost" onClick={() => navigator.clipboard?.writeText(circle.invite_code)}>Copy</button>
              </div>
            </div>
          )}
          <div className="card stack">
            <b>Recipient profile</b>
            <div className="muted">{circle.recipient_name} · b. {circle.recipient_dob || " - "}</div>
            <div className="muted">{circle.recipient_notes}</div>
            <div className="tiny">
              Consent recorded: {circle.consent_recorded_at ? new Date(circle.consent_recorded_at).toLocaleDateString() : "not yet"} ·
              Ihtama never gives medical advice  -  emergencies: call your local emergency number.
            </div>
          </div>
        </div>
        <div className="stack">{activity}</div>
      </div>
    </div>
  );
}
