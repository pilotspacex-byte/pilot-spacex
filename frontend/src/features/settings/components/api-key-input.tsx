/**
 * APIKeyInput - Secure API key input with visibility toggle.
 *
 * T180: Password-style input with show/hide, "Set" badge, clear button, validation.
 */

import * as React from 'react';
import { Eye, EyeOff, Check, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface APIKeyInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  isSet: boolean;
  required?: boolean;
  error?: string;
  disabled?: boolean;
  placeholder?: string;
  provider?: 'anthropic' | 'openai';
}

export function APIKeyInput({
  label,
  value,
  onChange,
  isSet,
  required = false,
  error,
  disabled = false,
  placeholder,
  provider,
}: APIKeyInputProps) {
  const [showKey, setShowKey] = React.useState(false);
  const inputId = React.useId();
  const errorId = React.useId();

  const handleClear = () => {
    onChange('');
  };

  const getPlaceholder = () => {
    if (placeholder) return placeholder;
    if (isSet) return '••••••••••••••••••••';
    return 'Enter API key';
  };

  const hasValue = value.length > 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={inputId}>
          {label}
          {required && <span className="ml-1 text-destructive">*</span>}
        </Label>
        {isSet && (
          <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20">
            <Check className="h-3 w-3 mr-1" />
            Set
          </Badge>
        )}
      </div>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Input
            id={inputId}
            type={showKey ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={getPlaceholder()}
            disabled={disabled}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : undefined}
            className={cn('pr-20', error && 'border-destructive focus-visible:ring-destructive/20')}
            autoComplete="off"
            data-provider={provider}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {hasValue && (
              <Button
                variant="ghost"
                size="icon-sm"
                className="h-7 w-7"
                onClick={handleClear}
                disabled={disabled}
                type="button"
                aria-label="Clear API key"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-7 w-7"
              onClick={() => setShowKey(!showKey)}
              disabled={disabled || (!hasValue && !isSet)}
              type="button"
              aria-label={showKey ? 'Hide API key' : 'Show API key'}
            >
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
      </div>
      {error && (
        <p id={errorId} className="text-sm text-destructive flex items-center gap-1.5">
          <X className="h-3.5 w-3.5" />
          {error}
        </p>
      )}
    </div>
  );
}
