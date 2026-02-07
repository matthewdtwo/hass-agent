import type { User } from "../api/auth";
import { logout } from "../api/auth";
import type { SessionInfo } from "../types";

interface Props {
  sessions: SessionInfo[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  user: User;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  user,
}: Props) {
  const handleLogout = async () => {
    await logout();
    window.location.reload();
  };

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-800 bg-gray-950">
      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full rounded-lg border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 transition-colors"
        >
          + New Chat
        </button>
      </div>

      {/* Session list */}
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {sessions.length === 0 && (
          <p className="px-3 py-4 text-center text-xs text-gray-600">
            No conversations yet
          </p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group relative mb-0.5 flex cursor-pointer items-center rounded-lg px-3 py-2 text-sm transition-colors ${
              s.id === activeSessionId
                ? "bg-gray-800 text-gray-100"
                : "text-gray-400 hover:bg-gray-900 hover:text-gray-200"
            }`}
            onClick={() => onSelectSession(s.id)}
          >
            <div className="min-w-0 flex-1">
              <div className="truncate">{s.title}</div>
              <div className="text-xs text-gray-600">
                {timeAgo(s.updated_at)}
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSession(s.id);
              }}
              className="ml-2 hidden shrink-0 rounded p-1 text-gray-600 hover:bg-gray-700 hover:text-red-400 group-hover:block"
              title="Delete"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path
                  fillRule="evenodd"
                  d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        ))}
      </nav>

      {/* User info */}
      <div className="border-t border-gray-800 p-3">
        <div className="flex items-center gap-2">
          {user.picture ? (
            <img
              src={user.picture}
              alt=""
              className="h-7 w-7 shrink-0 rounded-full"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-700 text-xs text-gray-300">
              {user.name[0]}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm text-gray-300">{user.name}</div>
          </div>
          <button
            onClick={handleLogout}
            className="shrink-0 rounded p-1 text-gray-600 hover:bg-gray-800 hover:text-gray-300"
            title="Sign out"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-4 w-4"
            >
              <path
                fillRule="evenodd"
                d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z"
                clipRule="evenodd"
              />
              <path
                fillRule="evenodd"
                d="M19 10a.75.75 0 00-.75-.75H8.704l1.048-.943a.75.75 0 10-1.004-1.114l-2.5 2.25a.75.75 0 000 1.114l2.5 2.25a.75.75 0 101.004-1.114l-1.048-.943h9.546A.75.75 0 0019 10z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
