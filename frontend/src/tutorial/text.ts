/** Every sentence on its own line (callers decide whether there is room). */
export function splitSentences(text: string): string {
  return text.split(/(?<=[.!?])\s+/).join('\n');
}
