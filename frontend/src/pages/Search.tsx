import { Search as SearchIcon } from "lucide-react";
import { useState } from "react";
import { Markdown } from "../components/Markdown";
import { Button, Card, ErrorNotice, Input, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { SearchResponse } from "../lib/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.post<SearchResponse>("/api/search", { query: query.trim(), max_results: 6 }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<SearchIcon className="h-5 w-5" />}
        title="Web Search"
        subtitle="Genuine Tavily search with extracted snippets, source links and a synthesized answer. If no key is configured, the integration state is shown instead of fabricated results."
      />
      <Card className="mb-6">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && void run()}
            placeholder="Ask a question that needs current sources…"
            aria-label="Search query"
          />
          <Button onClick={() => void run()} disabled={busy || !query.trim()}>
            {busy ? <Spinner label="Searching…" /> : "Search"}
          </Button>
        </div>
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      {result && (
        <div className="space-y-4">
          <Card>
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs muted">
              <span className="nexa-chip">provider: {result.provider}</span>
              <span className="nexa-chip">{result.results.length} results</span>
              <span className="nexa-chip">{result.latency_ms} ms</span>
            </div>
            {result.answer && <Markdown>{result.answer}</Markdown>}
          </Card>
          <div className="space-y-3">
            {result.results.map((item) => (
              <Card key={item.url}>
                <a href={item.url} target="_blank" rel="noreferrer" className="font-medium text-accent-500 hover:underline">
                  {item.title || item.url}
                </a>
                <p className="muted mt-1 break-all text-xs">{item.url}</p>
                <p className="mt-2 text-sm leading-6">{item.content}</p>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
