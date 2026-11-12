import { Network, Plus, Trash2, Search, ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Spinner } from "../components/ui";
import { api } from "../lib/api";

interface Entity { id: number; name: string; entity_type: string; summary: string; source_url: string; tags: string[]; confidence: string }
interface EntityDetail extends Entity { relations: { id: number; source_id: number; target_id: number; relation_type: string; confidence: string; evidence: string }[]; related: Entity[] }

export default function KnowledgeGraphPage() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [entityType, setEntityType] = useState("concept");
  const [summary, setSummary] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [tags, setTags] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (type) params.set("entity_type", type);
      const data = await api.get<Entity[]>(`/api/graph/entities?${params.toString()}`);
      setEntities(data);
    } catch (err) { setError(err); } finally { setLoading(false); }
  }

  useEffect(() => { const t = setTimeout(() => void load(), 250); return () => clearTimeout(t); }, [query, type]);

  async function openDetail(entity: Entity) {
    try {
      const data = await api.get<EntityDetail>(`/api/graph/entities/${entity.id}`);
      setDetail(data);
    } catch (err) { setError(err); }
  }

  async function create() {
    try {
      await api.post("/api/graph/entities", { name, entity_type: entityType, summary, source_url: sourceUrl, tags: tags.split(",").map((t) => t.trim()).filter(Boolean), confidence: "derived" });
      setCreateOpen(false);
      setName(""); setSummary(""); setSourceUrl(""); setTags("");
      await load();
    } catch (err) { setError(err); }
  }

  async function remove(entity: Entity) {
    if (!window.confirm(`Delete ${entity.name}?`)) return;
    try { await api.del(`/api/graph/entities/${entity.id}`); if (detail?.id === entity.id) setDetail(null); await load(); } catch (err) { setError(err); }
  }

  const TYPES = ["concept", "technology", "person", "company", "paper", "api", "project"];

  return (
    <div>
      <PageHeader
        icon={<Network className="h-5 w-5" />}
        title="Global Knowledge Graph"
        subtitle="Entities and relationships across research, technology, companies and APIs. Confidence levels distinguish verified facts from inferred connections."
        actions={<Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> Add entity</Button>}
      />
      {Boolean(error) && <div className="mb-4"><ErrorNotice error={error} /></div>}
      <Card className="mb-5">
        <div className="flex flex-wrap gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search entities…" className="pl-9" />
          </div>
          <Select value={type} onChange={(e) => setType(e.target.value)} className="w-auto">
            <option value="">All types</option>
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
        </div>
      </Card>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="grid content-start gap-3 sm:grid-cols-2">
          {entities.map((entity) => (
            <button key={entity.id} onClick={() => void openDetail(entity)} className="rounded-xl border border-soft surface-2 p-3 text-left transition hover:border-accent-500/50">
              <div className="flex items-center justify-between gap-2"><Badge>{entity.entity_type}</Badge><Badge tone={entity.confidence === "verified" ? "success" : "warn"}>{entity.confidence}</Badge></div>
              <p className="mt-2 text-sm font-semibold">{entity.name}</p>
              <p className="muted mt-1 line-clamp-2 text-xs">{entity.summary}</p>
            </button>
          ))}
          {entities.length === 0 && !loading && <Empty title="No entities" hint="Add your first knowledge entity." />}
          {loading && <Spinner label="Loading…" />}
        </div>
        <Card className="h-fit">
          {!detail ? <p className="muted text-sm">Select an entity to view details and relationships.</p> : (
            <div>
              <div className="flex items-start justify-between gap-2">
                <div><h2 className="font-display text-lg font-semibold">{detail.name}</h2><Badge>{detail.entity_type}</Badge></div>
                <button onClick={() => void remove(detail)} className="rounded-lg p-1.5 muted hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
              </div>
              <p className="mt-3 text-sm leading-6">{detail.summary || "No summary."}</p>
              {detail.source_url && <a href={detail.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-accent-400 hover:underline">Source <ExternalLink className="h-3 w-3" /></a>}
              {detail.tags.length > 0 && <div className="mt-2 flex flex-wrap gap-1">{detail.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}</div>}
              <h3 className="mt-4 text-xs font-semibold uppercase tracking-wider muted">Relationships ({detail.relations.length})</h3>
              <div className="mt-2 space-y-1">
                {detail.relations.map((relation) => <p key={relation.id} className="text-xs"><Badge>{relation.relation_type}</Badge> → entity #{relation.source_id === detail.id ? relation.target_id : relation.source_id}</p>)}
                {detail.relations.length === 0 && <p className="muted text-xs">No relationships yet.</p>}
              </div>
              <h3 className="mt-4 text-xs font-semibold uppercase tracking-wider muted">Related entities</h3>
              <div className="mt-2 space-y-1">
                {detail.related.map((entity) => <p key={entity.id} className="text-xs">{entity.name}</p>)}
                {detail.related.length === 0 && <p className="muted text-xs">None.</p>}
              </div>
            </div>
          )}
        </Card>
      </div>
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add knowledge entity" wide>
        <div className="grid gap-3">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Entity name (e.g. Qiskit)" autoFocus />
          <Select value={entityType} onChange={(e) => setEntityType(e.target.value)}>
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </Select>
          <Input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Summary" />
          <Input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="Source URL" />
          <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="Tags (comma-separated)" />
          <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button><Button onClick={() => void create()} disabled={!name.trim()}>Add</Button></div>
        </div>
      </Modal>
    </div>
  );
}
