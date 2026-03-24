/**
 * Retro Plugin
 *
 * Inserts a retrospective board for team reviews.
 * Demonstrates block types, slash commands, and actions.
 */

function onActivate(sdk) {
  // Register block type renderer
  sdk.editor.registerBlockRenderer('retro', {
    label: 'Retrospective',
    icon: 'MessageSquare',
  });

  // Helper: insert a retro board block at cursor
  function insertRetro() {
    sdk.editor.insertBlock('retro', {
      title: 'Sprint Retrospective',
      wentWell: [''],
      didntGoWell: [''],
      actionItems: [''],
    });
  }

  // Register slash command
  sdk.commands.register('/retro', {
    label: 'Insert Retro Board',
    description: 'Insert a retrospective board',
    handler: insertRetro,
  });

  // Register action (command palette)
  sdk.actions.register('retro.insert', {
    label: 'Insert Retro Board',
    handler: insertRetro,
  });

  sdk.ui.showToast('Retro plugin activated');
}
