import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { BrainCircuit, Loader2, Lock, Mail, User as UserIcon, KeyRound, ArrowLeft, CheckCircle2 } from "lucide-react";
import { useAuth } from "../lib/auth";
import { Button, ErrorNotice, Input } from "../components/ui";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

type Mode = "signin" | "register" | "forgot" | "reset";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
          prompt: () => void;
        };
      };
    };
  }
}

export default function AuthPage() {
  const { login, register, loginWithGoogle, forgotPassword, resetPassword } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>(location.pathname === "/register" ? "register" : "signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);

  // Load Google Identity Services script when configured
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          setBusy(true);
          setError(null);
          try {
            await loginWithGoogle(response.credential);
            navigate("/chat");
          } catch (err) {
            setError(err);
          } finally {
            setBusy(false);
          }
        },
      });
      setGoogleReady(true);
    };
    document.head.appendChild(script);
    return () => {
      document.head.removeChild(script);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      if (mode === "register") {
        await register(email.trim(), password, name.trim());
        navigate("/chat");
      } else if (mode === "signin") {
        await login(email.trim(), password);
        navigate("/chat");
      } else if (mode === "forgot") {
        const result = await forgotPassword(email.trim());
        setNotice(result.message);
        if (result.reset_token) {
          setResetToken(result.reset_token);
          setMode("reset");
        }
      } else if (mode === "reset") {
        await resetPassword(resetToken.trim(), newPassword);
        setNotice("Password updated. You can now sign in.");
        setMode("signin");
        setPassword("");
        setNewPassword("");
        setResetToken("");
      }
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  function triggerGoogleSignIn() {
    if (!GOOGLE_CLIENT_ID) {
      setError(new Error("Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID on the frontend and GOOGLE_CLIENT_ID on the backend."));
      return;
    }
    if (!window.google) {
      setError(new Error("Google Identity Services failed to load. Check your network connection."));
      return;
    }
    window.google.accounts.id.prompt();
  }

  const isRegister = mode === "register";
  const isSignin = mode === "signin";
  const isForgot = mode === "forgot";
  const isReset = mode === "reset";

  const heading = isRegister
    ? "Create your workspace"
    : isForgot
      ? "Reset your password"
      : isReset
        ? "Set a new password"
        : "Welcome back";

  const subheading = isRegister
    ? "Your first account becomes the workspace administrator."
    : isForgot
      ? "Enter the email associated with your account."
      : isReset
        ? "Paste the reset token and choose a new password."
        : "Sign in to continue where you left off.";

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

          {(isForgot || isReset) && (
            <button
              onClick={() => { setMode("signin"); setError(null); setNotice(""); }}
              className="mb-4 inline-flex items-center gap-1 text-xs muted hover:text-accent-400 transition"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to sign in
            </button>
          )}

          <h2 className="font-display text-3xl font-semibold tracking-tight">{heading}</h2>
          <p className="muted mt-2 text-sm">{subheading}</p>

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

            {(isRegister || isSignin || isForgot) && (
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
            )}

            {(isRegister || isSignin) && (
              <label className="block">
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="block text-xs font-semibold uppercase tracking-wider muted">Password</span>
                  {isSignin && (
                    <button
                      type="button"
                      onClick={() => { setMode("forgot"); setError(null); setNotice(""); }}
                      className="text-xs text-accent-500 hover:underline"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
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
            )}

            {isReset && (
              <>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">Reset token</span>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
                    <Input
                      className="pl-9 font-mono text-xs"
                      required
                      value={resetToken}
                      onChange={(event) => setResetToken(event.target.value)}
                      placeholder="Paste the token from the previous step"
                    />
                  </div>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider muted">New password</span>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-3 h-4 w-4 muted" />
                    <Input
                      className="pl-9"
                      type="password"
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      placeholder="At least 8 characters"
                      autoComplete="new-password"
                    />
                  </div>
                </label>
              </>
            )}

            {Boolean(error) && <ErrorNotice error={error} />}
            {notice && (
              <div className="flex items-start gap-2 rounded-xl border border-mint-500/30 bg-mint-500/10 p-3 text-xs text-mint-400">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none" />
                <span>{notice}</span>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {isRegister && "Create account"}
              {isSignin && "Sign in"}
              {isForgot && "Send reset link"}
              {isReset && "Update password"}
            </Button>
          </form>

          {(isSignin || isRegister) && (
            <>
              <div className="my-5 flex items-center gap-3">
                <div className="h-px flex-1 bg-soft" />
                <span className="text-[11px] uppercase tracking-wider muted">or continue with</span>
                <div className="h-px flex-1 bg-soft" />
              </div>

              <button
                type="button"
                onClick={triggerGoogleSignIn}
                disabled={busy}
                className="flex w-full items-center justify-center gap-3 rounded-xl border border-soft bg-surface px-4 py-2.5 text-sm font-medium transition hover:bg-black/5 dark:hover:bg-white/5 disabled:opacity-50"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                  <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z" />
                  <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z" />
                  <path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z" />
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09C6.22 6.86 8.87 4.75 12 4.75z" />
                </svg>
                {googleReady ? "Continue with Google" : GOOGLE_CLIENT_ID ? "Loading Google…" : "Continue with Google"}
              </button>
              {!GOOGLE_CLIENT_ID && (
                <p className="muted mt-2 text-center text-[10px]">
                  Google sign-in needs <code className="rounded bg-black/20 px-1">VITE_GOOGLE_CLIENT_ID</code> (frontend) and{" "}
                  <code className="rounded bg-black/20 px-1">GOOGLE_CLIENT_ID</code> (backend).
                </p>
              )}
            </>
          )}

          <p className="muted mt-6 text-sm">
            {isRegister ? "Already have an account?" : "New to NexaMind?"}{" "}
            <Link
              className="text-accent-500 hover:underline"
              to={isRegister ? "/login" : "/register"}
              onClick={() => setMode(isRegister ? "signin" : "register")}
            >
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
