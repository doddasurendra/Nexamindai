import { Database, FileUp, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Markdown } from "../components/Markdown";
import { Badge, Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Spinner, cn } from "../components/ui";
import { api } from "../lib/api";
import type { DocumentItem, KnowledgeBase, RagHit } from "../lib/types";

export default function KnowledgePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selected, setSelected] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [name, setName] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [hits, setHits] = useState<RagHit[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<{ filename?: string; index?: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function refresh() {
    const list = await api.get<KnowledgeBase[]>("/api/knowledge-bases");
    setKbs(list);
    if (!selected && list.length) setSelected(list[0]);
    return list;
  }

  useEffect(() => {
    void refresh().catch(setError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.get<DocumentItem[]>(`/api/knowledge-bases/${selected.id}/documents`).then(setDocuments).catch(setError);
  }, [selected]);

  async function create() {
    setBusy(true);
    try {
      const kb = await api.post<KnowledgeBase>("/api/knowledge-bases", { name, description: "" });
      setKbs((current) => [kb, ...current]);
      setSelected(kb);
      setCreateOpen(false);
      setName("");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    if (!selected) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const doc = await api.upload<DocumentItem>(`/api/knowledge-bases/${selected.id}/documents`, form);
      setDocuments((current) => [doc, ...current]);
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  }

  async function removeDoc(doc: DocumentItem) {
    if (!window.confirm(`Delete ${doc.filename}?`)) return;
    try {
      await api.del(`/api/documents/${doc.id}`);
      setDocuments((current) => current.filter((item) => item.id !== doc.id));
    } catch (err) {
      setError(err);
    }
  }

  async function ask() {
    if (!selected || !query.trim()) return;
    setBusy(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await api.post<{ answer: string | null; hits: RagHit[]; citations: { filename?: string; index?: number }[]; notice?: string }>(
        "/api/rag/answer",
        { knowledge_base_id: selected.id, query, top_k: 5, mode }
      );
      setHits(result.hits);
      setAnswer(result.answer ?? result.notice ?? "No answer returned.");
      setCitations(result.citations ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<Database className="h-5 w-5" />}
        title="Knowledge Base"
        subtitle="Upload PDF, DOCX, TXT, CSV, XLSX or images. Chunks are embedded and stored locally; hybrid retrieval combines semantic and lexical scoring."
        actions={<Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> New knowledge base</Button>}
      />
      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-fit">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Knowledge bases</h3>
          <div className="space-y-1">
            {kbs.map((kb) => (
              <button
                key={kb.id}
                onClick={() => setSelected(kb)}
                className={cn("w-full rounded-xl px-2 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5", selected?.id === kb.id && "bg-accent-500/10")}
              >
                <p className="truncate font-medium">{kb.name}</p>
                <p className="muted text-[10px]">{kb.document_count ?? 0} documents</p>
              </button>
            ))}
            {kbs.length === 0 && <p className="muted text-xs">No knowledge bases yet.</p>}
          </div>
        </Card>

        <div className="space-y-5">
          {!selected ? (
            <Empty title="Create a knowledge base" hint="Upload documents, then ask grounded questions with citations." />
          ) : (
            <>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="font-display text-lg font-semibold">{selected.name}</h2>
                    <p className="muted text-xs">{documents.length} documents · {documents.filter((doc) => doc.status === "ready").length} ready</p>
                  </div>
                  <label className="nexa-btn-ghost cursor-pointer">
                    <FileUp className="h-4 w-4" /> {uploading ? "Extracting…" : "Upload document"}
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.txt,.csv,.xlsx,.md,.png,.jpg,.jpeg,.webp"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void upload(file);
                        event.target.value = "";
                      }}
                    />
                  </label>
                </div>

                <div className="mt-4 space-y-2">
                  {documents.map((doc) => (
                    <div key={doc.id} className="flex items-center gap-3 rounded-xl border border-soft surface-2 p-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{doc.filename}</p>
                        <p className="muted text-[11px]">
                          {(doc.size / 1024).toFixed(1)} KB · {String(doc.meta?.chunks ?? "?")} chunks · {String(doc.meta?.extractor ?? "")}
                        </p>
                        {doc.error && <p className="mt-1 text-xs text-red-400">{doc.error}</p>}
                      </div>
                      <Badge tone={doc.status === "ready" ? "success" : doc.status === "error" ? "danger" : "warn"}>{doc.status}</Badge>
                      <button className="rounded-lg p-1 muted hover:text-red-400" onClick={() => void removeDoc(doc)} title="Delete document">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  {documents.length === 0 && <p className="muted text-sm">No documents yet.</p>}
                </div>
                {Boolean(error) && <div className="mt-3"><ErrorNotice error={error} /></div>}
              </Card>

              <Card>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <div className="relative flex-1">
                    <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
                    <Input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void ask()} placeholder="Ask the knowledge base…" className="pl-9" />
                  </div>
                  <Select value={mode} onChange={(event) => setMode(event.target.value)} className="w-auto">
                    <option value="hybrid">Hybrid</option>
                    <option value="semantic">Semantic</option>
                  </Select>
                  <Button onClick={() => void ask()} disabled={busy || !query.trim()}>{busy ? <Spinner label="Retrieving…" /> : "Ask"}</Button>
                </div>

                {answer && (
                  <div className="mt-4">
                    <div className="rounded-2xl border border-soft surface-2 p-4">
                      <Markdown>{answer}</Markdown>
                    </div>
                    {citations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {citations.map((citation, index) => (
                          <span key={index} className="nexa-chip">[{citation.index ?? index + 1}] {citation.filename}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {hits.length > 0 && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs font-medium">Retrieved chunks ({hits.length})</summary>
                    <div className="mt-2 space-y-2">
                      {hits.map((hit) => (
                        <div key={hit.chunk_id} className="rounded-xl border border-soft p-3 text-xs">
                          <p className="font-medium">{hit.filename} · score {hit.score.toFixed(3)}</p>
                          <p className="muted mt-1 line-clamp-4 whitespace-pre-wrap">{hit.content}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </Card>
            </>
          )}
        </div>
      </div>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New knowledge base">
        <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Product documentation" autoFocus />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button onClick={() => void create()} disabled={busy || !name.trim()}>Create</Button>
        </div>
      </Modal>
    </div>
  );
}
