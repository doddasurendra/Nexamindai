import { Image as ImageIcon, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { AuthedImage } from "../components/Media";
import { Button, Card, ErrorNotice, Input, PageHeader, Spinner } from "../components/ui";
import { api } from "../lib/api";
import type { MediaItem } from "../lib/types";

export default function ImagesPage() {
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [items, setItems] = useState<MediaItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");

  async function load() {
    try {
      setItems(await api.get<MediaItem[]>("/api/media?kind=image"));
    } catch {
      /* gallery is optional */
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function generate() {
    if (!prompt.trim()) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const created = await api.post<MediaItem[]>("/api/images/generate", { prompt: prompt.trim(), model, n: 1 });
      setItems((current) => [...created, ...current]);
      setNotice(`Generated ${created.length} image${created.length === 1 ? "" : "s"} with ${String(created[0]?.meta?.model ?? model)}.`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<ImageIcon className="h-5 w-5" />}
        title="Image Generation"
        subtitle="Uses OpenRouter's image-capable models. Requires an image model (e.g. google/gemini-2.5-flash-image) and OPENROUTER_API_KEY; failures are shown, never simulated."
      />
      <Card className="mb-6">
        <div className="grid gap-3 md:grid-cols-[1fr_260px]">
          <Input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Describe the image…" />
          <Input value={model} onChange={(event) => setModel(event.target.value)} placeholder="model (optional)" />
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Button onClick={() => void generate()} disabled={busy || !prompt.trim()}>
            <Sparkles className="h-4 w-4" /> {busy ? <Spinner label="Generating…" /> : "Generate"}
          </Button>
          <span className="muted text-xs">Default model: google/gemini-2.5-flash-image</span>
        </div>
        {notice && <p className="mt-3 text-xs text-mint-500">{notice}</p>}
        {Boolean(error) && <div className="mt-4"><ErrorNotice error={error} /></div>}
      </Card>

      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Generated images</h3>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Card key={item.id} className="p-3">
            <AuthedImage src={`/api/media/${item.id}/file`} alt={item.title} className="aspect-square w-full rounded-xl object-cover" />
            <p className="mt-2 line-clamp-2 text-xs">{item.title}</p>
            <p className="muted text-[10px]">{new Date(item.created_at).toLocaleString()}</p>
          </Card>
        ))}
        {items.length === 0 && <p className="muted text-sm">No generated images yet.</p>}
      </div>
    </div>
  );
}
