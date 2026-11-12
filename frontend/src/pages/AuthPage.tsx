import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { BrainCircuit, Loader2, Lock, Mail, User as UserIcon } from "lucide-react";
import { useAuth } from "../lib/auth";
import { Button, ErrorNotice, Input } from "../components/ui";

export default function AuthPage() {
  const { login, register } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const isRegister = location.pathname === "/register";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isRegister) await register(email.trim(), password, name.trim());
      else await login(email.trim(), password);
      navigate("/chat");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_.9fr]">
      <section className="relative hidden overflow-hidden border-r border-soft p-10 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-accent-500/20 blur-3xl" />
        <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-mint-500/15 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-accent-500 to-mint-500 shadow-glow">
            <BrainCircuit className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="font-display text-lg font-semibold">NexaMind AI</p>
            <p className="text-xs muted">one mind, many tools</p>
          </div>
        </div>
        <div className="relative max-w-xl">
          <h1 className="font-display text-4xl font-semibold leading-tight tracking-tight">
            Research, build, and automate with a workspace that tells the truth.
          </h1>
          <p className="muted mt-4 text-sm leading-relaxed">
            Streaming chat, cited research, specialized agents, RAG, workflow automation, MCP tooling and measured
            evaluations — all behind one clean interface. Real integrations, honest disabled states, no fabricated results.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-3 text-center text-xs">
            {[
              ["14", "workspaces"],
              ["4", "expert agents"],
              ["0", "fake outputs"]
            ].map(([value, label]) => (
              <div key={label} className="rounded-2xl border border-soft glass px-3 py-4">
                <p className="font-display text-2xl font-semibold">{value}</p>
                <p className="muted mt-1">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-[11px] muted">© {new Date().getFullYear()} NexaMind AI · built for serious work</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-md animate-fadeup">
          <div className="mb-8 lg:hidden">
            <div className="mb-3 grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-accent-500 to-mint-500">
              <BrainCircuit className="h-5 w-5 text-white" />
            </div>
            <p className="font-display text-lg font-semibold">NexaMind AI</p>
          </div>
          <h2 className="font-display text-3xl font-semibold tracking-tight">
            {isRegister ? "Create your workspace" : "Welcome back"}
          </h2>
          <p className="muted mt-2 text-sm">
            {isRegister ? "Your first account becomes the workspace administrator." : "Sign in to continue where you left off."}
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            {isRegister && (
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">Name</span>
                <div className="relative">
                  <UserIcon className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
                  <Input
                    className="pl-9"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Ada Lovelace"
                    autoComplete="name"
                  />
                </div>
              </label>
            )}
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">Email</span>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
                <Input
                  className="pl-9"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                />
              </div>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">Password</span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
                <Input
                  className="pl-9"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="At least 8 characters"
                  autoComplete={isRegister ? "new-password" : "current-password"}
                />
              </div>
            </label>
            {Boolean(error) && <ErrorNotice error={error} />}
            <Button type="submit" className="w-full" disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {isRegister ? "Create account" : "Sign in"}
            </Button>
          </form>

          <p className="muted mt-6 text-sm">
            {isRegister ? "Already have an account?" : "New to NexaMind?"}{" "}
            <Link className="text-accent-500 hover:underline" to={isRegister ? "/login" : "/register"}>
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
