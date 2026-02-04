import type { AIContextResult } from '@/stores/ai/AIContextStore';

export type AIContextResultForCopy = Pick<
  AIContextResult,
  'summary' | 'relatedIssues' | 'relatedDocs' | 'tasks' | 'prompts'
>;

export function generateFullContextMarkdown(result: AIContextResultForCopy): string {
  const sections: string[] = [];
  const heading = result.summary
    ? `# ${result.summary.issueIdentifier}: ${result.summary.title}`
    : '# AI Context';
  sections.push(heading);

  if (result.summary) {
    sections.push(`## Summary\n${result.summary.summaryText}`);
  }

  const relatedIssuesMd = buildRelatedIssuesSection(result.relatedIssues);
  if (relatedIssuesMd) sections.push(`## Related Issues\n${relatedIssuesMd}`);

  const relatedDocsMd = buildRelatedDocsSection(result.relatedDocs);
  if (relatedDocsMd) sections.push(`## Related Documents\n${relatedDocsMd}`);

  const tasksMd = buildTasksSection(result.tasks);
  if (tasksMd) sections.push(`## Implementation Tasks\n${tasksMd}`);

  const promptsMd = buildPromptsSection(result.prompts);
  if (promptsMd) sections.push(`## Ready-to-Use Prompts\n${promptsMd}`);

  return sections.join('\n\n');
}

export function generateSectionMarkdown(section: string, result: AIContextResultForCopy): string {
  switch (section) {
    case 'summary':
      return result.summary?.summaryText ?? '';
    case 'related_issues':
      return buildRelatedIssuesSection(result.relatedIssues);
    case 'related_docs':
      return buildRelatedDocsSection(result.relatedDocs);
    case 'tasks':
      return buildTasksSection(result.tasks);
    case 'prompts':
      return buildPromptsSection(result.prompts);
    default:
      return '';
  }
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function buildRelatedIssuesSection(issues: AIContextResultForCopy['relatedIssues']): string {
  if (issues.length === 0) return '';
  return issues
    .map((i) => `- ${i.identifier} (${i.relationType}): ${i.title} — ${i.status}\n  ${i.summary}`)
    .join('\n');
}

function buildRelatedDocsSection(docs: AIContextResultForCopy['relatedDocs']): string {
  if (docs.length === 0) return '';
  return docs
    .map((d) => `- [${d.docType}] ${d.title}${d.summary ? `\n  ${d.summary}` : ''}`)
    .join('\n');
}

function buildTasksSection(tasks: AIContextResultForCopy['tasks']): string {
  if (tasks.length === 0) return '';
  return tasks
    .map((t, idx) => {
      let line = `${idx + 1}. ${t.title} (${t.estimate})`;
      if (t.dependencies.length > 0) {
        line += `\n   Dependencies: ${t.dependencies.join(', ')}`;
      }
      return line;
    })
    .join('\n');
}

function buildPromptsSection(prompts: AIContextResultForCopy['prompts']): string {
  if (prompts.length === 0) return '';
  return prompts
    .map((p) => `### Task ${p.taskId}: ${p.title}\n\`\`\`\n${p.content}\n\`\`\``)
    .join('\n\n');
}
