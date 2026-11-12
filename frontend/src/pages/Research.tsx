import { FlaskConical } from "lucide-react";
import { useEffect, useState } from "react";
import { Markdown } from "../components/Markdown";
import { Button, Card, ErrorNotice, PageHeader, Select, Spinner, Textarea } from "../components/ui";
import { api } from "../lib/api";
import type { ResearchRun } from "../lib/types";

export default function ResearchPage() {
  const [question, setQuestion] = useState("");
  const [depth, setDepth] = useState("standard");
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [active, setActive] = useState<ResearchRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get<ResearchRun[]>("/api/research").then(setRuns).catch(() => undefined);
  }, []);

  async function run() {
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.post<ResearchRun>("/api/research", { question: question.trim(), depth });
      setActive(result);
      setRuns((current) => [result, ...current]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<FlaskConical className="h-5 w-5" />}
        title="Deep Research"
        subtitle="Plans sub-questions, searches multiple sources, retrieves pages, compares findings and writes a cited report with retrieval timestamps."
      />
      <Card className="mb-6">
        <Textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What decision are you trying to make? e.g. Compare pgvector vs Qdrant for a 5M-vector RAG workload in 2025."
          rows={3}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Select value={depth} onChange={(event) => setDepth(event.target.value)} className="w-auto">
            <option value="quick">Quick (2 sources / subquestion)</option>
            <option value="standard">Standard (3 sources + page fetch)</option>
            <option value="deep">Deep (5 sources + page fetch)</option>
          </Select>
          <Button onClick={() => void run()} disabled={busy || !question.trim()}>
            {busy ? <Spinner label="Researching…" /> : "Run research"}
          </Button>
          <span className="muted text-xs">Requires OPENROUTER_API_KEY + TAVILY_API_KEY.</span>
        </div>
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-fit">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">History</h3>
          <div className="space-y-1">
            {runs.map((item) => (
              <button
                key={item.id}
                onClick={() => setActive(item)}
                className="w-full rounded-xl px-2 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5"
              >
                <p className="line-clamp-2">{item.question}</p>
                <p className="muted mt-1 text-[10px]">
                  {item.status} · {new Date(item.created_at).toLocaleString()}
                </p>
              </button>
            ))}
            {runs.length === 0 && <p className="muted text-xs">No research runs yet.</p>}
          </div>
        </Card>

        <Card>
          {!active && <p className="muted text-sm">Select a run or start a new one.</p>}
          {active && (
            <div>
              <h2 className="font-display text-xl font-semibold">{active.question}</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="nexa-chip">status: {active.status}</span>
                <span className="nexa-chip">{active.sources.length} sources</span>
              </div>
              {active.plan.length > 0 && (
                <div className="mt-4 rounded-xl border border-soft surface-2 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider muted">Research plan</p>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                    {active.plan.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
              <div className="mt-4">
                <Markdown>{active.report || "No report generated."}</Markdown>
              </div>
              {active.sources.length > 0 && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm font-medium">Sources ({active.sources.length})</summary>
                  <ul className="mt-2 space-y-1 text-xs">
                    {active.sources.map((source) => (
                      <li key={source.url}>
                        <a className="text-accent-500 hover:underline" href={source.url} target="_blank" rel="noreferrer">
                          {source.title || source.url}
                        </a>
                        {source.retrieved_at && <span className="muted"> · {new Date(source.retrieved_at).toLocaleString()}</span>}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
