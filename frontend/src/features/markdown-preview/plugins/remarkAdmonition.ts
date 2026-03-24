/**
 * remarkAdmonition - Remark plugin for custom admonition containers.
 *
 * Transforms :::note, :::warning, :::tip, :::danger, :::info container directives
 * (from remark-directive) into <div data-admonition="{type}" class="admonition admonition-{type}">
 * elements in the hast output.
 *
 * Requires remark-directive to be loaded before this plugin in the remark chain.
 */
import { visit } from 'unist-util-visit';
import type { Root } from 'mdast';

/** Supported admonition types */
const ADMONITION_TYPES = new Set(['note', 'warning', 'tip', 'danger', 'info']);

/**
 * Remark plugin that converts container directives (:::type) into admonition divs.
 */
export function remarkAdmonition() {
  return (tree: Root) => {
    visit(tree, (node) => {
      if (
        node.type === 'containerDirective' &&
        'name' in node &&
        typeof node.name === 'string' &&
        ADMONITION_TYPES.has(node.name)
      ) {
        const name = node.name;
        const data = (node.data ||= {});
        data.hName = 'div';
        data.hProperties = {
          'data-admonition': name,
          className: ['admonition', `admonition-${name}`],
        };
      }
    });
  };
}
