/** Allow importing CSS files (e.g. xterm.js stylesheet via dynamic import). */
declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}
