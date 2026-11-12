import { Navigate, Route, Routes } from "react-router-dom";
import { Loader2 } from "lucide-react";
import Layout from "./components/Layout";
import { useAuth } from "./lib/auth";
import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/Chat";
import SearchPage from "./pages/Search";
import ResearchPage from "./pages/Research";
import ImageGenPage from "./pages/Images";
import VideoGenPage from "./pages/Video";
import MediaPage from "./pages/Media";
import AgentsPage from "./pages/Agents";
import AutomationPage from "./pages/Automation";
import ChatbotsPage from "./pages/Chatbots";
import KnowledgePage from "./pages/Knowledge";
import MCPPage from "./pages/MCP";
import EvaluationPage from "./pages/Evaluation";
import GlobalNewsPage from "./pages/GlobalNews";
import CommandCenterPage from "./pages/CommandCenter";
import ApiUniversePage from "./pages/ApiUniverse";
import KnowledgeGraphPage from "./pages/KnowledgeGraph";
import DevWorkspacePage from "./pages/DevWorkspace";
import DevToolsPage from "./pages/DevTools";
import SettingsPage from "./pages/Settings";

function Splash() {
  return (
    <div className="grid h-full place-items-center">
      <div className="flex items-center gap-2 text-sm muted">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading NexaMind…
      </div>
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <Splash />;

  if (!user) {
    return (
      <Routes>
        <Route path="/register" element={<AuthPage />} />
        <Route path="/login" element={<AuthPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/research" element={<ResearchPage />} />
        <Route path="/news" element={<GlobalNewsPage />} />
        <Route path="/command-center" element={<CommandCenterPage />} />
        <Route path="/images" element={<ImageGenPage />} />
        <Route path="/video" element={<VideoGenPage />} />
        <Route path="/media" element={<MediaPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/automation" element={<AutomationPage />} />
        <Route path="/chatbots" element={<ChatbotsPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/mcp" element={<MCPPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/apis" element={<ApiUniversePage />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="/dev-workspace" element={<DevWorkspacePage />} />
        <Route path="/devtools" element={<DevToolsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Layout>
  );
}
