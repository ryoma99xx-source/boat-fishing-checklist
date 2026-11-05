export function mapConfigResponse(env = {}, request) {
 const key = typeof env.GOOGLE_MAPS_BROWSER_KEY === 'string' ? env.GOOGLE_MAPS_BROWSER_KEY.trim() : '';
 const enabled = String(env.GOOGLE_MAPS_ENABLED || '').trim().toLowerCase() === 'true';
 const origin = 'https://tide-current-map.cutlassfish.tokyo';
 let allowed = false;
 try {
  allowed = request?.method === 'GET' && new URL(request.url).origin === origin;
  const suppliedOrigin = request?.headers.get('Origin');
  const referrer = request?.headers.get('Referer');
  if (suppliedOrigin && suppliedOrigin !== origin) allowed = false;
  if (request?.headers.get('Sec-Fetch-Site') === 'cross-site') allowed = false;
  if (referrer && new URL(referrer).origin !== origin) allowed = false;
 } catch { allowed = false; }
 // These checks reduce unwanted key delivery. Google must also enforce website
 // and API restrictions; request headers and browser-side code are not a budget.
 return Response.json(enabled && key && allowed ? {provider:'google',apiKey:key} : {provider:'standard'}, {
  headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
 });
}
