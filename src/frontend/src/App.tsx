import { useCallback, useEffect, useState } from "react";
import { checkAuth, loginUrl, type User } from "./api/auth";
import { deleteSession, listSessions } from "./api/sessions";
import Chat from "./components/Chat";
import ModelSelector from "./components/ModelSelector";
import Settings from "./components/Settings";
import Sidebar from "./components/Sidebar";
import type { SessionInfo } from "./types";

type Page = "chat" | "settings";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [model, setModel] = useState("google-gla:gemini-3-flash-preview");
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<Page>("chat");
  // chatKey only changes on explicit user actions (new chat, select session),
  // NOT when a session is auto-created mid-stream.
  const [chatKey, setChatKey] = useState("__new__");

  // Check auth on mount
  useEffect(() => {
    checkAuth()
      .then((u) => {
        setUser(u);
        setAuthChecked(true);
      })
      .catch(() => setAuthChecked(true));
  }, []);

  // Load sessions once authenticated
  useEffect(() => {
    if (user) {
      listSessions().then(setSessions).catch(() => {});
    }
  }, [user]);

  const handleNewChat = useCallback(() => {
    setActiveSessionId(null);
    setChatKey("__new__" + Date.now());
    setCurrentPage("chat");
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    setChatKey(id);
    setCurrentPage("chat");
  }, []);

  const handleDeleteSession = useCallback(
    async (id: string) => {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
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
      // Only update sidebar highlight — don't change chatKey so Chat keeps streaming
      setActiveSessionId(id);
    },
    []
  );

  // Loading state
  if (!authChecked) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 text-gray-400">
        Loading...
      </div>
    );
  }

  // Not authenticated — redirect to login (only reached in non-addon mode,
  // since addon mode auto-authenticates via HA Ingress headers)
  if (!user) {
    window.location.href = loginUrl();
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950 text-gray-400">
        Redirecting to login…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        currentPage={currentPage}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onNavigate={setCurrentPage}
        user={user}
      />

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
          <h1 className="text-lg font-semibold">
            {currentPage === "settings" ? "Settings" : "HA Agent"}
          </h1>
          {currentPage === "chat" && (
            <ModelSelector selected={model} onSelect={setModel} />
          )}
        </header>

        <main className="flex-1 overflow-hidden">
          {currentPage === "settings" ? (
            <Settings />
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
