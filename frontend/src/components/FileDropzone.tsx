import { useRef, useState } from "react";
import type { ReactNode } from "react";

export function FileDropzone({
  accept,
  onFile,
  busy = false,
  help,
  icon = "📁",
}: {
  accept: string;
  onFile: (f: File | null) => void;
  busy?: boolean;
  help?: ReactNode;
  icon?: string;
}) {
  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const pick = (f: File | null) => {
    setFile(f);
    onFile(f);
  };

  return (
    <div>
      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => !busy && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          pick(e.dataTransfer.files?.[0] ?? null);
        }}
      >
        <input
          ref={input}
          type="file"
          accept={accept}
          hidden
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
          disabled={busy}
        />
        <div className="dropzone-icon">{icon}</div>
        <div className="dropzone-text">Drop a file here or click to browse</div>
        {help && <div className="muted small">{help}</div>}
      </div>
      {file && (
        <div className="file-chip">
          <b>{file.name}</b> · {(file.size / 1024 / 1024).toFixed(1)} MB
          <button className="link" onClick={() => pick(null)} aria-label="Remove file">
            ×
          </button>
        </div>
      )}
    </div>
  );
}
