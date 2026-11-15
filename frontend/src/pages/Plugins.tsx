import { Plug, Copy, Check, ExternalLink, BookOpen, ShieldCheck, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, ErrorNotice, PageHeader, Spinner, cn } from "../components/ui";
import { api } from "../lib/api";

interface Plugin {
  id: string;
  name: string;
  fixes: string;
  problem: string;
  repo: string;
  docs: string;
  type: string;
  status: string;
  install_steps: string[];
  env_vars: string[];
  aI_note: string;
}

const STATUS_TONE: Record<string, "success" | "warn" | "default"> = {
  ready: "success",
  installed: "success",
  "configured-but-unreachable": "warn",
  unreachable: "warn",
  "not-configured": "warn",
  "available (claude code skill)": "default",
  "not-installed": "default",
};

const TYPE_LABEL: Record<string, string> = {
  "llm-proxy": "LLM proxy",
  "claude-code-skill": "Claude Code skill",
  "cli-tool": "CLI tool",
  "security-scanner": "Security scanner",
};

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [copied, setCopied] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Plugin[]>("/api/plugins");
      setPlugins(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function copy(text: string, id: string) {
    void navigator.clipboard.writeText(text);
    setCopied(id);
    window.setTimeout(() => setCopied(null), 1500);
  }

  return (
    <div>
      <PageHeader
        icon={<Plug className="h-5 w-5" />}
        title="Plugin Center"
        subtitle="Five free AI plugins — each fixes a different problem (usage, video, output, data, security). Connect the ones NexaMind can run directly; install the Claude Code ones into your terminal."
        actions={
          <Button variant="ghost" onClick={() => void load()}>
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} /> Refresh status
          </Button>
        }
      />
      {Boolean(error) && <div className="mb-4"><ErrorNotice error={error} /></div>}
      {loading && plugins.length === 0 ? (
        <Spinner label="Detecting plugins…" />
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          {plugins.map((plugin) => (
            <Card key={plugin.id} className="flex flex-col">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="font-display text-lg font-semibold">{plugin.name}</h2>
                  <p className="muted text-xs">Fixes: {plugin.fixes}</p>
                </div>
                <Badge tone={STATUS_TONE[plugin.status] ?? "default"}>{plugin.status}</Badge>
              </div>
              <p className="mt-3 text-sm leading-6 muted">{plugin.problem}</p>
              <p className="muted mt-2 text-[10px] uppercase tracking-wider">{TYPE_LABEL[plugin.type] ?? plugin.type}</p>

              <div className="mt-4 rounded-xl border border-soft surface-2 p-3">
                <p className="text-[10px] uppercase tracking-wider muted">How to connect</p>
                <ol className="mt-2 space-y-1.5 pl-4 list-decimal text-xs leading-6">
                  {plugin.install_steps.map((step, index) => (
                    <li key={index} className="flex items-start justify-between gap-2">
                      <code className="rounded bg-black/30 px-1.5 py-0.5 font-mono text-[10px] leading-5 whitespace-pre-wrap break-all">{step}</code>
                      <button onClick={() => copy(step, `${plugin.id}-${index}`)} className="flex-none rounded-lg p-1 muted hover:text-accent-400" title="Copy">
                        {copied === `${plugin.id}-${index}` ? <Check className="h-4 w-4 text-mint-400" /> : <Copy className="h-4 w-4" />}
                      </button>
                    </li>
                  ))}
                </ol>
                {plugin.env_vars.length > 0 && (
                  <p className="muted mt-2 text-[10px]">Env vars: {plugin.env_vars.join(", ")} → backend/.env</p>
                )}
              </div>

              <p className="muted mt-3 text-[11px] leading-5 italic">{plugin.aI_note}</p>

              <div className="mt-auto flex items-center gap-2 pt-4">
                <a href={plugin.repo} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-accent-400 hover:underline">
                  <BookOpen className="h-3.5 w-3.5" /> Repo <ExternalLink className="h-3 w-3" />
                </a>
                <a href={plugin.docs} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs muted hover:text-accent-400">
                  Docs <ExternalLink className="h-3 w-3" />
                </a>
                {plugin.id === "skillspector" && <ShieldCheck className="ml-auto h-4 w-4 text-mint-400" />}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
