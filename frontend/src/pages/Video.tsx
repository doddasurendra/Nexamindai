import { Video, Mic, Languages, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { AuthedVideo } from "../components/Media";
import { Button, Card, ErrorNotice, Input, PageHeader, Select, Spinner, cn } from "../components/ui";
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

  useEffect(() => {
    api
      .get<MediaItem[]>("/api/media?kind=video")
      .then(setItems)
      .catch(() => undefined);
  }, []);

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

  return (
    <div>
      <PageHeader
        icon={<Video className="h-5 w-5" />}
        title="Video Generation"
        subtitle="Text-to-video with AI voiceover. NexaMind writes a script, narrates it with TTS, generates scene clips and stitches them into one MP4. Longer videos take longer and cost more credits."
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
              <option value={300}>5 minutes (max)</option>
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
          <span className="muted text-xs">
            {mode === "voiceover" ? "Script + TTS + scenes + stitching (may take several minutes)" : "Silent clip (fast)"}
          </span>
        </div>
        <p className="muted mt-2 text-[11px]">
          Requires REPLICATE_API_TOKEN and OPENROUTER_API_KEY. Voiceover uses minimax/speech-02-hd; scenes use minimax/video-01 (~6s each). Longer videos = more scenes = more credits and time.
        </p>
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Card key={item.id} className="p-3">
            <AuthedVideo src={`/api/media/${item.id}/file`} className="aspect-video w-full rounded-xl bg-black" />
            <p className="mt-2 line-clamp-2 text-xs">{item.title}</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {item.meta?.language != null && <span className="nexa-chip">{String(item.meta.language)}</span>}
              {item.meta?.duration_seconds != null && <span className="nexa-chip">{String(item.meta.duration_seconds)}s</span>}
              {item.meta?.scenes != null && <span className="nexa-chip">{String(item.meta.scenes)} scenes</span>}
            </div>
            <p className="muted mt-1 text-[10px]">{new Date(item.created_at).toLocaleString()}</p>
          </Card>
        ))}
        {items.length === 0 && <p className="muted text-sm">No generated videos yet.</p>}
      </div>
    </div>
  );
}
