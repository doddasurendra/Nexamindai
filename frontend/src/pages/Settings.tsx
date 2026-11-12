import { Moon, Settings as SettingsIcon, ShieldCheck, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, ErrorNotice, Input, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import type { Integration } from "../lib/types";

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, toggle } = useTheme();
  const [name, setName] = useState(user?.name ?? "");
  const [password, setPassword] = useState("");
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [saved, setSaved] = useState("");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get<Integration[]>("/api/devops/integrations").then(setIntegrations).catch(() => undefined);
  }, []);

  async function saveProfile() {
    setError(null);
    setSaved("");
    try {
      await api.patch("/api/auth/me", { name, ...(password ? { password } : {}) });
      setPassword("");
      setSaved("Profile updated.");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div>
      <PageHeader
        icon={<SettingsIcon className="h-5 w-5" />}
        title="Settings"
        subtitle="Profile, appearance and integration status. Server-side secrets are configured only through environment variables."
      />
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Profile</h3>
          <div className="grid gap-3">
            <label className="block">
              <span className="mb-1 block text-xs muted">Email</span>
              <Input value={user?.email ?? ""} disabled />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs muted">Display name</span>
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs muted">New password (optional)</span>
              <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} placeholder="At least 8 characters" />
            </label>
            <Button onClick={() => void saveProfile()}>Save profile</Button>
            {saved && <p className="text-xs text-mint-500">{saved}</p>}
            {Boolean(error) && <ErrorNotice error={error} />}
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider muted">Appearance</h3>
          <Button variant="ghost" onClick={toggle}>
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            Switch to {theme === "dark" ? "light" : "dark"} theme
          </Button>
          <p className="muted mt-3 text-sm">
            Theme preference is stored locally in your browser. The interface is responsive across desktop and mobile with a collapsible sidebar.
          </p>
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider muted"><ShieldCheck className="h-3.5 w-3.5" /> Backend integrations</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {integrations.map((integration) => (
              <div key={integration.provider} className="flex items-center justify-between rounded-xl border border-soft surface-2 px-3 py-2 text-sm">
                <span>{integration.provider}</span>
                <Badge tone={integration.configured ? "success" : "warn"}>{integration.configured ? "configured" : integration.env}</Badge>
              </div>
            ))}
          </div>
          <p className="muted mt-3 text-xs">
            Set keys in <code className="rounded bg-black/20 px-1">backend/.env</code> (see <code className="rounded bg-black/20 px-1">.env.example</code>). Keys are never exposed to the browser or stored in local storage.
          </p>
        </Card>
      </div>
    </div>
  );
}
