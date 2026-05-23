import { useCallback, useEffect, useState } from "react";
import { checkAuth, loginUrl, type User } from "./api/auth";
import { getConfig } from "./api/config";
import { deleteSession, listSessions } from "./api/sessions";
import Chat from "./components/Chat";
import ModelSelector from "./components/ModelSelector";
import Settings from "./components/Settings";
import Sidebar from "./components/Sidebar";
import type { SessionInfo } from "./types";

type Page = "chat" | "settings";

const STORAGE_KEY = "hass-agent-session";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  // Empty string until config loads; ModelSelector falls back to first available
  const [model, setModel] = useState("");
  const [sessions, setSessions] = useState<SessionInfo[]>([]);

  // Restore last active session from localStorage so a browser refresh resumes
  // the same session instead of starting a new one.
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY)
  );
  const [currentPage, setCurrentPage] = useState<Page>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // chatKey changes on explicit user actions (new chat, select session), not on
  // mid-stream auto-create. Seed from localStorage so refresh reconnects properly.
  const [chatKey, setChatKey] = useState(
    () => localStorage.getItem(STORAGE_KEY) ?? "__new__"
  );

  // Check auth on mount and load preferred model from config
  useEffect(() => {
    checkAuth()
      .then((u) => {
        setUser(u);
        setAuthChecked(true);
      })
      .catch(() => setAuthChecked(true));
    getConfig()
      .then((c) => { if (c.preferred_model) setModel(c.preferred_model); })
      .catch(() => {});
  }, []);

  // Load sessions once authenticated
  useEffect(() => {
    if (user) {
      listSessions().then(setSessions).catch(() => {});
    }
  }, [user]);

  const handleNewChat = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setActiveSessionId(null);
    setChatKey("__new__" + Date.now());
    setCurrentPage("chat");
    setSidebarOpen(false);
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    localStorage.setItem(STORAGE_KEY, id);
    setActiveSessionId(id);
    setChatKey(id);
    setCurrentPage("chat");
    setSidebarOpen(false);
  }, []);

  const handleDeleteSession = useCallback(
    async (id: string) => {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        localStorage.removeItem(STORAGE_KEY);
        setActiveSessionId(null);
        setChatKey("__new__" + Date.now());
      }
    },
    [activeSessionId]
  );

  const handleSessionCreated = useCallback(
    (id: string, title: string) => {
      const now = new Date().toISOString();
      const session: SessionInfo = {
        id,
        title,
        created_at: now,
        updated_at: now,
      };
      setSessions((prev) => [session, ...prev]);
      // Persist and update sidebar highlight without remounting Chat
      localStorage.setItem(STORAGE_KEY, id);
      setActiveSessionId(id);
    },
    []
  );

  const handleNavigate = useCallback((page: Page) => {
    setCurrentPage(page);
    setSidebarOpen(false);
  }, []);

  // Loading state
  if (!authChecked) {
    return (
      <div className="flex h-dvh items-center justify-center bg-white text-gray-500 dark:bg-gray-950 dark:text-gray-400">
        Loading...
      </div>
    );
  }

  // Not authenticated — redirect to login (only reached in non-addon mode,
  // since addon mode auto-authenticates via HA Ingress headers)
  if (!user) {
    window.location.href = loginUrl();
    return (
      <div className="flex h-dvh items-center justify-center bg-white text-gray-500 dark:bg-gray-950 dark:text-gray-400">
        Redirecting to login…
      </div>
    );
  }

  return (
    <div className="flex h-dvh bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        currentPage={currentPage}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onNavigate={handleNavigate}
        user={user}
      />

      {/* Main content */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-950">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="shrink-0 rounded-md p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 md:hidden"
            aria-label="Open sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
              <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 10.5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10z" clipRule="evenodd" />
            </svg>
          </button>

          <h1 className="flex-1 truncate text-base font-semibold">
            {currentPage === "settings" ? "Settings" : "HA Agent"}
          </h1>

          {currentPage === "chat" && (
            <ModelSelector selected={model} onSelect={setModel} />
          )}
        </header>

        <main className="min-h-0 flex-1 overflow-hidden">
          {currentPage === "settings" ? (
          <Settings onPreferredModelChange={setModel} />
          ) : (
            <Chat
              key={chatKey}
              model={model}
              sessionId={activeSessionId}
              onSessionCreated={handleSessionCreated}
            />
          )}
        </main>
      </div>
    </div>
  );
}
