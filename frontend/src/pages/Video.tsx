import { Video } from "lucide-react";
import { useEffect, useState } from "react";
import { AuthedVideo } from "../components/Media";
import { Button, Card, ErrorNotice, Input, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { MediaItem } from "../lib/types";

export default function VideoPage() {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [busy, setBusy] = useState(false);
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
      const item = await api.post<MediaItem>("/api/videos/generate", { prompt: prompt.trim(), model });
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
        subtitle="Text-to-video through Replicate. Best results with English prompts — non-English prompts are auto-translated. Without REPLICATE_API_TOKEN the integration reports as not configured."
      />
      <Card className="mb-6">
        <Input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Describe the video… (e.g. 'a person explaining quantum computing with glowing qubits')" />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Input value={model} onChange={(event) => setModel(event.target.value)} placeholder="model (optional, default minimax/video-01)" className="max-w-xs" />
          <Button onClick={() => void generate()} disabled={busy || !prompt.trim()}>
            {busy ? <Spinner label="Rendering…" /> : "Generate video"}
          </Button>
          <span className="muted text-xs">Requires REPLICATE_API_TOKEN. Video rendering can take 2–5 minutes.</span>
        </div>
        <p className="muted mt-2 text-[11px]">
          Tip: video models are optimized for English. If you write in Telugu/Hindi/etc., NexaMind auto-translates the prompt for generation.
        </p>
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Card key={item.id} className="p-3">
            <AuthedVideo src={`/api/media/${item.id}/file`} className="aspect-video w-full rounded-xl bg-black" />
            <p className="mt-2 line-clamp-2 text-xs">{item.title}</p>
            <p className="muted text-[10px]">{new Date(item.created_at).toLocaleString()}</p>
          </Card>
        ))}
        {items.length === 0 && <p className="muted text-sm">No generated videos yet.</p>}
      </div>
    </div>
  );
}
