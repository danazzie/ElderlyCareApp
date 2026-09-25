import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, Doc, ExtractedItem, getToken } from "../api";
import { useAuth } from "../auth";
import { Icon, IconName, IconTile } from "../components/Icon";

const KIND_ICON: Record<string, IconName> = {
  medication: "pill", appointment: "calendar", instruction: "clipboard",
  observation: "stethoscope", contact: "phone",
};

function ItemCard({ item, decision, onDecide, onEdit, canReview }:
  { item: ExtractedItem; decision: string; onDecide: (d: string) => void;
    onEdit: (payload: any) => void; canReview: boolean }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(JSON.stringify(item.payload, null, 2));
  const blocking = item.flags.some((f) => ["conflict", "missing_field"].includes(f));

  return (
    <div className="card stack" style={{ opacity: decision === "rejected" ? 0.5 : 1 }}>
      <div className="spread">
        <div className="row">
          <IconTile name={KIND_ICON[item.kind] ?? "file"} tone="green" size={32} iconSize={16} />
          <b>{item.payload.name ?? item.payload.what ?? item.payload.text?.slice(0, 60) ?? item.kind}</b>
        </div>
        <span className="tiny">p.{item.source_page} ù conf {Math.round(item.confidence * 100)}%</span>
      </div>
      <div>
        {item.flags.map((f) => <span key={f} className={`flag ${f}`}>{f.replaceAll("_", " ")}</span>)}
      </div>
      {!editing ? (
        <div className="muted" style={{ fontSize: 13 }}>
          {Object.entries(item.payload).filter(([k]) => !["name", "what", "text"].includes(k))
            .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" ù ")}
          {item.payload.text && item.payload.text.length > 60 ? ` ${item.payload.text}` : ""}
        </div>
      ) : (
        <textarea className="input" rows={5} value={draft} onChange={(e) => setDraft(e.target.value)} />
      )}
      {item.source_quote && (
        <div className="quote">"{item.source_quote}" <span className="cite-chip">source ù p.{item.source_page}</span></div>
      )}
      {canReview && item.review_status === "pending" && (
        <div className="row">
          {!editing ? (
            <>
              <button className={`btn small ${decision === "approved" && !blocking ? "primary" : "ghost"}`}
                disabled={blocking}
                title={blocking ? "Blocked until the conflict/missing field is resolved" : ""}
                onClick={() => onDecide("approved")}><Icon name="check" size={14} /> Approve</button>
              <button className="btn small ghost" onClick={() => setEditing(true)}><Icon name="pencil" size={14} /> Edit</button>
              <button className={`btn small ${decision === "rejected" ? "coral" : "ghost"}`}
                onClick={() => onDecide("rejected")}><Icon name="close" size={14} /> Reject</button>
              {blocking && <span className="tiny" style={{ color: "var(--coral-deep)" }}>blocked  -  edit to resolve</span>}
            </>
          ) : (
            <>
              <button className="btn small primary" onClick={() => {
                try { onEdit(JSON.parse(draft)); setEditing(false); } catch { alert("Invalid JSON"); }
              }}>Save edit</button>
              <button className="btn small ghost" onClick={() => setEditing(false)}>Cancel</button>
            </>
          )}
        </div>
      )}
      {item.review_status !== "pending" && <span className={`badge ${item.review_status === "approved" ? "green" : "grey"}`}>{item.review_status}</span>}
    </div>
  );
}

