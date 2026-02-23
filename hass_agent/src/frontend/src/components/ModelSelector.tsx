import { useEffect, useState } from "react";
import type { ModelInfo } from "../types";

interface Props {
  selected: string;
  onSelect: (modelId: string) => void;
}

export default function ModelSelector({ selected, onSelect }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    fetch("api/models")
      .then((r) => {
        if (!r.ok) return [];
        return r.json();
      })
      .then((loaded: ModelInfo[]) => {
        setModels(loaded);
        // If the current selection isn't in the list, auto-pick the first available
        if (loaded.length > 0 && !loaded.find((m) => m.id === selected)) {
          onSelect(loaded[0].id);
        }
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grouped = models.reduce<Record<string, ModelInfo[]>>((acc, m) => {
    (acc[m.provider] ??= []).push(m);
    return acc;
  }, {});

  return (
    <select
      value={selected}
      onChange={(e) => onSelect(e.target.value)}
      className="rounded-md border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
    >
      {Object.entries(grouped).map(([provider, providerModels]) => (
        <optgroup key={provider} label={provider.toUpperCase()}>
          {providerModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
