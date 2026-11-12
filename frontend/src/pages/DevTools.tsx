import { Activity, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, ErrorNotice, PageHeader, Spinner, Stat } from "../components/ui";
import { api } from "../lib/api";
import type { Integration, Usage } from "../lib/types";

interface Health {
  status: string;
  time: number;
  checks: Record<string, string>;
}

export default function DevToolsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null);
  const [logs, setLogs] = useState<{ time: string; level: string; logger: string; message: string }[]>([]);
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    const results = await Promise.allSettled([
      api.get<Health>("/api/devops/health"),
      api.get<Integration[]>("/api/devops/integrations"),
      api.get<Usage>("/api/devops/usage"),
      api.get<Record<string, number>>("/api/devops/metrics"),
      api.get<{ time: string; level: string; logger: string; message: string }[]>("/api/devops/logs"),
      api.get<Record<string, unknown>>("/api/devops/config")
    ]);
    if (results[0].status === "fulfilled") setHealth(results[0].value);
    if (results[1].status === "fulfilled") setIntegrations(results[1].value);
    if (results[2].status === "fulfilled") setUsage(results[2].value);
    if (results[3].status === "fulfilled") setMetrics(results[3].value);
    if (results[4].status === "fulfilled") setLogs(results[4].value);
    else setLogs([]);
    if (results[5].status === "fulfilled") setConfig(results[5].value);
    else setConfig(null);
    if (results[0].status === "rejected") setError(results[0].reason);
    setBusy(false);
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div>
      <PageHeader
        icon={<Activity className="h-5 w-5" />}
        title="Developer Tools"
        subtitle="Health checks, provider status, measured usage, metrics and redacted configuration. Secret values are never displayed here."
        actions={<Button variant="ghost" onClick={() => void load()} disabled={busy}><RefreshCw className={busy ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh</Button>}
      />
      {Boolean(error) && <div className="mb-4"><ErrorNotice error={error} /></div>}
      {busy && !health && <Spinner label="Loading workspace health…" />}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat label="API" value={health?.status ?? "—"} hint={health ? new Date(health.time * 1000).toLocaleTimeString() : ""} />
        <Stat label="Requests" value={usage?.requests ?? "—"} hint="your account" />
        <Stat label="Tokens" value={usage ? usage.tokens_in + usage.tokens_out : "—"} hint={`in ${usage?.tokens_in ?? 0} / out ${usage?.tokens_out ?? 0}`} />
        <Stat label="Cost" value={usage ? `$${usage.cost.toFixed(6)}` : "—"} hint="OpenRouter reported" />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider muted"><ShieldCheck className="h-3.5 w-3.5" /> Health checks</h3>
          <div className="space-y-2">
            {health && Object.entries(health.checks).map(([name, value]) => (
              <div key={name} className="flex items-center justify-between rounded-xl border border-soft surface-2 px-3 py-2 text-sm">
                <span>{name}</span>
                <Badge tone={value === "ok" || value === "configured" ? "success" : value.includes("error") ? "danger" : "warn"}>{value}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Integrations</h3>
          <div className="space-y-2">
            {integrations.map((integration) => (
              <div key={integration.provider} className="flex items-center justify-between rounded-xl border border-soft surface-2 px-3 py-2 text-sm">
                <div>
                  <p>{integration.provider}</p>
                  <p className="muted text-[10px]">{integration.env}</p>
                </div>
                <Badge tone={integration.configured ? "success" : "warn"}>{integration.configured ? "configured" : "missing"}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Workspace metrics</h3>
          <div className="grid grid-cols-2 gap-2">
            {metrics && Object.entries(metrics).map(([key, value]) => (
              <div key={key} className="rounded-xl border border-soft surface-2 px-3 py-2">
                <p className="muted text-[10px]">{key.replaceAll("_", " ")}</p>
                <p className="text-lg font-semibold">{value}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Redacted configuration</h3>
          {config ? (
            <pre className="max-h-64 overflow-auto rounded-xl bg-black/30 p-3 text-[11px]">{JSON.stringify(config, null, 2)}</pre>
          ) : (
            <p className="muted text-sm">Administrator role required to view configuration.</p>
          )}
        </Card>
      </div>

      <Card className="mt-5">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Backend logs (last 200, admin)</h3>
        <div className="max-h-72 space-y-1 overflow-auto font-mono text-[11px]">
          {logs.map((log, index) => (
            <div key={index} className="flex gap-2">
              <span className="muted">{log.time}</span>
              <span className={log.level === "ERROR" ? "text-red-400" : "text-accent-400"}>{log.level}</span>
              <span className="muted">{log.logger}</span>
              <span className="min-w-0 flex-1 break-all">{log.message}</span>
            </div>
          ))}
          {logs.length === 0 && <p className="muted">No logs available (admin role required).</p>}
        </div>
      </Card>
    </div>
  );
}