export default function DocumentReview() {
  const { docId } = useParams();
  const { role } = useAuth();
  const nav = useNavigate();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [edits, setEdits] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const canReview = ["owner", "member"].includes(role);

  const load = () => { if (docId) api.document(docId).then(setDoc).catch((e) => setError(e.message)); };
  useEffect(() => {
    load();
    const iv = setInterval(() => {
      setDoc((d) => { if (d && d.status === "processing") load(); return d; });
    }, 3000);
    return () => clearInterval(iv);
  }, [docId]);

  if (!doc) return <div className="empty">{error || <span className="spin dark" />}</div>;

  const pending = doc.status === "needs_review" || doc.status === "needs_clarification";
  const issues = doc.review_request?.validation_issues ?? [];
  const isImage = /\.(jpe?g|png|webp)$/i.test(doc.filename);
  const fileUrl = `/api/documents/${doc.id}/file`;

  const submit = async (action: string) => {
    setBusy(true); setError("");
    try {
      const body: any = { action, items: decisions };
      if (action === "edited") body.edits = Object.fromEntries(
        Object.entries(edits).map(([id, payload]) => [id, { payload }]));
      const r = await api.review(doc.id, body);
      setDoc(r);
      setDecisions({}); setEdits({});
    } catch (e: any) { setError(e.message); }
    setBusy(false);
  };

  return (
    <div>
      <button className="btn small ghost" onClick={() => nav("/records")} style={{ marginBottom: 12 }}>
        <Icon name="chevronLeft" size={16} /> Records
      </button>
      <div className="spread" style={{ marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
        <h2 style={{ wordBreak: "break-all" }}>{doc.filename}</h2>
        <span className={`badge ${doc.status === "approved" ? "green" : pending ? "coral" : "grey"}`}>{doc.status.replaceAll("_", " ")}</span>
      </div>
      {doc.summary && <p className="muted">{doc.summary}</p>}
      {doc.status === "rejected" && doc.reject_reason && (
        <div className="alert-banner" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {doc.reject_reason}</div>
      )}
      {issues.length > 0 && (
        <div className="alert-banner" style={{ background: "var(--amber-soft)", borderColor: "var(--amber)", color: "var(--amber-deep)", marginBottom: 12 }}>
          {issues.map((s, i) => <div key={i}><Icon name="alert" size={14} /> {s}</div>)}
        </div>
      )}

      <div className="grid cols-2">
        <div className="card" style={{ minHeight: 320 }}>
          <b>Source document</b>
          <div style={{ marginTop: 10 }}>
            {isImage ? (
              <AuthedImage url={fileUrl} />
            ) : (
              <a className="btn ghost" href="#" onClick={async (e) => {
                e.preventDefault();
                const r = await fetch(fileUrl, { headers: { Authorization: `Bearer ${getToken()}` } });
                const blob = await r.blob();
                window.open(URL.createObjectURL(blob), "_blank");
              }}><Icon name="file" size={16} /> Open PDF</a>
            )}
          </div>
        </div>

        <div className="stack">
          <b>Extracted items ({(doc.items ?? []).length})</b>
          {(doc.items ?? []).map((item) => (
            <ItemCard key={item.id} item={item} canReview={canReview && pending}
              decision={decisions[item.id] ?? "approved"}
              onDecide={(d) => setDecisions({ ...decisions, [item.id]: d })}
              onEdit={(payload) => setEdits({ ...edits, [item.id]: payload })} />
          ))}
          {(doc.items ?? []).length === 0 && doc.status !== "processing" && (
            <div className="card muted">No items were extracted.</div>
          )}
          {doc.status === "processing" && <div className="card muted"><span className="spin dark" /> Extracting...</div>}
        </div>
      </div>

      {pending && canReview && (
        <div className="card row sticky-actions" style={{ position: "sticky", bottom: 84, marginTop: 16, flexWrap: "wrap" }}>
          <button className="btn primary" disabled={busy} onClick={() => submit(Object.keys(edits).length ? "edited" : "approved")}>
            {busy ? <span className="spin" /> : Object.keys(edits).length ? "Save edits & re-check" : "Approve & update plan"}
          </button>
          <button className="btn coral" disabled={busy} onClick={() => submit("rejected")}>Reject document</button>
          <span className="tiny">Items flagged conflict/missing stay blocked until edited  -  safety rule.</span>
        </div>
      )}
      {pending && !canReview && (
        <div className="card muted" style={{ marginTop: 16 }}>Waiting for a family member (owner/member) to review. Caregivers can upload but not approve.</div>
      )}
      {error && <div className="alert-banner" style={{ marginTop: 12 }}><Icon name="alert" size={16} /> {error}</div>}
    </div>
  );
}

function AuthedImage({ url }: { url: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob()).then((b) => setSrc(URL.createObjectURL(b)));
  }, [url]);
  return src ? <img src={src} style={{ width: "100%", borderRadius: 12 }} /> : <span className="spin dark" />;
}
