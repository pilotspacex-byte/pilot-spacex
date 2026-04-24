/**
 * ProposalEnvelope fixtures for tests + storybook.
 * Use via spread to override any field:
 *   const proposal = { ...mockTextProposal(), status: 'applied' };
 */

import type {
  ProposalEnvelope,
  TextDiffPayload,
  FieldsDiffPayload,
} from '../types';

const ISO_NOW = '2026-04-24T12:00:00.000Z';

export function mockTextDiffPayload(): TextDiffPayload {
  return {
    kind: 'text',
    hunks: [
      { op: 'equal', text: 'The agent should ' },
      { op: 'delete', text: 'log failures but not retry.\n' },
      {
        op: 'insert',
        text: 'retry up to 3 times with exponential back-off before logging failure.\n',
      },
      { op: 'equal', text: 'Nothing else changes.' },
    ],
  };
}

export function mockFieldsDiffPayload(): FieldsDiffPayload {
  return {
    kind: 'fields',
    rows: [
      { field: 'priority', label: 'Priority', before: 'low', after: 'high' },
      { field: 'assignee', label: 'Assignee', before: null, after: 'tin@example.com' },
    ],
  };
}

export function mockTextProposal(overrides: Partial<ProposalEnvelope> = {}): ProposalEnvelope {
  return {
    id: 'prop-text-1',
    workspaceId: 'ws-1',
    sessionId: 'sess-1',
    messageId: 'msg-1',
    targetArtifactType: 'ISSUE',
    targetArtifactId: 'issue-abcdef12',
    intentTool: 'update_issue',
    intentArgs: { issue_id: 'issue-abcdef12', description: '…' },
    diffKind: 'text',
    diffPayload: mockTextDiffPayload(),
    reasoning:
      'I noticed you mentioned flaky tests three times this session — raising priority surfaces this to the top.',
    status: 'pending',
    appliedVersion: null,
    decidedAt: null,
    decidedBy: null,
    createdAt: ISO_NOW,
    mode: 'act',
    acceptDisabled: false,
    persist: true,
    planPreviewOnly: false,
    ...overrides,
  };
}

export function mockFieldsProposal(overrides: Partial<ProposalEnvelope> = {}): ProposalEnvelope {
  return {
    ...mockTextProposal(),
    id: 'prop-fields-1',
    targetArtifactId: 'issue-11112222',
    intentTool: 'update_issue_fields',
    diffKind: 'fields',
    diffPayload: mockFieldsDiffPayload(),
    reasoning: null,
    ...overrides,
  };
}

export function mockAppliedProposal(overrides: Partial<ProposalEnvelope> = {}): ProposalEnvelope {
  return {
    ...mockTextProposal(),
    id: 'prop-applied-1',
    status: 'applied',
    appliedVersion: 4,
    decidedAt: ISO_NOW,
    decidedBy: 'user-1',
    ...overrides,
  };
}

export function mockRejectedProposal(overrides: Partial<ProposalEnvelope> = {}): ProposalEnvelope {
  return {
    ...mockTextProposal(),
    id: 'prop-rejected-1',
    status: 'rejected',
    decidedAt: ISO_NOW,
    decidedBy: 'user-1',
    ...overrides,
  };
}

export function mockPlanModeProposal(overrides: Partial<ProposalEnvelope> = {}): ProposalEnvelope {
  return {
    ...mockTextProposal(),
    id: 'prop-plan-1',
    mode: 'plan',
    acceptDisabled: true,
    planPreviewOnly: true,
    ...overrides,
  };
}

export function mockDraftModeProposal(overrides: Partial<ProposalEnvelope> = {}): ProposalEnvelope {
  return {
    ...mockTextProposal(),
    id: 'prop-draft-1',
    mode: 'draft',
    persist: false,
    ...overrides,
  };
}
