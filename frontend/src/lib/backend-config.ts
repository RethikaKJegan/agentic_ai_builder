/** Server-only deployment configuration, also validated by instrumentation at startup. */
export function backendConfig() {
  const upstream = new URL(process.env['BUILDER_API_URL'] || 'http://127.0.0.1:8000');
  const host = upstream.hostname;
  const privateHost = ['localhost', '127.0.0.1', '[::1]'].includes(host) ||
    /^10\.\d+\.\d+\.\d+$/.test(host) || /^192\.168\.\d+\.\d+$/.test(host) ||
    /^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$/.test(host) || /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(host);
  if (!['http:', 'https:'].includes(upstream.protocol) || !privateHost || upstream.username || upstream.password ||
      upstream.search || upstream.hash || upstream.pathname !== '/') throw new Error('Configure a private BUILDER_API_URL without credentials, path or query.');
  const production = process.env['BUILDER_ENVIRONMENT'] === 'production';
  const defaults = production ? ['https://praxi.bellcorpstudio.com'] :
    ['localhost', '127.0.0.1', '[::1]'].flatMap((h) => [3000, 3001, 3100].map((p) => `http://${h}:${p}`));
  const origins = (process.env['BUILDER_UI_ORIGINS']?.split(',') || defaults).map((entry) => entry.trim());
  for (const origin of origins) {
    const url = new URL(origin);
    if (url.origin !== origin || url.username || url.password || !['http:', 'https:'].includes(url.protocol) ||
        (production ? url.protocol !== 'https:' : !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) throw new Error('Configure exact authorized UI origins.');
  }
  const plannerSeconds = Number(process.env['BUILDER_PLANNER_TIMEOUT_SECONDS'] || 180);
  // LivePlannerProvider may make two generation attempts, each with a correction.
  if (!Number.isInteger(plannerSeconds) || plannerSeconds < 30 || plannerSeconds > 300) throw new Error('Invalid planner deadline.');
  return { upstream, origins, normalTimeout: 30_000, plannerTimeout: plannerSeconds * 4_000 + 30_000, maxBody: 2 * 1024 * 1024 };
}
