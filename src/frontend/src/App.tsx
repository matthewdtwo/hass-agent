import { useCallback, useEffect, useState } from "react";
import { checkAuth, loginUrl, type User } from "./api/auth";
import { deleteSession, listSessions } from "./api/sessions";
import Chat from "./components/Chat";
import ModelSelector from "./components/ModelSelector";
import Sidebar from "./components/Sidebar";
import type { SessionInfo } from "./types";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [model, setModel] = useState("google-gla:gemini-3-flash-preview");
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
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
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    setChatKey(id);
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

  // Not authenticated — show login
  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <div className="flex flex-col items-center gap-6 rounded-xl border border-gray-800 bg-gray-900 px-12 py-10">
          <h1 className="text-2xl font-semibold text-gray-100">HA Agent</h1>
          <p className="text-sm text-gray-400">Sign in to continue</p>
          <a
            href={loginUrl()}
            className="rounded-lg bg-white px-6 py-2.5 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-200"
          >
            Sign in with Google
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        user={user}
      />

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
          <h1 className="text-lg font-semibold">HA Agent</h1>
          <ModelSelector selected={model} onSelect={setModel} />
        </header>

        <main className="flex-1 overflow-hidden">
          <Chat
            key={chatKey}
            model={model}
            sessionId={activeSessionId}
            onSessionCreated={handleSessionCreated}
          />
        </main>
      </div>
    </div>
  );
}
