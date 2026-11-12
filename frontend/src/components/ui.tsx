import { clsx } from "clsx";
import { AlertTriangle, Loader2, Sparkles } from "lucide-react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { ApiError } from "../lib/api";

export const cn = clsx;

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  return (
    <button
      className={cn(
        variant === "primary" && "nexa-btn-primary",
        variant === "ghost" && "nexa-btn-ghost",
        variant === "danger" && "nexa-btn-danger",
        className
      )}
      {...props}
    />
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn("nexa-input", props.className)} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn("nexa-input min-h-[92px] resize-y", props.className)} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn("nexa-input", props.className)} />;
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("nexa-card p-5", className)}>{children}</div>;
}

export function PageHeader({
  title,
  subtitle,
  actions,
  icon
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="grid h-11 w-11 place-items-center rounded-2xl border border-soft surface-2 text-accent-400">
            {icon}
          </div>
        )}
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="muted mt-1 max-w-2xl text-sm">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "success" | "warn" | "danger" }) {
  const tones = {
    default: "border-soft muted",
    success: "border-mint-500/30 text-mint-500 bg-mint-500/10",
    warn: "border-amberish-500/30 text-amberish-500 bg-amberish-500/10",
    danger: "border-red-500/30 text-red-400 bg-red-500/10"
  };
  return <span className={cn("nexa-chip", tones[tone])}>{children}</span>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm muted">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label ?? "Working…"}
    </div>
  );
}

export function Empty({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="grid place-items-center rounded-2xl border border-dashed border-soft px-6 py-14 text-center">
      <div className="mb-3 grid h-11 w-11 place-items-center rounded-2xl bg-accent-500/10 text-accent-400">
        <Sparkles className="h-5 w-5" />
      </div>
      <p className="font-medium">{title}</p>
      {hint && <p className="muted mt-1 max-w-md text-sm">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  const apiError = error instanceof ApiError ? error : null;
  const message = error instanceof Error ? error.message : String(error ?? "Something went wrong");
  const integration = apiError?.code === "integration_not_configured";
  return (
    <div
      role="alert"
      className={cn(
        "rounded-2xl border px-4 py-3 text-sm",
        integration ? "border-amberish-500/30 bg-amberish-500/10" : "border-red-500/30 bg-red-500/10"
      )}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className={cn("mt-0.5 h-4 w-4", integration ? "text-amberish-500" : "text-red-400")} />
        <div>
          <p className="font-medium">{message}</p>
          {integration && apiError?.envVar && (
            <p className="muted mt-1 text-xs">
              Configure <code className="rounded bg-black/20 px-1">{apiError.envVar}</code> on the backend and restart the API.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">{label}</span>
      {children}
      {hint && <span className="muted mt-1 block text-xs">{hint}</span>}
    </label>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className={cn("nexa-card max-h-[88vh] w-full overflow-auto p-6 animate-fadeup", wide ? "max-w-3xl" : "max-w-lg")}>
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="font-display text-lg font-semibold">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close">
            Close
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-2xl border border-soft surface-2 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-wider muted">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
      {hint && <p className="muted mt-0.5 text-xs">{hint}</p>}
    </div>
  );
}
