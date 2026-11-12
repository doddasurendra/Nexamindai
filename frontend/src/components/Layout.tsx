import {
  Activity,
  Bot,
  Boxes,
  BrainCircuit,
  ChevronRight,
  Code2,
  Cpu,
  Database,
  FlaskConical,
  Gauge,
  Globe,
  Image as ImageIcon,
  LayoutDashboard,
  Menu,
  MessageSquarePlus,
  Moon,
  Network,
  Newspaper,
  Search,
  Settings as SettingsIcon,
  Sparkles,
  Sun,
  Terminal,
  Video,
  Workflow,
  X
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { cn, Button } from "./ui";

const NAV = [
  { to: "/chat", label: "AI Assistant", icon: MessageSquarePlus },
  { to: "/command-center", label: "AI Command Center", icon: Terminal },
  { to: "/research", label: "Deep Research", icon: FlaskConical },
  { to: "/news", label: "Global News", icon: Newspaper },
  { to: "/search", label: "Web Search", icon: Search },
  { to: "/images", label: "Image Generation", icon: ImageIcon },
  { to: "/video", label: "Video Generation", icon: Video },
  { to: "/media", label: "My Media", icon: LayoutDashboard },
  { to: "/agents", label: "Agent Studio", icon: Bot },
  { to: "/automation", label: "Automation Studio", icon: Workflow },
  { to: "/chatbots", label: "Chatbot Studio", icon: Cpu },
  { to: "/knowledge", label: "Knowledge Base", icon: Database },
  { to: "/apis", label: "API Universe", icon: Globe },
  { to: "/mcp", label: "MCP Center", icon: Boxes },
  { to: "/evaluation", label: "Model Testing Lab", icon: Gauge },
  { to: "/knowledge-graph", label: "Knowledge Graph", icon: Network },
  { to: "/dev-workspace", label: "Software Dev", icon: Code2 },
  { to: "/devtools", label: "Developer Tools", icon: Activity },
  { to: "/settings", label: "Settings", icon: SettingsIcon }
];

function Brand() {
  return (
    <div className="flex items-center gap-3 px-1">
      <div className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-accent-500 via-accent-600 to-mint-500 shadow-glow">
        <BrainCircuit className="h-5 w-5 text-white" />
      </div>
      <div className="leading-tight">
        <p className="font-display text-[15px] font-semibold tracking-tight">NexaMind AI</p>
        <p className="text-[11px] muted">one mind, many tools</p>
      </div>
    </div>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <Brand />
      <nav className="scrollbar-none flex-1 space-y-1 overflow-y-auto pr-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) => cn("nav-item", isActive && "active")}
          >
            <Icon className="nav-icon h-[18px] w-[18px] flex-none" />
            <span className="truncate">{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="rounded-2xl border border-soft surface-2 p-3">
        <div className="flex items-center gap-2 text-xs font-medium">
          <Sparkles className="h-3.5 w-3.5 text-mint-400" />
          Streaming + real APIs
        </div>
        <p className="muted mt-1 text-[11px] leading-relaxed">
          OpenRouter, Tavily, Hugging Face, MCP. Missing keys are shown honestly — never simulated.
        </p>
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    let active = true;
    const check = () =>
      api
        .get<{ status: string }>("/health")
        .then((data) => active && setOnline(data.status === "ok"))
        .catch(() => active && setOnline(false));
    check();
    const timer = setInterval(check, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const current = NAV.find((item) => location.pathname.startsWith(item.to));

  return (
    <div className="flex h-full">
      <aside className="hidden w-[268px] flex-none border-r border-soft glass lg:block">
        <Sidebar />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-[280px] border-r border-soft surface">
            <div className="flex justify-end p-3">
              <Button variant="ghost" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                <X className="h-4 w-4" />
              </Button>
            </div>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-soft glass px-4 lg:px-6">
          <Button variant="ghost" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-4 w-4" />
          </Button>
          <div className="hidden items-center gap-2 text-sm sm:flex">
            <span className="muted">Workspace</span>
            <ChevronRight className="h-3.5 w-3.5 muted" />
            <span className="font-medium">{current?.label ?? "New Chat"}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span
              className={cn(
                "nexa-chip hidden sm:inline-flex",
                online === false ? "border-red-500/30 text-red-400" : "border-mint-500/30 text-mint-500"
              )}
              title="Backend health"
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", online === false ? "bg-red-400" : "bg-mint-400")} />
              {online === null ? "checking…" : online ? "API online" : "API offline"}
            </span>
            <Button variant="ghost" onClick={toggle} aria-label="Toggle theme">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <div className="flex items-center gap-2 rounded-xl border border-soft surface-2 px-2 py-1.5">
              <div className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-accent-500 to-mint-500 text-xs font-bold text-white">
                {(user?.name || user?.email || "N").slice(0, 1).toUpperCase()}
              </div>
              <div className="hidden leading-tight sm:block">
                <p className="max-w-[140px] truncate text-xs font-semibold">{user?.name || "Member"}</p>
                <p className="max-w-[140px] truncate text-[10px] muted">{user?.email}</p>
              </div>
              <Button
                variant="ghost"
                className="!px-2 !py-1 text-[11px]"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Sign out
              </Button>
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1400px] px-4 py-6 lg:px-8 lg:py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
