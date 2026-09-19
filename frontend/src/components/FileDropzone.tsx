import { useRef, useState } from "react";
import { fmtBytes } from "../utils";

export function FileDropzone({
  onFile,
  accept,
  label,
  sub,
  busy,
  icon = "📁",
  help,
}: {
  onFile: (f: File) => void;
  accept?: string;
  label?: string;
  sub?: string;
  busy?: boolean;
  icon?: string;
  help?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handle = (file: File | undefined) => {
    if (file) {
      setSelectedFile(file);
      onFile(file);
    }
  };

  const clearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (ref.current) ref.current.value = "";
  };

  return (
    <div>
      <div
        className={`dropzone${over ? " over" : ""}${busy ? " busy" : ""}`}
        onClick={() => !busy && ref.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!busy) setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (!busy) handle(e.dataTransfer.files[0]);
        }}
      >
        <div className="dropzone-icon">{busy ? "⏳" : icon}</div>
        <div className="dropzone-label">
          {busy ? "Processing file..." : (label ?? "Drop a file or click to browse")}
        </div>
        <div className="dropzone-sub">
          {sub ?? (accept ? accept.replace(/,/g, " ·") : "Any file type")}
        </div>
        {help && <div className="dropzone-help">{help}</div>}
        <input
          ref={ref}
          type="file"
          accept={accept}
          disabled={busy}
          style={{ display: "none" }}
          onChange={(e) => handle(e.target.files?.[0])}
        />
      </div>

      {selectedFile && (
        <div className="dropzone-file-selected">
          <span>📄</span>
          <span className="dropzone-file-name" title={selectedFile.name}>
            {selectedFile.name}
          </span>
          <span className="dropzone-file-size">({fmtBytes(selectedFile.size)})</span>
          {!busy && (
            <button
              type="button"
              className="dropzone-file-clear"
              onClick={clearFile}
              title="Remove file"
            >
              ✕
            </button>
          )}
        </div>
      )}
    </div>
  );
}
