'use client';

/**
 * FormRenderer — Renders Form PM blocks with 10 field types.
 *
 * FR-027: 10 field types (text, textarea, number, date, select, multiselect, checkbox, rating, email, url)
 * FR-028: Field validation (required, min, max, pattern)
 * FR-029: Response collection and submission
 *
 * @module pm-blocks/renderers/FormRenderer
 */
import { useCallback, useMemo, useState } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { pmBlockStyles } from '../pm-block-styles';
import type { PMRendererProps } from '../PMBlockNodeView';

/* ── Data types ──────────────────────────────────────────────────────── */

type FieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'date'
  | 'select'
  | 'multiselect'
  | 'checkbox'
  | 'rating'
  | 'email'
  | 'url';

interface FormField {
  id: string;
  label: string;
  type: FieldType;
  required?: boolean;
  placeholder?: string;
  options?: string[];
  min?: number;
  max?: number;
  pattern?: string;
}

interface FormData {
  title: string;
  description?: string;
  fields: FormField[];
  responses: Record<string, unknown>;
  responseCount: number;
}

const DEFAULT_DATA: FormData = {
  title: 'Untitled Form',
  fields: [
    { id: 'f1', label: 'Name', type: 'text', required: true },
    { id: 'f2', label: 'Email', type: 'email', required: true },
    { id: 'f3', label: 'Comments', type: 'textarea' },
  ],
  responses: {},
  responseCount: 0,
};

/* ── Field renderer ──────────────────────────────────────────────────── */

function FormFieldInput({
  field,
  value,
  onChange,
  onBlur,
  readOnly,
  error,
}: {
  field: FormField;
  value: unknown;
  onChange: (val: unknown) => void;
  onBlur?: () => void;
  readOnly: boolean;
  error?: string;
}) {
  const baseInput = pmBlockStyles.form.fieldInput;

  switch (field.type) {
    case 'text':
    case 'email':
    case 'url':
      return (
        <>
          <input
            type={field.type}
            className={baseInput}
            placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={readOnly}
            required={field.required}
            aria-label={field.label}
          />
          {error && <p className={pmBlockStyles.form.fieldError}>{error}</p>}
        </>
      );

    case 'textarea':
      return (
        <>
          <textarea
            className={cn(baseInput, 'min-h-[80px] resize-y')}
            placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={readOnly}
            aria-label={field.label}
          />
          {error && <p className={pmBlockStyles.form.fieldError}>{error}</p>}
        </>
      );

    case 'number':
      return (
        <>
          <input
            type="number"
            className={baseInput}
            value={(value as number) ?? ''}
            onChange={(e) => onChange(e.target.valueAsNumber)}
            onBlur={onBlur}
            disabled={readOnly}
            min={field.min}
            max={field.max}
            aria-label={field.label}
          />
          {error && <p className={pmBlockStyles.form.fieldError}>{error}</p>}
        </>
      );

    case 'date':
      return (
        <input
          type="date"
          className={baseInput}
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={readOnly}
          aria-label={field.label}
        />
      );

    case 'select':
      return (
        <select
          className={baseInput}
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={readOnly}
          aria-label={field.label}
        >
          <option value="">Select...</option>
          {field.options?.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );

    case 'multiselect': {
      const selected = (value as string[]) ?? [];
      return (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label={field.label}>
          {field.options?.map((opt) => (
            <label
              key={opt}
              className={cn(
                'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs cursor-pointer transition-colors',
                selected.includes(opt)
                  ? 'bg-primary/10 border-primary text-primary'
                  : 'hover:bg-accent'
              )}
            >
              <input
                type="checkbox"
                className="sr-only"
                checked={selected.includes(opt)}
                onChange={(e) => {
                  const next = e.target.checked
                    ? [...selected, opt]
                    : selected.filter((s) => s !== opt);
                  onChange(next);
                }}
                disabled={readOnly}
              />
              {opt}
            </label>
          ))}
        </div>
      );
    }

    case 'checkbox':
      return (
        <label className="inline-flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
            disabled={readOnly}
            aria-label={field.label}
          />
          <span>{field.placeholder || field.label}</span>
        </label>
      );

    case 'rating': {
      const rating = (value as number) ?? 0;
      const max = field.max ?? 5;
      return (
        <div className={pmBlockStyles.form.ratingStars} role="radiogroup" aria-label={field.label}>
          {Array.from({ length: max }, (_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => !readOnly && onChange(i + 1)}
              disabled={readOnly}
              aria-label={`${i + 1} star${i > 0 ? 's' : ''}`}
            >
              <Star
                className={cn(
                  'size-5 transition-colors',
                  i < rating
                    ? pmBlockStyles.form.ratingStarFilled
                    : pmBlockStyles.form.ratingStarEmpty
                )}
              />
            </button>
          ))}
        </div>
      );
    }

    default:
      return <input type="text" className={baseInput} disabled aria-label={field.label} />;
  }
}

