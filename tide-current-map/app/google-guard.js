// This reduces accidental/repeated browser reloads. It is not a billing cap:
// storage can be cleared, and a public browser key can be used without this code.
const GOOGLE_LOAD_HISTORY = 'shio-google-load-history-v1';
export function claimGoogleMapLoad(storage, now = Date.now()) {
 if (!Number.isFinite(now)) return false;
 try {
  const raw = storage.getItem(GOOGLE_LOAD_HISTORY);
  const history = raw === null ? [] : JSON.parse(raw);
  if (!Array.isArray(history) || history.some(t => !Number.isFinite(t))) return false;
  const recent = history.filter(t => t > now - 3600000 && t <= now);
  if (recent.length >= 20 || recent.filter(t => t > now - 60000).length >= 3) return false;
  storage.setItem(GOOGLE_LOAD_HISTORY, JSON.stringify([...recent, now]));
  return true;
 } catch {
  // When browser storage is unavailable, retain the standard map.
  return false;
 }
}
