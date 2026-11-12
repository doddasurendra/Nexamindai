import { Boxes, Check, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Spinner, Textarea, cn } from "../components/ui";
import { api } from "../lib/api";
import type { MCPConnection } from "../lib/types";

export default function MCPPage() {
  const [connections, setConnections] = useState<MCPConnection[]>([]);
  const [selected, setSelected] = useState<MCPConnection | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [headersJson, setHeadersJson] = useState("{}");
  const [allowed, setAllowed] = useState("");
  const [requireApproval, setRequireApproval] = useState(true);
  const [allowPrivate, setAllowPrivate] = useState(false);
  const [callOpen, setCallOpen] = useState(false);
  const [tool, setTool] = useState("");
  const [argsJson, setArgsJson] = useState("{}");
  const [approved, setApproved] = useState(false);
  const [result, setResult] = useState("");
  const [logs, setLogs] = useState<{ id: number; detail: Record<string, unknown>; created_at: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function refresh() {
    const [list, audit] = await Promise.all([
      api.get<MCPConnection[]>("/api/mcp/connections"),
      api.get<typeof logs>("/api/mcp/logs").catch(() => [])
    ]);
    setConnections(list);
    setLogs(audit);
    if (!selected && list.length) setSelected(list[0]);
  }

  useEffect(() => {
    void refresh().catch(setError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const headers = JSON.parse(headersJson) as Record<string, string>;
      const connection = await api.post<MCPConnection>("/api/mcp/connections", {
        name,
        url,
        headers,
        allowed_tools: allowed.split(",").map((value) => value.trim()).filter(Boolean),
        require_approval: requireApproval,
        allow_private: allowPrivate
      });
      setConnections((current) => [connection, ...current]);
      setSelected(connection);
      setCreateOpen(false);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function connect(connection: MCPConnection) {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.post<MCPConnection>(`/api/mcp/connections/${connection.id}/connect`);
      setConnections((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSelected(updated);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove(connection: MCPConnection) {
    if (!window.confirm(`Delete ${connection.name}?`)) return;
    try {
      await api.del(`/api/mcp/connections/${connection.id}`);
      setConnections((current) => current.filter((item) => item.id !== connection.id));
      if (selected?.id === connection.id) setSelected(null);
    } catch (err) {
      setError(err);
    }
  }

  async function call() {
    if (!selected || !tool) return;
    setBusy(true);
    setError(null);
    setResult("");
    try {
      const response = await api.post<{ result: unknown; latency_ms: number }>(`/api/mcp/connections/${selected.id}/call`, {
        tool,
        arguments: JSON.parse(argsJson),
        approved
      });
      setResult(JSON.stringify(response, null, 2));
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<Boxes className="h-5 w-5" />}
        title="MCP Connections"
        subtitle="Connect HTTP MCP servers, discover tools, and execute them with allowlists and explicit approval. Tool execution is logged."
        actions={<Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> New connection</Button>}
      />
      <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="h-fit">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Connections</h3>
          <div className="space-y-1">
            {connections.map((connection) => (
              <div key={connection.id} className={cn("group flex items-center gap-1 rounded-xl px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5", selected?.id === connection.id && "bg-accent-500/10")}>
                <button className="min-w-0 flex-1 text-left" onClick={() => setSelected(connection)}>
                  <p className="truncate text-sm font-medium">{connection.name}</p>
                  <p className="muted text-[10px]">{connection.status} · {connection.tools.length} tools</p>
                </button>
                <button className="p-1 muted opacity-0 hover:text-red-400 group-hover:opacity-100" onClick={() => void remove(connection)} title="Delete">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
            {connections.length === 0 && <p className="muted text-xs">No MCP connections yet.</p>}
          </div>
          {logs.length > 0 && (
            <div className="mt-4 border-t border-soft pt-3">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider muted">Recent tool calls</p>
              {logs.slice(0, 5).map((log) => (
                <p key={log.id} className="muted truncate text-[10px]">{String(log.detail.tool)} · {new Date(log.created_at).toLocaleTimeString()}</p>
              ))}
            </div>
          )}
        </Card>

        {!selected ? (
          <Empty title="Add an MCP server" hint="Point NexaMind at an HTTP JSON-RPC MCP endpoint to discover and call tools." />
        ) : (
          <div className="space-y-4">
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="font-display text-lg font-semibold">{selected.name}</h2>
                  <p className="muted break-all text-xs">{selected.url}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={selected.status === "connected" ? "success" : selected.status === "error" ? "danger" : "warn"}>{selected.status}</Badge>
                  <Button variant="ghost" onClick={() => void connect(selected)} disabled={busy}>
                    <RefreshCw className={cn("h-4 w-4", busy && "animate-spin")} /> Connect
                  </Button>
                </div>
              </div>
              {selected.last_error && <p className="mt-2 text-xs text-red-400">{selected.last_error}</p>}
              <p className="muted mt-2 text-xs">
                approval required: {String(selected.require_approval)} · allow private network: {String(selected.allow_private)} · allowlist: {selected.allowed_tools.join(", ") || "all"}
              </p>
            </Card>

            <Card>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Tools ({selected.tools.length})</h3>
              <div className="space-y-2">
                {selected.tools.map((item) => (
                  <div key={item.name} className="rounded-xl border border-soft surface-2 p-3">
                    <p className="text-sm font-medium">{item.name}</p>
                    <p className="muted text-xs">{item.description || "No description"}</p>
                  </div>
                ))}
                {selected.tools.length === 0 && <p className="muted text-sm">Run “Connect” to discover tools.</p>}
              </div>
              <div className="mt-3">
                <Button onClick={() => { setCallOpen(true); setTool(selected.tools[0]?.name ?? ""); setApproved(false); setResult(""); }} disabled={selected.tools.length === 0}>
                  Call tool
                </Button>
              </div>
            </Card>
            {Boolean(error) && <ErrorNotice error={error} />}
          </div>
        )}
      </div>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New MCP connection" wide>
        <div className="grid gap-3">
          <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Name" />
          <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://mcp.example.com/mcp" />
          <Textarea value={headersJson} onChange={(event) => setHeadersJson(event.target.value)} rows={3} className="font-mono text-xs" placeholder='{"Authorization": "Bearer …"}' />
          <Input value={allowed} onChange={(event) => setAllowed(event.target.value)} placeholder="Allowed tools (comma-separated, empty = all)" />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={requireApproval} onChange={(event) => setRequireApproval(event.target.checked)} /> require explicit approval for calls</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={allowPrivate} onChange={(event) => setAllowPrivate(event.target.checked)} /> allow private-network endpoints (localhost)</label>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={() => void create()} disabled={busy || !name || !url}>Create</Button>
          </div>
        </div>
      </Modal>

      <Modal open={callOpen} onClose={() => setCallOpen(false)} title="Call MCP tool" wide>
        <div className="grid gap-3">
          <Select value={tool} onChange={(event) => setTool(event.target.value)}>
            {selected?.tools.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
          </Select>
          <Textarea value={argsJson} onChange={(event) => setArgsJson(event.target.value)} rows={5} className="font-mono text-xs" />
          {selected?.require_approval && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={approved} onChange={(event) => setApproved(event.target.checked)} /> I approve executing this tool
            </label>
          )}
          <Button onClick={() => void call()} disabled={busy || !tool}><Check className="h-4 w-4" /> Execute</Button>
          {result && <pre className="max-h-80 overflow-auto rounded-xl bg-black/30 p-3 text-[11px]">{result}</pre>}
        </div>
      </Modal>
    </div>
  );
}
