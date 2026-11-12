import { ArrowDown, Check, Plus, Play, Save, Trash2, Workflow as WorkflowIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Spinner, Textarea, cn } from "../components/ui";
import { api } from "../lib/api";
import type { Workflow, WorkflowExecution, WorkflowGraph, WorkflowNode } from "../lib/types";

const NODE_TYPES = ["ai", "search", "fetch_url", "doc_extract", "rag", "agent", "http", "transform", "notify", "approval"];

function defaultGraph(): WorkflowGraph {
  return {
    nodes: [
      { id: "start", type: "trigger", config: {} },
      { id: "step-1", type: "ai", config: { prompt: "Summarize the input", max_tokens: 400 } }
    ],
    edges: [{ from: "start", to: "step-1" }]
  };
}

function relink(nodes: WorkflowNode[]): WorkflowGraph {
  return {
    nodes,
    edges: nodes.slice(0, -1).map((node, index) => ({ from: node.id, to: nodes[index + 1].id }))
  };
}

export default function AutomationPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [name, setName] = useState("New workflow");
  const [description, setDescription] = useState("");
  const [nodes, setNodes] = useState<WorkflowNode[]>(defaultGraph().nodes);
  const [inputJson, setInputJson] = useState('{"topic": "NexaMind"}');
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<WorkflowNode | null>(null);
  const [configDraft, setConfigDraft] = useState("{}");

  async function refresh() {
    const [flows, runs] = await Promise.all([
      api.get<Workflow[]>("/api/workflows"),
      api.get<WorkflowExecution[]>("/api/workflows/executions")
    ]);
    setWorkflows(flows);
    setExecutions(runs);
  }

  useEffect(() => {
    void refresh().catch(setError);
  }, []);

  function pick(workflow: Workflow) {
    setSelected(workflow);
    setName(workflow.name);
    setDescription(workflow.description);
    setNodes(workflow.graph.nodes);
    setExecution(null);
  }

  function newWorkflow() {
    setSelected(null);
    setName("New workflow");
    setDescription("");
    setNodes(defaultGraph().nodes);
    setExecution(null);
  }

  function addNode(type: string) {
    const id = `node-${Date.now().toString(36).slice(-4)}`;
    const config: Record<string, unknown> =
      type === "ai"
        ? { prompt: "Summarize the input", max_tokens: 400 }
        : type === "search"
          ? { query: "{input}", max_results: 5 }
          : type === "transform"
            ? { template: "Result: {text}" }
            : type === "notify"
              ? { message: "Workflow finished" }
              : type === "approval"
                ? { message: "Approve to continue" }
                : {};
    setNodes((current) => [...current, { id, type, config }]);
  }

  function removeNode(id: string) {
    setNodes((current) => current.filter((node) => node.id !== id));
  }

  function saveNodeConfig() {
    if (!editing) return;
    try {
      const parsed = JSON.parse(configDraft) as Record<string, unknown>;
      setNodes((current) => current.map((node) => (node.id === editing.id ? { ...node, config: parsed } : node)));
      setEditing(null);
    } catch {
      setError(new Error("Config must be valid JSON"));
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const graph = relink(nodes);
      if (selected) {
        const updated = await api.patch<Workflow>(`/api/workflows/${selected.id}`, { name, description, graph });
        setSelected(updated);
        setWorkflows((current) => current.map((flow) => (flow.id === updated.id ? updated : flow)));
      } else {
        const created = await api.post<Workflow>("/api/workflows", { name, description, graph });
        setSelected(created);
        setWorkflows((current) => [created, ...current]);
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function run() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setExecution(null);
    try {
      const parsed = JSON.parse(inputJson);
      const result = await api.post<WorkflowExecution>(`/api/workflows/${selected.id}/run`, { input: parsed });
      setExecution(result);
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!execution?.approval_token) return;
    try {
      const result = await api.post<WorkflowExecution>(`/api/workflows/executions/${execution.id}/approve`, {
        token: execution.approval_token,
        approved: true
      });
      setExecution(result);
      await refresh();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<WorkflowIcon className="h-5 w-5" />}
        title="Automation"
        subtitle="Build linear workflows from typed nodes, run them, inspect every step, and require approval before sensitive actions. Node connections are wired in order."
        actions={<Button onClick={newWorkflow}><Plus className="h-4 w-4" /> New workflow</Button>}
      />

      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-fit">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Workflows</h3>
          <div className="space-y-1">
            {workflows.map((workflow) => (
              <button
                key={workflow.id}
                onClick={() => pick(workflow)}
                className={cn("w-full rounded-xl px-2 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5", selected?.id === workflow.id && "bg-accent-500/10")}
              >
                <p className="truncate font-medium">{workflow.name}</p>
                <p className="muted text-[10px]">v{workflow.version} · {workflow.graph.nodes.length} nodes</p>
              </button>
            ))}
            {workflows.length === 0 && <p className="muted text-xs">No workflows yet.</p>}
          </div>
        </Card>

        <div className="space-y-5">
          <Card>
            <div className="grid gap-3 md:grid-cols-2">
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Workflow name" />
              <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description" />
            </div>

            <div className="mt-4 space-y-2">
              {nodes.map((node, index) => (
                <div key={node.id}>
                  <div className="flex items-center gap-3 rounded-xl border border-soft surface-2 p-3">
                    <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent-500/15 text-[11px] font-bold text-accent-400">{index + 1}</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {node.type} <span className="muted text-[10px]">({node.id})</span>
                      </p>
                      <p className="muted truncate text-[11px]">{JSON.stringify(node.config)}</p>
                    </div>
                    <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => { setEditing(node); setConfigDraft(JSON.stringify(node.config, null, 2)); }}>
                      Configure
                    </Button>
                    {node.type !== "trigger" && (
                      <button className="rounded-lg p-1 muted hover:text-red-400" onClick={() => removeNode(node.id)} title="Remove node">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                  {index < nodes.length - 1 && <div className="grid place-items-center py-0.5 text-muted"><ArrowDown className="h-3 w-3" /></div>}
                </div>
              ))}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Select value="" onChange={(event) => event.target.value && addNode(event.target.value)} className="w-auto" aria-label="Add node">
                <option value="">Add node…</option>
                {NODE_TYPES.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </Select>
              <Button variant="ghost" onClick={() => void save()} disabled={busy}>
                <Save className="h-4 w-4" /> Save workflow
              </Button>
              <Button onClick={() => void run()} disabled={busy || !selected}>
                {busy ? <Spinner label="Running…" /> : <><Play className="h-4 w-4" /> Run</>}
              </Button>
            </div>
            <div className="mt-3">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wider muted">Run input (JSON)</label>
              <Textarea value={inputJson} onChange={(event) => setInputJson(event.target.value)} rows={2} className="font-mono text-xs" />
            </div>
            {Boolean(error) && <div className="mt-3"><ErrorNotice error={error} /></div>}
          </Card>

          {execution && (
            <Card>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge tone={execution.status === "completed" ? "success" : execution.status === "awaiting_approval" ? "warn" : "danger"}>
                  {execution.status}
                </Badge>
                <span className="nexa-chip">execution #{execution.id}</span>
                {execution.approval_token && (
                  <Button onClick={() => void approve()}>
                    <Check className="h-4 w-4" /> Approve & continue
                  </Button>
                )}
              </div>
              <div className="space-y-2">
                {execution.logs.map((log, index) => (
                  <div key={index} className="rounded-xl border border-soft surface-2 p-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{log.type}</span>
                      <span className="muted">{log.node_id}</span>
                      <Badge tone={log.status === "ok" ? "success" : log.status === "awaiting_approval" ? "warn" : "danger"}>{log.status}</Badge>
                      {typeof log.ms === "number" && <span className="muted">{log.ms} ms</span>}
                    </div>
                    {log.error && <p className="mt-1 text-red-400">{log.error}</p>}
                    {log.output !== undefined && (
                      <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-black/30 p-2 text-[11px]">{JSON.stringify(log.output, null, 2)}</pre>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Execution history</h3>
            <div className="space-y-1">
              {executions.slice(0, 10).map((run) => (
                <button key={run.id} onClick={() => setExecution(run)} className="w-full rounded-xl px-2 py-2 text-left text-xs hover:bg-black/5 dark:hover:bg-white/5">
                  #{run.id} · workflow {run.workflow_id} · {run.status} · {new Date(run.created_at).toLocaleString()}
                </button>
              ))}
              {executions.length === 0 && <p className="muted text-xs">No executions yet.</p>}
            </div>
          </Card>
        </div>
      </div>

      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={`Configure ${editing?.type ?? "node"}`} wide>
        <p className="muted mb-2 text-xs">
          Node-specific JSON. Examples: AI {"{prompt, model, max_tokens}"}; search {"{query, max_results}"}; http {"{url, method}"}; transform {"{template}"}.
        </p>
        <Textarea value={configDraft} onChange={(event) => setConfigDraft(event.target.value)} rows={8} className="font-mono text-xs" />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
          <Button onClick={saveNodeConfig}>Apply</Button>
        </div>
      </Modal>
    </div>
  );
}