/* ── Main renderer ───────────────────────────────────────────────────── */

export function FormRenderer({ data: rawData, readOnly, onDataChange }: PMRendererProps) {
  const data = useMemo<FormData>(() => {
    return { ...DEFAULT_DATA, ...(rawData as Partial<FormData>) };
  }, [rawData]);

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateField = useCallback((field: FormField, value: unknown): string | null => {
    if (field.required && (value === undefined || value === null || value === '')) {
      return `${field.label} is required`;
    }
    if (field.type === 'email' && typeof value === 'string' && value) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Invalid email address';
    }
    if (field.type === 'url' && typeof value === 'string' && value) {
      try {
        new URL(value);
      } catch {
        return 'Invalid URL';
      }
    }
    if (field.type === 'number' && typeof value === 'number') {
      if (field.min != null && value < field.min) return `Minimum value is ${field.min}`;
      if (field.max != null && value > field.max) return `Maximum value is ${field.max}`;
    }
    if (field.pattern && typeof value === 'string' && value) {
      try {
        if (value.length <= 1000 && !new RegExp(field.pattern).test(value))
          return `Does not match required format`;
      } catch {
        // Invalid regex pattern from form config — skip validation
      }
    }
    return null;
  }, []);

  const handleFieldBlur = useCallback(
    (fieldId: string) => {
      const field = data.fields.find((f) => f.id === fieldId);
      if (!field) return;
      const error = validateField(field, data.responses[fieldId]);
      setErrors((prev) => {
        if (error) return { ...prev, [fieldId]: error };
        const next = { ...prev };
        delete next[fieldId];
        return next;
      });
    },
    [data.fields, data.responses, validateField]
  );

  const handleFieldChange = useCallback(
    (fieldId: string, value: unknown) => {
      const newResponses = { ...data.responses, [fieldId]: value };
      onDataChange({ ...data, responses: newResponses });
      // Clear error on change
      if (errors[fieldId]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[fieldId];
          return next;
        });
      }
    },
    [data, onDataChange, errors]
  );

  const handleSubmit = useCallback(() => {
    const newErrors: Record<string, string> = {};
    for (const field of data.fields) {
      const error = validateField(field, data.responses[field.id]);
      if (error) newErrors[field.id] = error;
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    onDataChange({ ...data, responseCount: data.responseCount + 1, responses: {} });
    toast.success('Response recorded');
  }, [data, validateField, onDataChange]);

  return (
    <div data-testid="form-renderer">
      {/* Title */}
      <h3 className="text-base font-semibold leading-snug">{data.title}</h3>
      {data.description && <p className="mt-1 text-sm text-muted-foreground">{data.description}</p>}

      {/* Fields */}
      <div className={cn('mt-4', pmBlockStyles.form.fieldGroup)}>
        {data.fields.map((field) => (
          <div key={field.id}>
            <label className={pmBlockStyles.form.fieldLabel}>
              {field.label}
              {field.required && <span className={pmBlockStyles.form.fieldRequired}>*</span>}
            </label>
            <div className="mt-1.5">
              <FormFieldInput
                field={field}
                value={data.responses[field.id]}
                onChange={(val) => handleFieldChange(field.id, val)}
                onBlur={() => handleFieldBlur(field.id)}
                readOnly={readOnly}
                error={errors[field.id]}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Submit section */}
      <div className={pmBlockStyles.form.submitSection}>
        <span className="text-xs text-muted-foreground">
          {data.responseCount} response{data.responseCount !== 1 ? 's' : ''}
        </span>
        {!readOnly && (
          <button
            type="button"
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={handleSubmit}
          >
            Record Response
          </button>
        )}
      </div>
    </div>
  );
}
