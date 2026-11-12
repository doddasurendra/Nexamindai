import {
  Copy,
  Download,
  Loader2,
  MessageSquarePlus,
  Pencil,
  RefreshCw,
  Search,
  Send,
  Square,
  Trash2
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Markdown } from "../components/Markdown";
import { Button, ErrorNotice, Empty, Input, Modal, Select, Textarea, cn } from "../components/ui";
import { api, downloadBlob, streamChat, streamRequest, type StreamEvent } from "../lib/api";
import type { Conversation, ConversationDetail, Message, ModelCatalog } from "../lib/types";

function nowIso() {
  return new Date().toISOString();
}

function blankMessage(role: "user" | "assistant", content = ""): Message {
  return {
    id: -Math.floor(Math.random() * 1e9),
    role,
    content,
    model: "",
    tokens_in: 0,
    tokens_out: 0,
    cost: 0,
    citations: [],
    error: null,
    created_at: nowIso()
  };
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<ConversationDetail | null>(null);
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null);
  const [model, setModel] = useState("");
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [renaming, setRenaming] = useState<Conversation | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [editing, setEditing] = useState<Message | null>(null);
  const [editValue, setEditValue] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    api
      .get<ModelCatalog>("/api/models")
      .then((data) => {
        setCatalog(data);
        setModel((current) => current || data.default_model);
      })
      .catch(() => setCatalog({ configured: false, default_model: "", models: [] }));
  }, []);

  async function loadConversations(term = query) {
    try {
      const data = await api.get<Conversation[]>(`/api/conversations${term ? `?q=${encodeURIComponent(term)}` : ""}`);
      setConversations(data);
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => loadConversations(query), 250);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!searchParams.get("new")) return;
    navigate("/chat", { replace: true });
    void createConversation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active?.messages]);

  async function openConversation(id: number) {
    try {
      const detail = await api.get<ConversationDetail>(`/api/conversations/${id}`);
      setActive(detail);
      setModel(detail.model || catalog?.default_model || "");
      setError(null);
    } catch (err) {
      setError(err);
    }
  }

  async function createConversation(): Promise<ConversationDetail | null> {
    try {
      const conversation = await api.post<Conversation>("/api/conversations", {
        title: "New chat",
        model: model || catalog?.default_model || ""
      });
      const detail: ConversationDetail = { ...conversation, messages: [] };
      setActive(detail);
      setModel(conversation.model);
      await loadConversations();
      return detail;
    } catch (err) {
      setError(err);
      return null;
    }
  }

  async function persistTitle() {
    if (!active || active.title !== "New chat" || active.messages.length > 0) return;
    const title = input.trim().slice(0, 70) || "New chat";
    try {
      await api.patch(`/api/conversations/${active.id}`, { title });
      await loadConversations();
    } catch {
      /* non-critical */
    }
  }

  function applyEvent(container: ConversationDetail, assistantId: number, event: StreamEvent, accumulator: { text: string }) {
    if (event.type === "delta") {
      accumulator.text += event.text;
      setActive((current) =>
        current
          ? {
              ...current,
              messages: current.messages.map((message) =>
                message.id === assistantId ? { ...message, content: accumulator.text } : message
              )
            }
          : current
      );
    }
    if (event.type === "done") {
      setActive((current) =>
        current
          ? {
              ...current,
              messages: current.messages.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      id: event.message_id,
                      content: accumulator.text,
                      model: event.model ?? message.model,
                      tokens_in: event.tokens_in ?? 0,
                      tokens_out: event.tokens_out ?? 0,
                      cost: event.cost ?? 0
                    }
                  : message
              )
            }
          : current
      );
    }
    if (event.type === "error") {
      setError(new Error(event.error));
    }
  }

  async function consumeStream(
    path: string,
    payload: Record<string, unknown>,
    optimistic: { user?: Message; assistant?: Message } = {}
  ) {
    if (!active) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError(null);
    const base = active;
    const assistant = optimistic.assistant ?? blankMessage("assistant", "");
    const messages = [...base.messages];
    if (optimistic.user) messages.push(optimistic.user);
    messages.push(assistant);
    setActive({ ...base, messages });
    const accumulator = { text: "" };
    try {
      await streamRequest(
        path,
        payload,
        (event) => applyEvent(base, assistant.id, event, accumulator),
        controller.signal
      );
      const detail = await api.get<ConversationDetail>(`/api/conversations/${base.id}`);
      setActive(detail);
      setModel(detail.model);
      await loadConversations();
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) setError(err);
      try {
        const detail = await api.get<ConversationDetail>(`/api/conversations/${base.id}`);
        setActive(detail);
      } catch {
        /* keep optimistic state */
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  async function send() {
    const content = input.trim();
    if (!content || busy) return;
    let conversation = active;
    if (!conversation) {
      conversation = await createConversation();
      if (!conversation) return;
    }
    setInput("");
    if (conversation.messages.length === 0) {
      const title = content.slice(0, 70);
      api.patch(`/api/conversations/${conversation.id}`, { title }).catch(() => undefined);
    }
    await consumeStream(
      "/api/chat/stream",
      { conversation_id: conversation.id, content, model, temperature: 0.7 },
      { user: { ...blankMessage("user", content), model }, assistant: blankMessage("assistant", "") }
    );
  }

  async function regenerate() {
    if (!active || busy) return;
    const lastUser = [...active.messages].reverse().find((message) => message.role === "user");
    if (!lastUser) return;
    await consumeStream(
      "/api/chat/regenerate",
      { conversation_id: active.id, content: lastUser.content, model },
      { assistant: blankMessage("assistant", "") }
    );
  }

  async function saveEdit() {
    if (!active || !editing) return;
    const target = editing;
    setEditing(null);
    await consumeStream(
      `/api/chat/edit?message_id=${target.id}&content=${encodeURIComponent(editValue)}`,
      {},
      {}
    );
  }

  async function rename() {
    if (!renaming) return;
    try {
      await api.patch(`/api/conversations/${renaming.id}`, { title: renameValue });
      setRenaming(null);
      await loadConversations();
      if (active?.id === renaming.id) await openConversation(renaming.id);
    } catch (err) {
      setError(err);
    }
  }

  async function remove(conversation: Conversation) {
    if (!window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) return;
    try {
      await api.del(`/api/conversations/${conversation.id}`);
      if (active?.id === conversation.id) setActive(null);
      await loadConversations();
    } catch (err) {
      setError(err);
    }
  }

  async function exportChat() {
    if (!active) return;
    try {
      const token = localStorage.getItem("nexamind_token");
      const response = await fetch(`/api/conversations/${active.id}/export?format=markdown`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      downloadBlob(await response.blob(), `nexamind-${active.id}.md`);
    } catch (err) {
      setError(err);
    }
  }

  const modelOptions = useMemo(() => catalog?.models ?? [], [catalog]);
  const hasConfiguredModels = Boolean(catalog?.configured);

  return (
    <div className="grid gap-5 lg:grid-cols-[290px_minmax(0,1fr)]">
      <aside className="nexa-card hidden max-h-[calc(100vh-9rem)] flex-col p-3 lg:flex">
        <Button onClick={() => void createConversation()} className="w-full">
          <MessageSquarePlus className="h-4 w-4" /> New chat
        </Button>
        <div className="relative mt-3">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search conversations"
            className="pl-9"
            aria-label="Search conversations"
          />
        </div>
        <div className="mt-3 flex-1 space-y-1 overflow-y-auto pr-1">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={cn(
                "group flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm transition hover:bg-black/5 dark:hover:bg-white/5",
                active?.id === conversation.id && "bg-accent-500/10"
              )}
            >
              <button
                className="min-w-0 flex-1 text-left"
                onClick={() => void openConversation(conversation.id)}
                title={conversation.title}
              >
                <p className="truncate font-medium">{conversation.title}</p>
                <p className="muted truncate text-[11px]">
                  {conversation.model || "default"} · {new Date(conversation.updated_at).toLocaleDateString()}
                </p>
              </button>
              <div className="flex flex-none items-center gap-0.5 opacity-0 transition group-hover:opacity-100">
                <button
                  className="rounded-lg p-1 muted hover:text-accent-400"
                  title="Rename"
                  onClick={() => {
                    setRenaming(conversation);
                    setRenameValue(conversation.title);
                  }}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button className="rounded-lg p-1 muted hover:text-red-400" title="Delete" onClick={() => void remove(conversation)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
          {conversations.length === 0 && <p className="muted px-2 py-6 text-center text-xs">No conversations yet.</p>}
        </div>
      </aside>

      <section className="nexa-card flex min-h-[calc(100vh-9rem)] flex-col overflow-hidden p-0">
        <header className="flex flex-wrap items-center gap-3 border-b border-soft px-4 py-3">
          <div className="min-w-0 flex-1">
            <h1 className="truncate font-display text-lg font-semibold">{active?.title ?? "New chat"}</h1>
            <p className="muted text-xs">
              {active ? `${active.messages.length} messages` : "Ask anything — markdown, code, streaming"} · {model || "no model"}
            </p>
          </div>
          <Select
            value={model}
            onChange={(event) => {
              setModel(event.target.value);
              if (active) api.patch(`/api/conversations/${active.id}`, { model: event.target.value }).catch(() => undefined);
            }}
            className="max-w-[260px]"
            aria-label="Model"
          >
            {!model && <option value="">Select a model</option>}
            {modelOptions.length === 0 && <option value={model}>{model || "OPENROUTER_API_KEY not configured"}</option>}
            {modelOptions.map((item) => (
              <option key={item.model_id} value={item.model_id}>
                {item.name || item.model_id}
              </option>
            ))}
          </Select>
          <Button variant="ghost" onClick={() => void exportChat()} disabled={!active} title="Export markdown">
            <Download className="h-4 w-4" />
          </Button>
        </header>

        {!hasConfiguredModels && (
          <div className="border-b border-soft px-4 py-2 text-xs text-amberish-500">
            OpenRouter is not configured on the backend. Chat will return a 503 integration state until OPENROUTER_API_KEY is set.
          </div>
        )}

        <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
          {!active?.messages.length && (
            <div className="mx-auto mt-6 max-w-2xl">
              <Empty
                title="Start a conversation"
                hint="NexaMind streams real model output. Choose a model, ask a question, and use the message actions to copy, edit, or regenerate."
              />
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {[
                  "Explain vector databases like I'm building a RAG app.",
                  "Compare three approaches to multi-agent routing.",
                  "Draft a secure code review checklist for FastAPI.",
                  "Summarize the tradeoffs of SSE vs WebSockets."
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="rounded-xl border border-soft surface-2 px-3 py-2 text-left text-xs transition hover:border-accent-400/50"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {active?.messages.map((message) => (
            <article key={message.id} className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}>
              {message.role !== "user" && (
                <div className="mt-1 grid h-8 w-8 flex-none place-items-center rounded-xl bg-gradient-to-br from-accent-500 to-mint-500 text-[11px] font-bold text-white">
                  N
                </div>
              )}
              <div className={cn("max-w-[min(760px,92%)]", message.role === "user" && "order-first")}>
                <div
                  className={cn(
                    "rounded-2xl px-4 py-3",
                    message.role === "user"
                      ? "bg-gradient-to-br from-accent-600 to-accent-500 text-white"
                      : "border border-soft surface-2"
                  )}
                >
                  {message.role === "assistant" ? (
                    <Markdown>{message.content || "…"}</Markdown>
                  ) : (
                    <p className="whitespace-pre-wrap text-[14px] leading-6">{message.content}</p>
                  )}
                  {message.citations?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {message.citations.map((citation, index) => (
                        <span key={`${message.id}-${index}`} className="rounded-full border border-soft px-2 py-0.5 text-[10px] muted">
                          [{citation.index ?? index + 1}] {citation.filename ?? citation.title ?? citation.url}
                        </span>
                      ))}
                    </div>
                  )}
                  {message.error && <p className="mt-2 text-xs text-red-400">{message.error}</p>}
                </div>
                <div className="mt-1 flex items-center gap-2 text-[10px] muted">
                  <span>{message.model || ""}</span>
                  {message.tokens_out > 0 && (
                    <span>
                      {message.tokens_in + message.tokens_out} tokens · ${message.cost.toFixed(6)}
                    </span>
                  )}
                  {message.role === "assistant" && message.content && (
                    <>
                      <button
                        className="hover:text-accent-400"
                        onClick={() => navigator.clipboard.writeText(message.content)}
                        title="Copy"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                      <button className="hover:text-accent-400" onClick={() => void regenerate()} disabled={busy} title="Regenerate">
                        <RefreshCw className="h-3 w-3" />
                      </button>
                    </>
                  )}
                  {message.role === "user" && (
                    <button
                      className="hover:text-accent-400"
                      onClick={() => {
                        setEditing(message);
                        setEditValue(message.content);
                      }}
                      title="Edit and resend"
                    >
                      <Pencil className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-xs muted">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-400 typing-dot" />
              <span className="h-1.5 w-1.5 rounded-full bg-accent-400 typing-dot" />
              <span className="h-1.5 w-1.5 rounded-full bg-accent-400 typing-dot" />
              generating…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-soft p-3">
          {Boolean(error) && <div className="mb-2"><ErrorNotice error={error} /></div>}
          <div className="flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void send();
                }
              }}
              placeholder="Message NexaMind… (Enter to send, Shift+Enter for newline)"
              className="min-h-[52px] max-h-40"
              rows={2}
            />
            {busy ? (
              <Button
                variant="ghost"
                onClick={() => abortRef.current?.abort()}
                title="Stop generation"
                aria-label="Stop generation"
              >
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={() => void send()} disabled={!input.trim()} aria-label="Send message">
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </section>

      <Modal open={Boolean(renaming)} onClose={() => setRenaming(null)} title="Rename conversation">
        <Input value={renameValue} onChange={(event) => setRenameValue(event.target.value)} autoFocus />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setRenaming(null)}>
            Cancel
          </Button>
          <Button onClick={() => void rename()}>Save</Button>
        </div>
      </Modal>

      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title="Edit message">
        <Textarea value={editValue} onChange={(event) => setEditValue(event.target.value)} rows={6} />
        <p className="muted mt-2 text-xs">Saving replaces this message and all later messages, then regenerates the reply.</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setEditing(null)}>
            Cancel
          </Button>
          <Button onClick={() => void saveEdit()}>Save & resend</Button>
        </div>
      </Modal>
    </div>
  );
}
