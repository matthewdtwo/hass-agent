import { useCallback, useEffect, useState } from "react";
import { deleteSession, listSessions } from "./api/sessions";
import Chat from "./components/Chat";
import ModelSelector from "./components/ModelSelector";
import Sidebar from "./components/Sidebar";
import type { SessionInfo } from "./types";

export default function App() {
  const [model, setModel] = useState("google-gla:gemini-3-flash-preview");
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  // chatKey only changes on explicit user actions (new chat, select session),
  // NOT when a session is auto-created mid-stream.
  const [chatKey, setChatKey] = useState("__new__");

  // Load sessions on mount
  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
  }, []);

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

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
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
