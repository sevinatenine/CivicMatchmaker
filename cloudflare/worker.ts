/**
 * Hosted web app on Cloudflare (free Workers plan): one Worker serves the exported web app
 * (./dist) and forwards /api/* to the Python API server, which runs on Render (render.yaml).
 *
 *   https://<worker>/            -> static web app
 *   https://<worker>/api/run     -> API_ORIGIN  POST /run  (server-sent events, streamed through)
 *   https://<worker>/api/status  -> API_ORIGIN  GET  /status
 *
 * Expo Go on phones uses the same https://<worker>/api URL in hosted mode.
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) {
      return env.ASSETS.fetch(request);
    }
    if (!env.API_ORIGIN) {
      return Response.json({ error: 'API_ORIGIN is not set; run npm run deploy.' }, { status: 503 });
    }
    // Streaming proxy: the response body (SSE) is passed through without buffering
    const target = new URL(url.pathname.slice('/api'.length) + url.search, env.API_ORIGIN);
    return fetch(new Request(target, request));
  },
} satisfies ExportedHandler<Env>;
