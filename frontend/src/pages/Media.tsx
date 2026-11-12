import { Download, FileText, Image as ImageIcon, Search, Trash2, Upload, Video } from "lucide-react";
import { useEffect, useState } from "react";
import { AuthedImage, AuthedVideo } from "../components/Media";
import { Button, Card, Empty, ErrorNotice, Input, Modal, PageHeader, Select, Textarea, cn } from "../components/ui";
import { api, downloadMedia } from "../lib/api";
import type { MediaItem } from "../lib/types";

export default function MediaPage() {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [kind, setKind] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<MediaItem | null>(null);
  const [analyzing, setAnalyzing] = useState<MediaItem | null>(null);
  const [question, setQuestion] = useState("Describe this image and extract any visible text.");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const params = new URLSearchParams();
      if (kind) params.set("kind", kind);
      if (query) params.set("q", query);
      setItems(await api.get<MediaItem[]>(`/api/media${params.toString() ? `?${params}` : ""}`));
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => void load(), 200);
    return () => clearTimeout(timer);
  }, [kind, query]);

  async function upload(file: File) {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const item = await api.upload<MediaItem>("/api/media/upload", form);
      setItems((current) => [item, ...current]);
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  }

  async function remove(item: MediaItem) {
    if (!window.confirm(`Delete "${item.title}"?`)) return;
    try {
      await api.del(`/api/media/${item.id}`);
      setItems((current) => current.filter((entry) => entry.id !== item.id));
    } catch (err) {
      setError(err);
    }
  }

  async function analyze() {
    if (!analyzing) return;
    setBusy(true);
    setAnswer("");
    try {
      const result = await api.post<{ answer: string }>(`/api/media/${analyzing.id}/analyze`, {
        question,
        model: ""
      });
      setAnswer(result.answer);
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
        title="My Media"
        subtitle="Generated and uploaded images, videos and documents with previews, downloads and deletion. Files are served through an authenticated endpoint."
        actions={
          <label className="nexa-btn-ghost cursor-pointer">
            <Upload className="h-4 w-4" />
            {uploading ? "Uploading…" : "Upload"}
            <input
              type="file"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
                event.target.value = "";
              }}
            />
          </label>
        }
      />
      <Card className="mb-5">
        <div className="flex flex-wrap gap-2">
          <Select value={kind} onChange={(event) => setKind(event.target.value)} className="w-auto">
            <option value="">All media</option>
            <option value="image">Images</option>
            <option value="video">Videos</option>
            <option value="document">Documents</option>
          </Select>
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
            <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search titles" className="pl-9" />
          </div>
        </div>
        {Boolean(error) && <div className="mt-3"><ErrorNotice error={error} /></div>}
      </Card>

      {items.length === 0 ? (
        <Empty title="No media yet" hint="Generate an image/video or upload a file to see it here." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <Card key={item.id} className="p-3">
              <button className="block w-full overflow-hidden rounded-xl" onClick={() => setPreview(item)}>
                {item.kind === "image" ? (
                  <AuthedImage src={`/api/media/${item.id}/file`} alt={item.title} className="aspect-video w-full object-cover" />
                ) : item.kind === "video" ? (
                  <AuthedVideo src={`/api/media/${item.id}/file`} className="aspect-video w-full bg-black object-cover" />
                ) : (
                  <div className="grid aspect-video place-items-center rounded-xl border border-soft surface-2">
                    <FileText className="h-8 w-8 muted" />
                  </div>
                )}
              </button>
              <div className="mt-2 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{item.title}</p>
                  <p className="muted text-[10px]">
                    {item.kind} · {(item.size / 1024).toFixed(1)} KB · {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="nexa-chip">{item.source}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => void downloadMedia(item.id, item.title)}>
                  <Download className="h-3 w-3" /> Download
                </Button>
                {item.kind === "image" && (
                  <Button variant="ghost" className="!px-2 !py-1 text-[11px]" onClick={() => { setAnalyzing(item); setAnswer(""); }}>
                    Analyze
                  </Button>
                )}
                <Button variant="danger" className="!px-2 !py-1 text-[11px]" onClick={() => void remove(item)}>
                  <Trash2 className="h-3 w-3" /> Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={Boolean(preview)} onClose={() => setPreview(null)} title={preview?.title ?? "Preview"} wide>
        {preview?.kind === "image" && <AuthedImage src={`/api/media/${preview.id}/file`} alt={preview.title} className="max-h-[70vh] w-full rounded-xl object-contain" />}
        {preview?.kind === "video" && <AuthedVideo src={`/api/media/${preview.id}/file`} className="max-h-[70vh] w-full rounded-xl bg-black" />}
        {preview?.kind === "document" && <p className="muted text-sm">Document downloads are available from the card.</p>}
      </Modal>

      <Modal open={Boolean(analyzing)} onClose={() => setAnalyzing(null)} title="Image analysis" wide>
        <div className="grid gap-3">
          <Textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={2} />
          <Button onClick={() => void analyze()} disabled={busy}>{busy ? "Analyzing…" : "Ask about image"}</Button>
          {answer && <div className="whitespace-pre-wrap rounded-xl border border-soft surface-2 p-3 text-sm">{answer}</div>}
        </div>
      </Modal>
    </div>
  );
}
