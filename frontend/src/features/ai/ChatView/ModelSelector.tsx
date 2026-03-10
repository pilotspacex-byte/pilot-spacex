/**
 * ModelSelector - Compact model picker in ChatHeader.
 *
 * Reads available models from AISettingsStore.availableModels.
 * Selection is persisted per workspace via PilotSpaceStore.setSelectedModel.
 * Disabled models (is_selectable=false) are rendered with opacity and cannot be chosen.
 *
 * Returns null when no models are configured (keeps ChatHeader layout stable).
 *
 * @module features/ai/ChatView/ModelSelector
 */
'use client';

import { observer } from 'mobx-react-lite';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useStore } from '@/stores';
import { cn } from '@/lib/utils';

export const ModelSelector = observer(function ModelSelector() {
  const { ai } = useStore();
  const { settings, pilotSpace } = ai;

  if (settings.availableModels.length === 0) return null;

  const selectedModelId = pilotSpace.selectedModel?.modelId ?? '';

  return (
    <Select
      value={selectedModelId}
      onValueChange={(modelId) => {
        const model = settings.availableModels.find((m) => m.model_id === modelId);
        if (model && model.is_selectable) {
          pilotSpace.setSelectedModel(model.provider, modelId, model.provider_config_id);
        }
      }}
    >
      <SelectTrigger
        className="h-6 w-[140px] text-xs border-border/50 bg-transparent"
        data-testid="model-selector"
      >
        <SelectValue placeholder="Model" />
      </SelectTrigger>
      <SelectContent>
        {settings.availableModels.map((m) => (
          <SelectItem
            key={`${m.provider_config_id}-${m.model_id}`}
            value={m.model_id}
            disabled={!m.is_selectable}
            className={cn(!m.is_selectable && 'opacity-50 cursor-not-allowed')}
          >
            {m.display_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
});

ModelSelector.displayName = 'ModelSelector';
