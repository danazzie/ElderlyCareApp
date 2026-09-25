import { useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Icon } from "./Icon";

type Props = {
  className?: string;
  label?: string;
  children?: ReactNode;
  onError?: (message: string) => void;
};

export async function uploadCareDocument(circleId: string, file: File) {
  return api.uploadDocument(circleId, file);
}

export default function UploadButton({ className = "btn primary", label = "Upload document", children, onError }: Props) {
  const { circle } = useAuth();
  const nav = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  const send = async (file: File) => {
    if (!circle) {
      onError?.("No care circle is selected.");
      return;
    }
    setBusy(true);
    try {
      const r = await uploadCareDocument(circle.id, file);
      nav(`/records/${r.id}`);
    } catch (e: any) {
      onError?.(e.message || "Upload failed");
    }
    setBusy(false);
  };

  return (
    <span className="upload-control">
      <button
        type="button"
        className={className}
        disabled={busy}
        onClick={() => fileRef.current?.click()}
      >
        {busy ? <span className="spin" /> : (children ?? <><Icon name="upload" size={16} /> {label}</>)}
      </button>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/*"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void send(f);
          e.target.value = "";
        }}
      />
    </span>
  );
}
