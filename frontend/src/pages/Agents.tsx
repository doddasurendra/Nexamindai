import { Bot, ShieldAlert, Sparkles, Stethoscope, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Markdown } from "../components/Markdown";
import { Badge, Button, Card, Empty, ErrorNotice, Input, PageHeader, Select, Spinner, Textarea, cn } from "../components/ui";
import { api } from "../lib/api";
import type { Agent, AgentExecution } from "../lib/types";

const DOMAIN_ICONS: Record<string, typeof Bot> = {
  quantum: Sparkles,
  healthcare: Stethoscope,
  finance: TrendingUp,
  cybersecurity: ShieldAlert
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [selected, setSelected] = useState<Agent | null>(null);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("");
  const [useTools, setUseTools] = useState(true);
  const [active, setActive] = useState<AgentExecution | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get<Agent[]>("/api/agents").then((data) => {
      setAgents(data);
      setSelected(data[0] ?? null);
    }).catch(setError);
    api.get<AgentExecution[]>("/api/agents/executions").then(setExecutions).catch(() => undefined);
  }, []);

  async function run() {
    if (!input.trim()) return;
    setBusy(true);
    setError(null);
    setActive(null);
    try {
      const execution = await api.post<AgentExecution>("/api/agents/run", {
        agent_slug: selected?.slug,
        input: input.trim(),
        model: model || undefined,
        use_tools: useTools
      });
      setActive(execution);
      setExecutions((current) => [execution, ...current]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<Bot className="h-5 w-5" />}
        title="AI Agents"
        subtitle="Specialized agents with independent instructions, tool boundaries and execution logs. The orchestrator routes ambiguous requests to the right domain."
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {agents.map((agent) => {
          const Icon = DOMAIN_ICONS[agent.domain] ?? Bot;
          return (
            <button
              key={agent.id}
              onClick={() => setSelected(agent)}
              className={cn(
                "nexa-card p-4 text-left transition hover:-translate-y-0.5",
                selected?.id === agent.id && "ring-2 ring-accent-500/50"
              )}
            >
              <div className="mb-2 flex items-center justify-between">
                <div className="grid h-9 w-9 place-items-center rounded-xl bg-accent-500/10 text-accent-400">
                  <Icon className="h-4 w-4" />
                </div>
                <Badge tone={agent.enabled ? "success" : "danger"}>{agent.enabled ? "ready" : "off"}</Badge>
              </div>
              <p className="font-display text-sm font-semibold">{agent.name}</p>
              <p className="muted mt-1 line-clamp-3 text-xs">{agent.description}</p>
              <p className="muted mt-2 text-[10px]">tools: {agent.tools.join(", ") || "none"}</p>
            </button>
          );
        })}
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <div className="flex flex-wrap items-center gap-2">
            <Select value={selected?.slug ?? ""} onChange={(event) => setSelected(agents.find((a) => a.slug === event.target.value) ?? null)} className="w-auto">
              {agents.map((agent) => (
                <option key={agent.slug} value={agent.slug}>
                  {agent.name}
                </option>
              ))}
            </Select>
            <Input value={model} onChange={(event) => setModel(event.target.value)} placeholder="model override (optional)" className="max-w-[240px]" />
            <label className="flex items-center gap-2 text-xs muted">
              <input type="checkbox" checked={useTools} onChange={(event) => setUseTools(event.target.checked)} />
              allow tools
            </label>
          </div>
          <Textarea
            className="mt-3"
            rows={4}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Give the agent a task…"
          />
          <div className="mt-3 flex items-center gap-2">
            <Button onClick={() => void run()} disabled={busy || !input.trim()}>
              {busy ? <Spinner label="Running…" /> : "Run agent"}
            </Button>
            {selected && <span className="muted text-xs">{selected.restrictions.join(" · ")}</span>}
          </div>
          {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
          {active && (
            <div className="mt-5 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={active.status === "completed" ? "success" : active.status === "refused" ? "warn" : "danger"}>{active.status}</Badge>
                <span className="nexa-chip">{active.model}</span>
                <span className="nexa-chip">{active.tokens_in + active.tokens_out} tokens</span>
                <span className="nexa-chip">{active.latency_ms} ms</span>
                <span className="nexa-chip">${active.cost.toFixed(6)}</span>
              </div>
              <div className="rounded-2xl border border-soft surface-2 p-4">
                <Markdown>{active.output || active.error || "No output."}</Markdown>
              </div>
              <details>
                <summary className="cursor-pointer text-xs font-medium">Execution log ({active.log.length})</summary>
                <pre className="mt-2 overflow-auto rounded-xl bg-black/30 p-3 text-[11px]">{JSON.stringify(active.log, null, 2)}</pre>
              </details>
            </div>
          )}
        </Card>

        <Card className="h-fit">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Recent executions</h3>
          <div className="space-y-2">
            {executions.slice(0, 12).map((execution) => (
              <button
                key={execution.id}
                onClick={() => setActive(execution)}
                className="w-full rounded-xl px-2 py-2 text-left text-xs hover:bg-black/5 dark:hover:bg-white/5"
              >
                <p className="line-clamp-2">{execution.input}</p>
                <p className="muted mt-1">
                  #{execution.id} · {execution.status} · {new Date(execution.created_at).toLocaleString()}
                </p>
              </button>
            ))}
            {executions.length === 0 && <Empty title="No executions" hint="Run an agent to see logs." />}
          </div>
        </Card>
      </div>
    </div>
  );
}
