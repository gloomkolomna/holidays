export function errorMessage(e: unknown, fallback = 'Ошибка'): string {
  const detail = (e as any)?.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d: any) => d?.msg).filter((m: any) => typeof m === 'string' && m);
    if (msgs.length) return msgs.join('; ');
  }
  if (detail && typeof detail === 'object') {
    const msg = (detail as any).message ?? (detail as any).code;
    if (typeof msg === 'string' && msg) return msg;
  }
  return fallback;
}
