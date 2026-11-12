import { Terminal, Play, CheckCircle2, XCircle, Loader2, Bot, Sparkles } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, ErrorNotice, PageHeader, Textarea, cn } from "../components/ui";
import { api } from "../lib/api";
import { Markdown } from "../components/Markdown";

interface PlanStep { id: number; task: string; agent: string }
interface StepResult { id: number; task: string; agent: string; status: string; output: string; execution_id: number | null }
interface CommandResult { objective: string; plan: PlanStep[]; results: StepResult[]; final: string; duration_ms: number; status: string }

export default function CommandCenterPage() {
  const [objective, setObjective] = useState("");
  const [result, setResult] = useState<CommandResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run() {
    if (!objective.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.post<CommandResult>("/api/command-center/execute", { objective: objective.trim() });
      setResult(data);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<Terminal className="h-5 w-5" />}
        title="AI Command Center"
        subtitle="Give NexaMind a large objective. It decomposes the task, assigns specialized agents, executes them, verifies results and returns one unified deliverable."
      />
      <Card className="mb-5">
        <Textarea
          value={objective}
          onChange={(event) => setObjective(event.target.value)}
          placeholder="e.g. Research quantum computing applications in pharmaceutical drug discovery, compare the latest research papers, find GitHub projects and prepare a technical implementation roadmap."
          rows={4}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button onClick={() => void run()} disabled={busy || !objective.trim()}>
            {busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Executing…</> : <><Play className="h-4 w-4" /> Execute objective</>}
          </Button>
          <span className="muted text-xs">Requires OPENROUTER_API_KEY. Each subtask runs a real agent with real tools.</span>
        </div>
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      {result && (
        <div className="space-y-4">
          <Card>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={result.status === "completed" ? "success" : "warn"}>{result.status}</Badge>
              <span className="nexa-chip">{result.results.length} steps</span>
              <span className="nexa-chip">{(result.duration_ms / 1000).toFixed(1)}s</span>
            </div>
            <h3 className="mt-3 text-xs font-semibold uppercase tracking-wider muted">Execution plan</h3>
            <ol className="mt-2 space-y-2">
              {result.plan.map((step) => {
                const res = result.results.find((r) => r.id === step.id);
                return (
                  <li key={step.id} className="flex items-start gap-3 rounded-xl border border-soft surface-2 p-3">
                    <span className={cn(
                      "mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-lg text-[11px] font-bold",
                      res?.status === "failed" ? "bg-red-500/20 text-red-400" : "bg-accent-500/15 text-accent-400"
                    )}>
                      {res?.status === "failed" ? <XCircle className="h-4 w-4" /> : step.id}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{step.task}</p>
                      <p className="muted mt-0.5 flex items-center gap-1 text-[11px]"><Bot className="h-3 w-3" /> {step.agent}</p>
                    </div>
                    {res && res.status === "failed" && <Badge tone="danger">failed</Badge>}
                  </li>
                );
              })}
            </ol>
          </Card>

          <Card>
            <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider muted"><Sparkles className="h-3.5 w-3.5" /> Subtask outputs</h3>
            <div className="mt-3 space-y-3">
              {result.results.map((res) => (
                <details key={res.id} className="rounded-xl border border-soft surface-2 p-3">
                  <summary className="cursor-pointer text-sm font-medium">
                    Step {res.id} · {res.agent} · {res.status}
                  </summary>
                  <div className="mt-2 max-h-64 overflow-auto rounded-lg bg-black/30 p-3 text-xs leading-6 whitespace-pre-wrap">{res.output}</div>
                </details>
              ))}
            </div>
          </Card>

          <Card>
            <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider muted"><CheckCircle2 className="h-3.5 w-3.5" /> Final deliverable</h3>
            <div className="mt-3"><Markdown>{result.final || "No final synthesis generated."}</Markdown></div>
          </Card>
        </div>
      )}
    </div>
  );
}
