import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, Doc } from "../api";
import { useAuth } from "../auth";
import { Icon, IconTile } from "../components/Icon";
import { EmptyArt } from "../components/Illustration";
import UploadButton, { uploadCareDocument } from "../components/UploadButton";

const STATUS_BADGE: Record<string, { cls: string; label: string }> = {
  processing: { cls: "grey", label: "processing..." },
  needs_review: { cls: "coral", label: "review" },
  needs_clarification: { cls: "amber", label: "clarify" },
  approved: { cls: "green", label: "approved" },
  rejected: { cls: "grey", label: "rejected" },
};

export default function Records() {
  const { circle } = useAuth();
  const nav = useNavigate();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [params] = useSearchParams();

  const load = () => { if (circle) api.documents(circle.id).then(setDocs).catch(() => {}); };
  useEffect(() => {
    load();
    const iv = setInterval(load, 4000);
    return () => clearInterval(iv);
  }, [circle?.id]);

  const upload = async (file: File) => {
    if (!circle) {
      setError("No care circle is selected.");
      return;
    }
    setError("");
    try {
      const r = await uploadCareDocument(circle.id, file);
      nav(`/records/${r.id}`);
    } catch (e: any) { setError(e.message); }
  };

  return (
    <div>
      <div className="page-head">
        <h2>Records</h2>
        <UploadButton className="btn primary rec-upload" onError={setError}>
          <Icon name="scan" size={16} />
          <span className="desktop-only">Upload document</span>
          <span className="mobile-only">Scan</span>
        </UploadButton>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/*"
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
            e.target.value = "";
          }}
        />
      </div>
      <p className="muted" style={{ marginTop: -8 }}>
        Photograph or upload discharge letters, prescriptions and notes. Ihtama extracts medications,
        appointments and instructions  -  you approve before anything reaches the plan.
      </p>
      {error && <div className="alert-banner" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div>}

      <div
        className="card empty dropzone"
        style={{ marginBottom: 14, cursor: "pointer" }}
        role="button"
        tabIndex={0}
        onClick={() => fileRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileRef.current?.click(); }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) upload(f); }}>
        <EmptyArt />
        {params.get("upload")
          ? "Choose a PDF or photo to upload"
          : "Drag a PDF or photo here, or click to upload"}
      </div>

      <div className="stack">
        {docs.map((d) => {
          const b = STATUS_BADGE[d.status] ?? { cls: "grey", label: d.status };
          const isImg = /\.(jpg|jpeg|png|webp)$/i.test(d.filename);
          return (
            <Link key={d.id} to={`/records/${d.id}`} className="card spread">
              <div className="row" style={{ minWidth: 0 }}>
                <IconTile name={isImg ? "image" : "file"} tone={d.status === "needs_review" ? "coral" : d.status === "needs_clarification" ? "amber" : "green"} />
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
