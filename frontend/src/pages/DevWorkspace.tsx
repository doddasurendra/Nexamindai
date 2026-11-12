import { Code2, Search, Star, GitFork, AlertCircle, ExternalLink, FileCode, Loader2 } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, ErrorNotice, Input, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";

interface RepoReport {
  repo: string; name: string; description: string; stars: number; forks: number; open_issues: number;
  default_branch: string; license: string | null; homepage: string; language: string;
  languages: Record<string, number>; file_count: number; sample_files: string[]; readme: string; url: string; latency_ms: number;
}

export default function DevWorkspacePage() {
  const [repo, setRepo] = useState("");
  const [report, setReport] = useState<RepoReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function inspect() {
    if (!repo.trim()) return;
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      const data = await api.post<RepoReport>("/api/dev-workspace/inspect", { repo: repo.trim() });
      setReport(data);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<Code2 className="h-5 w-5" />}
        title="Software Development Workspace"
        subtitle="Inspect any public GitHub repository: structure, languages, README, stars, issues — read-only, no credentials required (60 requests/hour)."
      />
      <Card className="mb-5">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input value={repo} onChange={(e) => setRepo(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void inspect()} placeholder="owner/repository (e.g. fastapi/fastapi)" aria-label="GitHub repository" />
          <Button onClick={() => void inspect()} disabled={busy || !repo.trim()}>
            {busy ? <Spinner label="Inspecting…" /> : <><Search className="h-4 w-4" /> Inspect</>}
          </Button>
        </div>
        {Boolean(error) && <div className="mt-3"><ErrorNotice error={error} /></div>}
      </Card>
      {report && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <a href={report.url} target="_blank" rel="noreferrer" className="font-display text-xl font-semibold hover:text-accent-400">{report.name} <ExternalLink className="inline h-4 w-4" /></a>
                <p className="muted mt-1 text-sm">{report.description || "No description"}</p>
              </div>
              <Badge tone="success">{report.latency_ms} ms</Badge>
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <span className="flex items-center gap-1"><Star className="h-4 w-4 text-amberish-500" /> {report.stars.toLocaleString()}</span>
              <span className="flex items-center gap-1"><GitFork className="h-4 w-4 muted" /> {report.forks.toLocaleString()}</span>
              <span className="flex items-center gap-1"><AlertCircle className="h-4 w-4 muted" /> {report.open_issues} open issues</span>
              <Badge>{report.language || "unknown"}</Badge>
              {report.license && <Badge>{report.license}</Badge>}
            </div>
            <h3 className="mt-5 text-xs font-semibold uppercase tracking-wider muted">Languages</h3>
            <div className="mt-2 flex flex-wrap gap-1">{Object.entries(report.languages).map(([lang, bytes]) => <Badge key={lang}>{lang} · {Math.round((bytes as number) / 1024)} KB</Badge>)}</div>
            <h3 className="mt-5 text-xs font-semibold uppercase tracking-wider muted">File structure ({report.file_count} files)</h3>
            <div className="mt-2 max-h-64 overflow-auto rounded-xl border border-soft surface-2 p-3 font-mono text-[11px] leading-6">
              {report.sample_files.slice(0, 60).map((file) => <p key={file}><FileCode className="inline h-3 w-3 muted" /> {file}</p>)}
            </div>
          </Card>
          <Card className="h-fit">
            <h3 className="text-xs font-semibold uppercase tracking-wider muted">README (first 6,000 chars)</h3>
            <pre className="mt-2 max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-xl bg-black/30 p-3 text-[11px] leading-6">{report.readme || "No README found."}</pre>
          </Card>
        </div>
      )}
    </div>
  );
}
