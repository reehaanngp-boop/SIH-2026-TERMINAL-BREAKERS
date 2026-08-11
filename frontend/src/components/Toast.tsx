import { useCallback, useRef, useState } from "react";

export type ToastTone = "info" | "success" | "error";

export interface ToastMsg {
  id: number;
  message: string;
  tone: ToastTone;
}

/** Simple push-based toast manager. Use `const { toasts, push } = useToasts()`. */
export function useToasts() {
  const [toasts, setToasts] = useState<ToastMsg[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((message: string, tone: ToastTone = "info") => {
    const id = nextId.current++;
    setToasts((ts) => [...ts, { id, message, tone }]);
    window.setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== id)), 4200);
  }, []);

  return { toasts, push, dismiss };
}

export function ToastStack({ toasts, onDismiss }: { toasts: ToastMsg[]; onDismiss: (id: number) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.tone}`} onClick={() => onDismiss(t.id)} role="button">
          {t.message}
        </div>
      ))}
    </div>
  );
}
