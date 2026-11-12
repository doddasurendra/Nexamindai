import { Video, Mic, Languages, Clock, Scissors, ListChecks, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { AuthedVideo } from "../components/Media";
import { Badge, Button, Card, ErrorNotice, Input, Modal, PageHeader, Select, Spinner, cn } from "../components/ui";
import { api } from "../lib/api";
import type { MediaItem } from "../lib/types";

const LANGUAGES = ["English", "Telugu", "Hindi", "Tamil", "Kannada", "Malayalam", "Bengali", "Marathi", "Gujarati", "Punjabi", "Spanish", "French", "German", "Japanese", "Korean", "Chinese", "Arabic", "Russian"];

export default function VideoPage() {
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(30);
  const [language, setLanguage] = useState("English");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"voiceover" | "silent">("voiceover");
  const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [editing, setEditing] = useState<MediaItem | null>(null);
  const [trimStart, setTrimStart] = useState("");
  const [trimEnd, setTrimEnd] = useState("");
  const [resizeWidth, setResizeWidth] = useState("");
  const [speed, setSpeed] = useState("");
  const [volume, setVolume] = useState("");
  const [overlayText, setOverlayText] = useState("");
  const [overlayPosition, setOverlayPosition] = useState("bottom");
  const [editBusy, setEditBusy] = useState(false);

  useEffect(() => {
    api
      .get<MediaItem[]>("/api/media?kind=video")
      .then(setItems)
      .catch(() => undefined);
  }, []);

  async function reload() {
    try {
      const data = await api.get<MediaItem[]>("/api/media?kind=video");
      setItems(data);
    } catch {
      // keep stale list
    }
  }

  async function generate() {
    if (!prompt.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const endpoint = mode === "voiceover" ? "/api/videos/generate-with-voiceover" : "/api/videos/generate";
      const item = await api.post<MediaItem>(endpoint, {
        prompt: prompt.trim(),
        duration_seconds: duration,
        language,
      });
      setItems((current) => [item, ...current]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function toggleSelect(id: number) {
    setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));
  }

  async function concatenateSelected() {
    if (selected.length < 2) return;
    setBusy(true);
    setError(null);
    try {
      const item = await api.post<MediaItem>("/api/videos/concatenate", { media_ids: selected });
      setItems((current) => [item, ...current]);
      setSelected([]);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function openEditor(item: MediaItem) {
    setEditing(item);
    setTrimStart("");
    setTrimEnd("");
    setResizeWidth("");
    setSpeed("");
    setVolume("");
    setOverlayText("");
    setOverlayPosition("bottom");
  }

  async function applyEdit() {
    if (!editing) return;
    setEditBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = { source_media_id: editing.id };
      if (trimStart) payload.trim_start = Number(trimStart);
      if (trimEnd) payload.trim_end = Number(trimEnd);
      if (resizeWidth) payload.resize_width = Number(resizeWidth);
      if (speed) payload.speed = Number(speed);
      if (volume) payload.volume = Number(volume);
      if (overlayText) payload.overlay_text = overlayText;
      if (overlayPosition) payload.overlay_position = overlayPosition;
      const item = await api.post<MediaItem>("/api/videos/edit", payload);
      setItems((current) => [item, ...current]);
      setEditing(null);
    } catch (err) {
      setError(err);
    } finally {
      setEditBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<Video className="h-5 w-5" />}
        title="Video Generation & Editing"
        subtitle="Generate videos with AI voiceover and edit them in the browser: trim, resize, speed, volume, text overlay, combine clips. Up to 1-hour videos supported."
      />
      <Card className="mb-6">
        <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">Video topic / prompt</label>
        <Input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Describe the video… (e.g. 'quantum computing explained for beginners')" />

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1.5 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider muted"><Clock className="h-3 w-3" /> Duration</span>
            <Select value={duration} onChange={(event) => setDuration(Number(event.target.value))}>
              <option value={10}>10 seconds</option>
              <option value={30}>30 seconds</option>
              <option value={60}>1 minute</option>
              <option value={120}>2 minutes</option>
              <option value={300}>5 minutes</option>
              <option value={600}>10 minutes</option>
              <option value={1800}>30 minutes</option>
              <option value={3600}>1 hour (max)</option>
            </Select>
          </label>
          <label className="block">
            <span className="mb-1.5 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider muted"><Languages className="h-3 w-3" /> Language</span>
            <Select value={language} onChange={(event) => setLanguage(event.target.value)}>
              {LANGUAGES.map((lang) => <option key={lang} value={lang}>{lang}</option>)}
            </Select>
          </label>
          <label className="block">
            <span className="mb-1.5 flex items-center gap-1 text-xs font-semibold uppercase tracking-wider muted"><Mic className="h-3 w-3" /> Mode</span>
            <Select value={mode} onChange={(event) => setMode(event.target.value as "voiceover" | "silent")}>
              <option value="voiceover">With voiceover (script + TTS)</option>
              <option value="silent">Silent clip only (fast)</option>
            </Select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button onClick={() => void generate()} disabled={busy || !prompt.trim()}>
            {busy ? <Spinner label="Producing…" /> : <><Mic className="h-4 w-4" /> Generate video</>}
          </Button>
          <Button variant="ghost" onClick={() => void concatenateSelected()} disabled={busy || selected.length < 2} title="Join selected videos end to end">
            <ListChecks className="h-4 w-4" /> Combine selected ({selected.length})
          </Button>
          <span className="muted text-xs">
            {mode === "voiceover" ? "Script + TTS + scenes + stitching" : "Silent clip"}
          </span>
        </div>
        <p className="muted mt-2 text-[11px]">
          Requires REPLICATE_API_TOKEN (billing required — free tier reached) and OPENROUTER_API_KEY (or local Ollama). Long videos = far more predictions, credits and time. Video editing (trim/resize/overlay/combine) works offline with no API credits.
        </p>
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Card key={item.id} className={cn("flex flex-col p-3", selected.includes(item.id) && "ring-2 ring-accent-500")}>
            <div className="relative">
              <AuthedVideo src={`/api/media/${item.id}/file`} className="aspect-video w-full rounded-xl bg-black" />
              <button
                onClick={() => toggleSelect(item.id)}
                className={cn("absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-lg border backdrop-blur transition", selected.includes(item.id) ? "border-accent-500 bg-accent-500 text-white" : "border-white/20 bg-black/50 text-white/80 hover:border-accent-500")}
                title="Select to combine"
                aria-label="Select video"
              >
                {selected.includes(item.id) && <Check className="h-4 w-4" />}
              </button>
            </div>
            <p className="mt-2 line-clamp-2 text-xs">{item.title}</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {item.meta?.language != null && <Badge>{String(item.meta.language)}</Badge>}
              {item.meta?.duration_seconds != null && <Badge>{String(Math.round(Number(item.meta.duration_seconds) * 10) / 10)}s</Badge>}
              {item.meta?.scenes != null && <Badge>{String(item.meta.scenes)} scenes</Badge>}
              {item.meta?.source_media_id != null && <Badge>edited</Badge>}
            </div>
            <div className="mt-2 flex items-center justify-between">
              <p className="muted text-[10px]">{new Date(item.created_at).toLocaleString()}</p>
              <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => openEditor(item)}>
                <Scissors className="h-3.5 w-3.5" /> Edit
              </Button>
            </div>
          </Card>
        ))}
        {items.length === 0 && <p className="muted text-sm">No generated videos yet.</p>}
      </div>

      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={`Edit video: ${editing?.title?.slice(0, 40) ?? ""}…`} wide>
        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Trim start (s)</span>
              <Input type="number" min={0} step={0.5} value={trimStart} onChange={(event) => setTrimStart(event.target.value)} placeholder="0" />
            </label>
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Trim end (s)</span>
              <Input type="number" min={0} step={0.5} value={trimEnd} onChange={(event) => setTrimEnd(event.target.value)} placeholder="e.g. 10" />
            </label>
          </div>
          <label className="block">
            <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Resize width (px)</span>
            <Input type="number" min={16} value={resizeWidth} onChange={(event) => setResizeWidth(event.target.value)} placeholder="Leave empty to keep original" />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Speed (×)</span>
              <Input type="number" min={0.1} max={10} step={0.1} value={speed} onChange={(event) => setSpeed(event.target.value)} placeholder="1 = normal" />
            </label>
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Volume (×)</span>
              <Input type="number" min={0} max={10} step={0.1} value={volume} onChange={(event) => setVolume(event.target.value)} placeholder="1 = normal" />
            </label>
          </div>
          <label className="block">
            <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Text overlay</span>
            <Input value={overlayText} onChange={(event) => setOverlayText(event.target.value)} placeholder="Optional caption burned into the video" />
          </label>
          <div className="flex items-center justify-between gap-2">
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider muted">Overlay position</span>
              <Select value={overlayPosition} onChange={(event) => setOverlayPosition(event.target.value)} className="w-auto">
                <option value="top">Top</option>
                <option value="center">Center</option>
                <option value="bottom">Bottom</option>
              </Select>
            </label>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
              <Button onClick={() => void applyEdit()} disabled={editBusy}>
                {editBusy ? <Spinner label="Editing…" /> : <><Scissors className="h-4 w-4" /> Apply edit</>}
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
