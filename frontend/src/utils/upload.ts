export interface SentFileStat {
  name: string;
  size: number;
  type: string;
  compressed: boolean;
}

export interface UploadFailMeta {
  attempts: number;
  uploadedBytes: number;
  sent: SentFileStat[];
}

export function isNetworkError(e: any): boolean {
  return !e?.response && e?.code === 'ERR_NETWORK';
}

export function isAlreadyAccepted(e: any, attempt: number): boolean {
  const status = e?.response?.status;
  return attempt > 1 && (status === 409 || status === 429);
}
