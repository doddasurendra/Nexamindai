import { useEffect, useState } from "react";
import { getToken } from "../lib/api";

export function useAuthedUrl(path: string | null) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!path) return;
    let objectUrl: string | null = null;
    let active = true;
    const token = getToken();
    fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => setError(true));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  return { url, error };
}

export function AuthedImage({ src, alt, className }: { src: string; alt: string; className?: string }) {
  const { url, error } = useAuthedUrl(src);
  if (error) return <div className="grid h-40 place-items-center rounded-xl border border-soft text-xs muted">preview unavailable</div>;
  if (!url) return <div className="h-40 animate-pulse rounded-xl bg-black/10 dark:bg-white/5" />;
  return <img src={url} alt={alt} className={className} loading="lazy" />;
}

export function AuthedVideo({ src, className }: { src: string; className?: string }) {
  const { url, error } = useAuthedUrl(src);
  if (error) return <div className="grid h-40 place-items-center rounded-xl border border-soft text-xs muted">video unavailable</div>;
  if (!url) return <div className="h-40 animate-pulse rounded-xl bg-black/10 dark:bg-white/5" />;
  return <video src={url} className={className} controls />;
}
