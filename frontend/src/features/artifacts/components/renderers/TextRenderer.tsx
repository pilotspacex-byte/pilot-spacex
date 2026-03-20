'use client';

interface TextRendererProps {
  content: string;
}

export function TextRenderer({ content }: TextRendererProps) {
  return (
    <div className="p-6">
      <pre className="text-sm font-mono whitespace-pre-wrap break-words text-foreground">
        {content}
      </pre>
    </div>
  );
}
