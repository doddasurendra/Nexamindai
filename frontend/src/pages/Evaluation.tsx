import { Gauge, Plus, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Spinner, Stat, Textarea, cn } from "../components/ui";
import { api } from "../lib/api";
import type { EvalDataset, EvalRun } from "../lib/types";

const SAMPLE = JSON.stringify(
  [
    { question: "What is the capital of France?", expected: "Paris" },
    { question: "Which HTTP header carries a bearer token?", expected: "Authorization" }
  ],
  null,
  2
);

export default function EvaluationPage() {
  const [datasets, setDatasets] = useState<EvalDataset[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selected, setSelected] = useState<EvalDataset | null>(null);
  const [run, setRun] = useState<EvalRun | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [itemsJson, setItemsJson] = useState(SAMPLE);
  const [model, setModel] = useState("openai/gpt-4o-mini");
  const [compare, setCompare] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function refresh() {
    const [sets, history] = await Promise.all([
      api.get<EvalDataset[]>("/api/evals/datasets"),
      api.get<EvalRun[]>("/api/evals/runs")
    ]);
    setDatasets(sets);
    setRuns(history);
    if (!selected && sets.length) setSelected(sets[0]);
  }

  useEffect(() => {
    void refresh().catch(setError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const dataset = await api.post<EvalDataset>("/api/evals/datasets", { name, items: JSON.parse(itemsJson) });
      setDatasets((current) => [dataset, ...current]);
      setSelected(dataset);
      setCreateOpen(false);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function startRun() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setRun(null);
    try {
      const result = await api.post<EvalRun>("/api/evals/runs", { dataset_id: selected.id, model, max_items: 10 });
      setRun(result);
      setRuns((current) => [result, ...current]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const metrics = run?.metrics ?? runs[0]?.metrics;
  const compared = compare ? runs.find((entry) => String(entry.id) === compare) : null;

  return (
    <div>
      <PageHeader
        icon={<Gauge className="h-5 w-5" />}
        title="AI Evaluation"
        subtitle="Repeatable datasets, real benchmark runs, and measured accuracy, F1, relevance, groundedness, latency and cost. Scores are computed from model output — never invented."
        actions={<Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> New dataset</Button>}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Datasets</h3>
          <div className="space-y-1">
            {datasets.map((dataset) => (
              <button key={dataset.id} onClick={() => setSelected(dataset)} className={cn("w-full rounded-xl px-2 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5", selected?.id === dataset.id && "bg-accent-500/10")}>
                <p className="truncate font-medium">{dataset.name}</p>
                <p className="muted text-[10px]">{dataset.items.length} items</p>
              </button>
            ))}
            {datasets.length === 0 && <p className="muted text-xs">No datasets yet.</p>}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2">
            <Input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Model id" className="max-w-[260px]" />
            <Button onClick={() => void startRun()} disabled={busy || !selected}>
              {busy ? <Spinner label="Running…" /> : <><Play className="h-4 w-4" /> Run benchmark</>}
            </Button>
            {selected && <span className="muted text-xs">{selected.items.length} items · max 10 per run</span>}
          </div>
          {Boolean(error) && <div className="mt-3"><ErrorNotice error={error} /></div>}
          {metrics && (
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Exact match" value={fmt(metrics.accuracy_exact_match)} />
              <Stat label="F1" value={fmt(metrics.f1)} />
              <Stat label="Relevance" value={fmt(metrics.relevance)} />
              <Stat label="Groundedness" value={fmt(metrics.groundedness)} />
              <Stat label="Hallucination" value={fmt(metrics.hallucination_rate)} />
              <Stat label="Latency" value={metrics.avg_latency_ms ? `${metrics.avg_latency_ms} ms` : "—"} />
              <Stat label="Tokens" value={metrics.total_tokens ?? "—"} />
              <Stat label="Cost" value={metrics.total_cost != null ? `$${Number(metrics.total_cost).toFixed(6)}` : "—"} />
            </div>
          )}
        </Card>
      </div>

      {run && (
        <Card className="mt-5">
          <div className="mb-2 flex items-center gap-2">
            <Badge tone={run.status === "completed" ? "success" : "danger"}>{run.status}</Badge>
            <span className="text-sm font-medium">Run #{run.id} · {run.model}</span>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-soft">
                  {["Question", "Expected", "Answer", "EM", "F1", "Relevance", "ms"].map((header) => (
                    <th key={header} className="px-2 py-2 font-semibold">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {run.results.map((row, index) => (
                  <tr key={index} className="border-b border-soft/50">
                    <td className="max-w-[220px] truncate px-2 py-2">{String(row.question)}</td>
                    <td className="max-w-[140px] truncate px-2 py-2">{String(row.expected)}</td>
                    <td className="max-w-[260px] truncate px-2 py-2">{String(row.answer)}</td>
                    <td className="px-2 py-2">{fmt(row.exact_match as number)}</td>
                    <td className="px-2 py-2">{fmt(row.f1 as number)}</td>
                    <td className="px-2 py-2">{fmt(row.relevance as number)}</td>
                    <td className="px-2 py-2">{String(row.latency_ms ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Card className="mt-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider muted">Evaluation history</h3>
          <Select value={compare} onChange={(event) => setCompare(event.target.value)} className="w-auto">
            <option value="">Compare with…</option>
            {runs.map((entry) => <option key={entry.id} value={entry.id}>#{entry.id} {entry.model}</option>)}
          </Select>
        </div>
        <div className="space-y-1">
          {runs.map((entry) => (
            <button key={entry.id} onClick={() => setRun(entry)} className="w-full rounded-xl px-2 py-2 text-left text-xs hover:bg-black/5 dark:hover:bg-white/5">
              #{entry.id} · {entry.model} · {entry.status} · {new Date(entry.created_at).toLocaleString()} · F1 {fmt(entry.metrics.f1)}
            </button>
          ))}
          {runs.length === 0 && <Empty title="No runs yet" hint="Create a dataset and run a benchmark." />}
        </div>
        {compared && (
          <div className="mt-3 rounded-xl border border-soft surface-2 p-3 text-xs">
            <p className="font-medium">Comparison vs run #{compared.id}</p>
            <p className="muted mt-1">
              F1 {fmt(compared.metrics.f1)} · Relevance {fmt(compared.metrics.relevance)} · Latency {String(compared.metrics.avg_latency_ms ?? "—")} ms
            </p>
          </div>
        )}
      </Card>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New evaluation dataset" wide>
        <div className="grid gap-3">
          <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Dataset name" />
          <Textarea value={itemsJson} onChange={(event) => setItemsJson(event.target.value)} rows={10} className="font-mono text-xs" />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={() => void create()} disabled={busy || !name}>Create dataset</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function fmt(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(3);
}
