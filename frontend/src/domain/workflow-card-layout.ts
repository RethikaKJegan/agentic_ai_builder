/** Presentation only: canonical task instructions and identities stay unchanged. */
export const subwayCardSize = {width: 280, height: 168};
export function workflowCardTitle(id: string, label: string) {
  const text = label.replace(/\s+/g, ' ').trim();
  if (text.length <= 90) return text;
  const name = id.replace(/^(?:task|action)[_-]/, '').replace(/[_-]+/g, ' ').trim();
  if (name && name.length <= 90) return name.charAt(0).toUpperCase() + name.slice(1);
  return text.slice(0, 87).trimEnd() + '…';
}
