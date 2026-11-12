import { Bot, Copy, Plus, Send, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Markdown } from "../components/Markdown";
import { Badge, Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Spinner, Textarea, cn } from "../components/ui";
import { api } from "../lib/api";
import type { Chatbot, KnowledgeBase } from "../lib/types";

interface TestMessage {
  role: "user" | "assistant";
  content: string;
}

export default function ChatbotsPage() {
  const [bots, setBots] = useState<Chatbot[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selected, setSelected] = useState<Chatbot | null>(null);
  const [name, setName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [model, setModel] = useState("");
  const [kbId, setKbId] = useState("");
  const [grounded, setGrounded] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [thread, setThread] = useState<TestMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function refresh() {
    const [botList, kbList] = await Promise.all([
      api.get<Chatbot[]>("/api/chatbots"),
      api.get<KnowledgeBase[]>("/api/knowledge-bases")
    ]);
    setBots(botList);
    setKbs(kbList);
  }

  useEffect(() => {
    void refresh().catch(setError);
  }, []);

  function pick(bot: Chatbot) {
    setSelected(bot);
    setName(bot.name);
    setInstructions(bot.instructions);
    setModel(bot.model);
    setKbId(bot.knowledge_base_id ? String(bot.knowledge_base_id) : "");
    setGrounded(bot.grounded);
    setThread([]);
  }

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const bot = await api.post<Chatbot>("/api/chatbots", {
        name: name || "Untitled chatbot",
        instructions,
        model,
        knowledge_base_id: kbId ? Number(kbId) : null,
        grounded,
        theme: {}
      });
      setBots((current) => [bot, ...current]);
      setCreateOpen(false);
      pick(bot);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.patch<Chatbot>(`/api/chatbots/${selected.id}`, {
        name,
        instructions,
        model,
        knowledge_base_id: kbId ? Number(kbId) : null,
        grounded,
        theme: {}
      });
      setSelected(updated);
      setBots((current) => current.map((bot) => (bot.id === updated.id ? updated : bot)));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function togglePublish() {
    if (!selected) return;
    try {
      const updated = await api.post<Chatbot>(`/api/chatbots/${selected.id}/publish?published=${!selected.published}`);
      setSelected(updated);
      setBots((current) => current.map((bot) => (bot.id === updated.id ? updated : bot)));
    } catch (err) {
      setError(err);
    }
  }

  async function remove(bot: Chatbot) {
    if (!window.confirm(`Delete ${bot.name}?`)) return;
    try {
      await api.del(`/api/chatbots/${bot.id}`);
      setBots((current) => current.filter((entry) => entry.id !== bot.id));
      if (selected?.id === bot.id) setSelected(null);
    } catch (err) {
      setError(err);
    }
  }

  async function test() {
    if (!selected || !message.trim()) return;
    const userMessage = message.trim();
    setMessage("");
    setThread((current) => [...current, { role: "user", content: userMessage }]);
    setBusy(true);
    try {
      const result = await api.post<{ answer: string | null; citations: unknown[] }>(`/api/chatbots/${selected.id}/test`, {
        message: userMessage
      });
      setThread((current) => [...current, { role: "assistant", content: result.answer ?? "No grounded answer available." }]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const embed = selected
    ? `<script src="${window.location.origin}/widget.js" data-token="${selected.public_token}"></script>`
    : "";

  return (
    <div>
      <PageHeader
        icon={<Bot className="h-5 w-5" />}
        title="Chatbot Studio"
        subtitle="Create grounded chatbots over your knowledge bases, test them, publish a public widget, and iterate on instructions and models."
        actions={<Button onClick={() => { setCreateOpen(true); setName(""); setInstructions(""); setModel(""); setKbId(""); setGrounded(true); }}><Plus className="h-4 w-4" /> New chatbot</Button>}
      />
      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="h-fit">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Chatbots</h3>
          <div className="space-y-1">
            {bots.map((bot) => (
              <div key={bot.id} className={cn("group flex items-center gap-1 rounded-xl px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5", selected?.id === bot.id && "bg-accent-500/10")}>
                <button className="min-w-0 flex-1 text-left" onClick={() => pick(bot)}>
                  <p className="truncate text-sm font-medium">{bot.name}</p>
                  <p className="muted text-[10px]">{bot.grounded ? "grounded" : "open"} · {bot.published ? "published" : "draft"}</p>
                </button>
                <button className="p-1 muted opacity-0 hover:text-red-400 group-hover:opacity-100" onClick={() => void remove(bot)} title="Delete">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
            {bots.length === 0 && <p className="muted text-xs">No chatbots yet.</p>}
          </div>
        </Card>

        {!selected ? (
          <Empty title="Select or create a chatbot" hint="Chatbots can be grounded in a knowledge base and published as a public widget." />
        ) : (
          <div className="grid gap-5 xl:grid-cols-2">
            <Card>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">{selected.name}</h2>
                <Badge tone={selected.published ? "success" : "warn"}>{selected.published ? "published" : "draft"}</Badge>
              </div>
              <div className="grid gap-3">
                <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Name" />
                <Textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={5} placeholder="System instructions…" />
                <Input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Model (optional, uses default)" />
                <Select value={kbId} onChange={(event) => setKbId(event.target.value)}>
                  <option value="">No knowledge base</option>
                  {kbs.map((kb) => (
                    <option key={kb.id} value={kb.id}>{kb.name}</option>
                  ))}
                </Select>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={grounded} onChange={(event) => setGrounded(event.target.checked)} />
                  Knowledge-only mode (refuse when nothing is retrieved)
                </label>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={() => void save()} disabled={busy}>Save</Button>
                <Button variant="ghost" onClick={() => void togglePublish()}>{selected.published ? "Unpublish" : "Publish"}</Button>
              </div>
              {selected.published && (
                <div className="mt-4 rounded-xl border border-soft surface-2 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold">Embed snippet</p>
                    <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => navigator.clipboard.writeText(embed)}>
                      <Copy className="h-3 w-3" /> Copy
                    </Button>
                  </div>
                  <pre className="mt-2 overflow-auto rounded-lg bg-black/30 p-2 text-[11px]">{embed}</pre>
                  <p className="muted mt-1 text-[10px]">Public endpoint: /api/public/chatbots/{selected.public_token}</p>
                </div>
              )}
              {Boolean(error) && <div className="mt-3"><ErrorNotice error={error} /></div>}
            </Card>

            <Card className="flex flex-col">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider muted">Test chat</h3>
              <div className="flex-1 space-y-3 overflow-y-auto">
                {thread.map((entry, index) => (
                  <div key={index} className={cn("rounded-2xl px-3 py-2 text-sm", entry.role === "user" ? "ml-8 bg-accent-600 text-white" : "mr-8 border border-soft surface-2")}>
                    {entry.role === "assistant" ? <Markdown>{entry.content}</Markdown> : entry.content}
                  </div>
                ))}
                {thread.length === 0 && <p className="muted text-xs">Ask the chatbot something to verify grounding and citations.</p>}
              </div>
              <div className="mt-3 flex gap-2">
                <Input value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void test()} placeholder="Test message…" />
                <Button onClick={() => void test()} disabled={busy || !message.trim()}>{busy ? <Spinner /> : <Send className="h-4 w-4" />}</Button>
              </div>
            </Card>
          </div>
        )}
      </div>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New chatbot">
        <div className="grid gap-3">
          <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Chatbot name" autoFocus />
          <Textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={4} placeholder="Instructions" />
          <Select value={kbId} onChange={(event) => setKbId(event.target.value)}>
            <option value="">No knowledge base</option>
            {kbs.map((kb) => <option key={kb.id} value={kb.id}>{kb.name}</option>)}
          </Select>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={grounded} onChange={(event) => setGrounded(event.target.checked)} /> knowledge-only mode
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={() => void create()} disabled={busy}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
