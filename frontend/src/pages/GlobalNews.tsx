import { Newspaper, Search, ExternalLink, Bookmark, Sparkles, RefreshCw, MapPin } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, ErrorNotice, Input, PageHeader, Select, Spinner, cn } from "../components/ui";
import { api } from "../lib/api";

interface NewsItem {
  title: string;
  url: string;
  description?: string;
  source: string;
  published?: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  world: "World", technology: "Technology", science: "Science", business: "Business",
  india: "India", ai: "AI & Tech", health: "Health", sports: "Sports"
};

const COUNTRIES = [
  { code: "", label: "All locations" },
  { code: "in", label: "India" },
  { code: "us", label: "United States" },
  { code: "gb", label: "United Kingdom" },
  { code: "cn", label: "China" },
  { code: "jp", label: "Japan" },
  { code: "de", label: "Germany" },
  { code: "fr", label: "France" },
  { code: "au", label: "Australia" },
  { code: "ca", label: "Canada" },
  { code: "sg", label: "Singapore" },
  { code: "ae", label: "UAE" },
];

export default function GlobalNewsPage() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [category, setCategory] = useState("world");
  const [country, setCountry] = useState("");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<{ answer: string; results: { title: string; url: string; content: string }[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [summaries, setSummaries] = useState<Record<string, string>>({});
  const [summarizing, setSummarizing] = useState<string | null>(null);
  const [bookmarks, setBookmarks] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("nexamind_news_bookmarks") || "[]"); } catch { return []; }
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<NewsItem[]>(`/api/news/headlines?category=${category}&limit=15`);
      setItems(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [category]);

  async function search() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<{ answer: string; results: { title: string; url: string; content: string }[] }>(
        `/api/news/search?q=${encodeURIComponent(query.trim())}&limit=8`
      );
      setSearchResults(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  async function summarize(item: NewsItem) {
    const key = item.url;
    setSummarizing(key);
    try {
      const result = await api.post<{ summary: string }>("/api/news/summarize", {
        title: item.title, url: item.url, content: item.description || ""
      });
      setSummaries((prev) => ({ ...prev, [key]: result.summary }));
    } catch {
      setSummaries((prev) => ({ ...prev, [key]: "Summary unavailable." }));
    } finally {
      setSummarizing(null);
    }
  }

  function toggleBookmark(url: string) {
    setBookmarks((prev) => {
      const next = prev.includes(url) ? prev.filter((u) => u !== url) : [...prev, url];
      localStorage.setItem("nexamind_news_bookmarks", JSON.stringify(next));
      return next;
    });
  }

  const breaking = items[0];
  const headlines = items.slice(1);

  return (
    <div>
      <PageHeader
        icon={<Newspaper className="h-5 w-5" />}
        title="Global News"
        subtitle="Live headlines from BBC and Al Jazeera RSS feeds, plus AI-powered search and summaries via Tavily. Bookmarks are stored locally."
        actions={
          <Button variant="ghost" onClick={() => void load()}>
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} /> Refresh
          </Button>
        }
      />

      {/* Breaking banner */}
      {breaking && (
        <Card className="mb-5 border-accent-500/30 bg-accent-500/5">
          <div className="flex items-start gap-3">
            <div className="mt-1 animate-pulse rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold uppercase text-white">Breaking</div>
            <div className="min-w-0 flex-1">
              <a href={breaking.url} target="_blank" rel="noreferrer" className="text-lg font-semibold leading-snug hover:text-accent-400">
                {breaking.title}
              </a>
              <p className="muted mt-1 text-xs">{breaking.source}{breaking.published ? ` · ${new Date(breaking.published).toLocaleString()}` : ""}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => void summarize(breaking)} disabled={summarizing === breaking.url}>
                  <Sparkles className="h-3 w-3" /> {summarizing === breaking.url ? "Summarizing…" : "AI summary"}
                </Button>
                <button onClick={() => toggleBookmark(breaking.url)} className="rounded-lg border border-soft p-1.5 hover:border-accent-500/50" title="Bookmark">
                  <Bookmark className={cn("h-4 w-4", bookmarks.includes(breaking.url) && "fill-accent-400 text-accent-400")} />
                </button>
              </div>
              {summaries[breaking.url] && <p className="mt-3 rounded-xl border border-soft surface-2 p-3 text-sm leading-6">{summaries[breaking.url]}</p>}
            </div>
          </div>
        </Card>
      )}

      {/* Controls */}
      <Card className="mb-5">
        <div className="flex flex-wrap gap-2">
          <Select value={category} onChange={(event) => setCategory(event.target.value)} className="w-auto" aria-label="Category">
            {Object.entries(CATEGORY_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </Select>
          <div className="relative">
            <MapPin className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
            <Select value={country} onChange={(event) => setCountry(event.target.value)} className="w-auto pl-9" aria-label="Country">
              {COUNTRIES.map((c) => <option key={c.code || "all"} value={c.code}>{c.label}</option>)}
            </Select>
          </div>
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
            <Input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void search()} placeholder="Search news…" className="pl-9" />
          </div>
          <Button onClick={() => void search()} disabled={!query.trim()}><Search className="h-4 w-4" /> Search</Button>
        </div>
        {country && <p className="muted mt-2 text-[11px]">Location filter: {COUNTRIES.find((c) => c.code === country)?.label}. Headlines are sourced from BBC/Al Jazeera world feeds.</p>}
      </Card>

      {Boolean(error) && <div className="mb-4"><ErrorNotice error={error} /></div>}

      {/* Search results */}
      {searchResults && (
        <Card className="mb-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider muted">Search results for “{query}”</h3>
            <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => setSearchResults(null)}>Clear</Button>
          </div>
          {searchResults.answer && <p className="rounded-xl border border-soft surface-2 p-3 text-sm leading-6">{searchResults.answer}</p>}
          <div className="mt-3 space-y-2">
            {searchResults.results.map((item, index) => (
              <a key={index} href={item.url} target="_blank" rel="noreferrer" className="block rounded-xl border border-soft p-3 hover:border-accent-500/40">
                <p className="text-sm font-medium hover:text-accent-400">{item.title}</p>
                <p className="muted mt-1 line-clamp-2 text-xs">{item.content}</p>
              </a>
            ))}
          </div>
        </Card>
      )}

      {/* Headlines grid */}
      {loading && items.length === 0 ? (
        <Spinner label="Fetching headlines…" />
      ) : headlines.length === 0 && !searchResults ? (
        <Empty title="No headlines" hint="Try another category or search." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {headlines.map((item) => (
            <Card key={item.url} className="flex flex-col p-4">
              <a href={item.url} target="_blank" rel="noreferrer" className="text-sm font-semibold leading-snug hover:text-accent-400">
                {item.title}
              </a>
              <p className="muted mt-1 line-clamp-2 text-xs">{item.description || ""}</p>
              <p className="muted mt-1 text-[10px]">{item.source}{item.published ? ` · ${new Date(item.published).toLocaleString()}` : ""}</p>
              <div className="mt-auto flex items-center justify-between pt-3">
                <div className="flex gap-1">
                  <button onClick={() => void summarize(item)} disabled={summarizing === item.url} className="rounded-lg border border-soft p-1.5 hover:border-accent-500/50" title="AI summary">
                    <Sparkles className="h-4 w-4" />
                  </button>
                  <button onClick={() => toggleBookmark(item.url)} className="rounded-lg border border-soft p-1.5 hover:border-accent-500/50" title="Bookmark">
                    <Bookmark className={cn("h-4 w-4", bookmarks.includes(item.url) && "fill-accent-400 text-accent-400")} />
                  </button>
                </div>
                <a href={item.url} target="_blank" rel="noreferrer" className="text-[11px] text-accent-400 hover:underline flex items-center gap-1">
                  Read <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              {summaries[item.url] && <p className="mt-2 rounded-xl border border-soft surface-2 p-2 text-xs leading-5">{summaries[item.url]}</p>}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
