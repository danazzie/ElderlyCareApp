import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, Doc } from "../api";
import { useAuth } from "../auth";

const STATUS_BADGE: Record<string, { cls: string; label: string }> = {
  processing: { cls: "grey", label: "processing…" },
  needs_review: { cls: "coral", label: "review" },
  needs_clarification: { cls: "amber", label: "clarify" },
  approved: { cls: "green", label: "approved" },
  rejected: { cls: "grey", label: "rejected" },
};

export default function Records() {
  const { circle } = useAuth();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [params] = useSearchParams();

  const load = () => { if (circle) api.documents(circle.id).then(setDocs).catch(() => {}); };
  useEffect(() => {
    load();
    const iv = setInterval(load, 4000); // poll while extraction runs in background
    return () => clearInterval(iv);
  }, [circle?.id]);

  useEffect(() => {
    if (params.get("upload")) fileRef.current?.click();
  }, []);

  const upload = async (file: File) => {
    if (!circle) return;
    setUploading(true); setError("");
    try {
      await api.uploadDocument(circle.id, file);
      load();
    } catch (e: any) { setError(e.message); }
    setUploading(false);
  };

  return (
    <div>
      <div className="spread" style={{ marginBottom: 14 }}>
        <h2>Records</h2>
        <label className="btn primary">
          {uploading ? <span className="spin" /> : "📄 Upload document"}
          <input ref={fileRef} type="file" hidden accept=".pdf,.jpg,.jpeg,.png,.webp"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        </label>
      </div>
      <p className="muted" style={{ marginTop: -8 }}>
        Photograph or upload discharge letters, prescriptions and notes. Ahtama extracts medications,
        appointments and instructions — you approve before anything reaches the plan.
      </p>
      {error && <div className="alert-banner" style={{ marginBottom: 12 }}>{error}</div>}

      <div
        className="card empty"
        style={{ borderStyle: "dashed", borderWidth: 2, borderColor: "var(--line)", boxShadow: "none", marginBottom: 14 }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) upload(f); }}>
        <div className="big">📄</div>
        Drag a PDF or photo here, or use the upload button
      </div>

      <div className="stack">
        {docs.map((d) => {
          const b = STATUS_BADGE[d.status] ?? { cls: "grey", label: d.status };
          return (
            <Link key={d.id} to={`/records/${d.id}`} className="card spread">
              <div className="row" style={{ minWidth: 0 }}>
                <div className="avatar">{d.filename.match(/\.(jpg|jpeg|png|webp)$/i) ? "🖼" : "📄"}</div>
                <div style={{ minWidth: 0 }}>
                  <b style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 380 }}>{d.filename}</b>
                  <div className="tiny">{d.doc_type.replaceAll("_", " ")} · {new Date(d.created_at).toLocaleDateString()}</div>
                </div>
              </div>
              <span className={`badge ${b.cls}`}>{d.status === "processing" && <span className="spin dark" style={{ width: 10, height: 10, marginRight: 5 }} />}{b.label}</span>
            </Link>
          );
        })}
        {docs.length === 0 && <div className="empty">No documents yet.</div>}
      </div>
    </div>
  );
}
