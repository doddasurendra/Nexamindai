import { Search, Globe, ExternalLink, Filter } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, ErrorNotice, Input, PageHeader, Select, Spinner, Stat, cn } from "../components/ui";
import { api } from "../lib/api";

interface APISummary {
  total: number;
  items: APIListItem[];
}

interface APIListItem {
  id: number;
  name: string;
  description: string;
  category: string;
  auth_type: string;
  https: string;
  cors: string;
  pricing: string;
  status: string;
  docs_url: string;
  health: string;
  url?: string;
}

interface Category {
  name: string;
  api_count: number;
  synced_at: string | null;
}

interface MCPServer {
  id: number;
  name: string;
  description: string;
  auth: string;
  transport: string;
  install_links: string;
  status: string;
  url?: string;
}

export default function ApiUniversePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [apis, setApis] = useState<APIListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [featured, setFeatured] = useState<APIListItem[]>([]);
  const [mcps, setMcps] = useState<MCPServer[]>([]);
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [authFilter, setAuthFilter] = useState("");
  const [activeSection, setActiveSection] = useState<"all" | "categories" | "featured" | "mcps" | "apis">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, string>>({});

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.allSettled([
      api.get<Category[]>("/api/apis/categories"),
      api.get<APISummary>("/api/apis/apis?limit=12"),
      api.get<APIListItem[]>("/api/apis/featured"),
      api.get<MCPServer[]>("/api/apis/mcp-servers"),
    ]).then((results) => {
      if (!active) return;
      const [cats, apisRes, feat, mcpList] = results;
      if (cats.status === "fulfilled") setCategories(cats.value);
      if (apisRes.status === "fulfilled") { setApis(apisRes.value.items); setTotal(apisRes.value.total); }
      if (feat.status === "fulfilled") setFeatured(feat.value);
      if (mcpList.status === "fulfilled") setMcps(mcpList.value);
      setLoading(false);
    }).catch(setError);
    return () => { active = false; };
  }, []);

  async function loadApis() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "50");
      if (category) params.set("category", category);
      if (query) params.set("query", query);
      if (authFilter) params.set("auth_type", authFilter);
      const data = await api.get<APISummary>(`/api/apis/apis?${params.toString()}`);
      setApis(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => { if (category || query || authFilter) loadApis(); }, 300);
    return () => clearTimeout(timer);
  }, [category, query, authFilter]);

  async function testApi(apiId: number) {
    setTesting(apiId);
    setTestResult((prev) => ({ ...prev, [apiId]: "Testing…" }));
    try {
      const result = await api.post<{ status: string; data?: unknown; error?: string; ms: number }>(`/api/apis/test/${apiId}`);
      setTestResult((prev) => ({ ...prev, [apiId]: result.status === "ok" ? `OK (${result.ms}ms)` : `FAIL: ${result.error || result.status}` }));
    } catch (err) {
      setTestResult((prev) => ({ ...prev, [apiId]: "Error" }));
    } finally {
      setTesting(null);
    }
  }

  const FREE_NO_AUTH = apis.filter((a) => a.auth_type === "none" && (a.pricing === "free" || a.pricing === "unknown"));

  return (
    <div>
      <PageHeader
        icon={<Globe className="h-5 w-5" />}
        title="API Universe"
        subtitle="Browse 2,359 APIs from the public-apis repository. Filter by category, authentication, HTTPS, CORS, and pricing. Each entry shows live catalogue data from the upstream repo."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone="success">Total: {total}</Badge>
            <Badge>Free no-auth: {FREE_NO_AUTH.length}</Badge>
            <Badge tone="success">MCP: {mcps.length}</Badge>
          </div>
        }
      />

      {Boolean(error) && <div className="mb-4"><ErrorNotice error={error} /></div>}

      <div className="flex flex-wrap gap-2 mb-5">
        {([
          ["all", "Overview", ""],
          ["apis", "All APIs", ""],
          ["featured", "Featured", ""],
          ["categories", "Categories", ""],
          ["mcps", "MCP Servers", ""],
        ] as [typeof activeSection, string, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveSection(key)}
            className={cn(
              "rounded-xl border px-3 py-2 text-xs font-semibold transition",
              activeSection === key ? "border-accent-500/50 bg-accent-500/10 text-accent-400" : "border-soft bg-surface text-muted"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <Card className="mb-5">
        <div className="flex flex-wrap gap-2">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-3 h-4 w-4 muted" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search APIs…" className="pl-9" />
          </div>
          <Select value={category} onChange={(e) => setCategory(e.target.value)} className="w-auto">
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.name} value={c.name}>{c.name} ({c.api_count})</option>
            ))}
          </Select>
          <Select value={authFilter} onChange={(e) => setAuthFilter(e.target.value)} className="w-auto">
            <option value="">All auth</option>
            <option value="none">No auth (free)</option>
            <option value="apiKey">API Key</option>
            <option value="OAuth">OAuth</option>
          </Select>
          <Button variant="ghost" onClick={() => { setCategory(""); setQuery(""); setAuthFilter(""); }}>
            <Filter className="h-4 w-4" /> Reset
          </Button>
        </div>
      </Card>

      {/* API list */}
      {activeSection === "all" || activeSection === "apis" ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {apis.map((api) => (
            <Card key={api.id} className="flex flex-col p-4 hover:-translate-y-0.5 transition">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold truncate">{api.name}</h3>
                <Badge tone={api.https === "Yes" ? "success" : "warn"}>{api.auth_type}</Badge>
              </div>
              <p className="muted mt-1 line-clamp-2 text-xs">{api.description}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                <Badge tone={api.pricing === "free" ? "success" : "warn"}>{api.pricing}</Badge>
                <Badge>{api.https === "Yes" ? "HTTPS" : "HTTP"}</Badge>
                <Badge>{api.cors === "Yes" ? "CORS" : "CORS?"}</Badge>
              </div>
              <div className="mt-auto flex items-center justify-between pt-3">
                <a href={api.docs_url || "#"} target="_blank" rel="noreferrer" className="text-[11px] text-accent-400 hover:underline flex items-center gap-1">
                  Docs <ExternalLink className="h-3 w-3" />
                </a>
                <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => void testApi(api.id)} disabled={testing === api.id}>
                  {testing === api.id ? <Spinner /> : "Test"}
                </Button>
              </div>
              {testResult[api.id] && (
                <p className="mt-1 text-[10px] muted">Test: {testResult[api.id]}</p>
              )}
            </Card>
          ))}
          {apis.length === 0 && !loading && (
            <div className="col-span-full"><Empty title="No APIs match" hint="Try a broader search or clear filters." /></div>
          )}
        </div>
      ) : null}

      {/* Categories tab */}
      {(activeSection === "all" || activeSection === "categories") && (
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5 mt-5">
          {categories.map((cat) => (
            <div key={cat.name} onClick={() => { setCategory(cat.name); setActiveSection("apis"); }} className="cursor-pointer rounded-xl border border-soft surface-2 p-3 text-center hover:border-accent-500/50 transition">
              <p className="text-xs font-semibold">{cat.name}</p>
              <p className="muted text-[11px]">{cat.api_count}</p>
            </div>
          ))}
        </div>
      )}

      {/* Featured tab */}
      {(activeSection === "all" || activeSection === "featured") && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 mt-5">
          {featured.map((api) => (
            <Card key={api.name} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold">{api.name}</h3>
                  <p className="muted text-xs">{api.category}</p>
                </div>
                <Badge tone="success">Free</Badge>
              </div>
              <p className="muted mt-2 line-clamp-2 text-xs">{api.description}</p>
              <a href={api.docs_url || api.url || "#"} target="_blank" rel="noreferrer" className="mt-2 flex items-center gap-1 text-[11px] text-accent-400 hover:underline">
                Docs <ExternalLink className="h-3 w-3" />
              </a>
            </Card>
          ))}
        </div>
      )}

      {/* MCP Servers */}
      {(activeSection === "all" || activeSection === "mcps") && (
        <div className="space-y-2 mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider muted">MCP Servers ({mcps.length})</h3>
          {mcps.map((m) => (
            <Card key={m.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0">
                <p className="text-sm font-medium">{m.name}</p>
                <p className="muted text-xs line-clamp-1">{m.description}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  <Badge>{m.transport}</Badge>
                  <Badge tone={m.auth === "None" ? "success" : "warn"}>{m.auth}</Badge>
                  <Badge>{m.status}</Badge>
                </div>
              </div>
              <a href={m.url} target="_blank" rel="noreferrer" className="flex-none text-accent-400">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Card>
          ))}
          {mcps.length === 0 && <p className="muted text-sm">No MCP servers imported yet. Run POST /api/apis/ingest.</p>}
        </div>
      )}
    </div>
  );
}