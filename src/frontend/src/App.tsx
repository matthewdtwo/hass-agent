import { useState } from "react";
import Chat from "./components/Chat";
import ModelSelector from "./components/ModelSelector";

export default function App() {
  const [model, setModel] = useState("google-gla:gemini-3-flash-preview");

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
        <h1 className="text-lg font-semibold">HA Agent</h1>
        <ModelSelector selected={model} onSelect={setModel} />
      </header>

      {/* Chat area */}
      <main className="flex-1 overflow-hidden">
        <Chat model={model} />
      </main>
    </div>
  );
}
