/**
 * Standup Plugin
 *
 * Inserts a structured daily standup template into the editor.
 * Demonstrates block types, slash commands, and actions.
 */

function onActivate(sdk) {
  // Register block type renderer
  sdk.editor.registerBlockRenderer('standup', {
    label: 'Standup',
    icon: 'Users',
  });

  // Helper: insert a standup block at cursor
  function insertStandup() {
    sdk.editor.insertBlock('standup', {
      date: new Date().toISOString().split('T')[0],
      yesterday: [''],
      today: [''],
      blockers: [''],
    });
  }

  // Register slash command
  sdk.commands.register('/standup', {
    label: 'Insert Standup',
    description: 'Insert a daily standup template',
    handler: insertStandup,
  });

  // Register action (command palette)
  sdk.actions.register('standup.insert', {
    label: 'Insert Standup Template',
    handler: insertStandup,
  });

  sdk.ui.showToast('Standup plugin activated');
}
