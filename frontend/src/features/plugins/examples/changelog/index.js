/**
 * Changelog Plugin
 *
 * Demonstrates all three extension points: block types, slash commands, and actions.
 * Inserts a structured changelog block into the editor.
 */

function onActivate(sdk) {
  // Register block type renderer
  sdk.editor.registerBlockRenderer('changelog', {
    label: 'Changelog',
    icon: 'FileText',
  });

  // Helper: insert a changelog block at cursor
  function insertChangelog() {
    sdk.editor.insertBlock('changelog', {
      title: 'Changelog',
      date: new Date().toISOString().split('T')[0],
      entries: ['New feature added', 'Bug fixes', 'Performance improvements'],
    });
  }

  // Register slash command
  sdk.commands.register('/changelog', {
    label: 'Insert Changelog',
    description: 'Generate a changelog block',
    handler: insertChangelog,
  });

  // Register action (command palette)
  sdk.actions.register('changelog.generate', {
    label: 'Generate Changelog',
    handler: insertChangelog,
  });

  sdk.ui.showToast('Changelog plugin activated');
}
