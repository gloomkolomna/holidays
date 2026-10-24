import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AxiosError } from 'axios';
import client, { clearToken } from '../api/client';
import { api } from '../api/endpoints';

function file(name: string): File {
  return new File([new Uint8Array([1, 2, 3])], name, { type: 'image/jpeg' });
}

function networkError(config: any) {
  return new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, undefined, undefined);
}

function withAdapter(handler: (config: any) => any) {
  (client.defaults as any).adapter = async (config: any) => {
    const outcome = handler(config);
    if (outcome instanceof Error) throw outcome;
    const validate = config.validateStatus || ((s: number) => s >= 200 && s < 300);
    if (!validate(outcome.status)) {
      const response = { ...outcome, config };
      throw new AxiosError(`Request failed with status code ${outcome.status}`, AxiosError.ERR_BAD_REQUEST, config, null, response);
    }
    return outcome;
  };
}

describe('reportTask — цикл ретраев', () => {
  beforeEach(() => {
    clearToken();
    localStorage.clear();
    (URL as any).createObjectURL = () => { throw new TypeError('not supported'); };
  });

  afterEach(() => {
    vi.useRealTimers();
    delete (URL as any).createObjectURL;
    (client.defaults as any).adapter = undefined;
  });

  it('две сетевые ошибки — успех на третьей, ровно 3 POST-а одной FormData', async () => {
    let calls = 0;
    const bodies: unknown[] = [];
    withAdapter((config) => {
      calls++;
      bodies.push(config.data);
      if (calls < 3) return networkError(config);
      return {
        status: 200,
        data: { ok: true, card_id: 7, collected: true, mode: 'norm' },
        statusText: 'OK',
        headers: {},
        config,
      };
    });

    vi.useFakeTimers();
    const promise = api.reportTask(5, 100, file('a.jpg'), file('b.jpg'));
    await vi.advanceTimersByTimeAsync(4000);
    const res = await promise;

    expect(calls).toBe(3);
    expect(res.collected).toBe(true);
    expect(bodies[0]).toBe(bodies[1]);
    expect(bodies[1]).toBe(bodies[2]);
  });

  it('409 на второй попытке резолвится как уже принято', async () => {
    let calls = 0;
    withAdapter((config) => {
      calls++;
      if (calls === 1) return networkError(config);
      return { status: 409, data: { detail: 'Задание уже закрыто' }, statusText: 'Conflict', headers: {}, config };
    });

    vi.useFakeTimers();
    const promise = api.reportTask(5, 100, file('a.jpg'), file('b.jpg'));
    await vi.advanceTimersByTimeAsync(2000);
    const res = await promise;

    expect(calls).toBe(2);
    expect(res.accepted).toBe(true);
    expect(res.card_id).toBeNull();
  });

  it('таймаут не ретраится — одна попытка', async () => {
    let calls = 0;
    withAdapter((config) => {
      calls++;
      return new AxiosError('timeout of 120000ms exceeded', AxiosError.ECONNABORTED, config, undefined, undefined);
    });

    await expect(api.reportTask(5, 100, file('a.jpg'), file('b.jpg'))).rejects.toBeDefined();
    expect(calls).toBe(1);
  });

  it('сетевая ошибка на тяжёлом теле — максимум две попытки', async () => {
    let calls = 0;
    withAdapter((config) => {
      calls++;
      return networkError(config);
    });
    const big = new File([new Uint8Array(6 * 1024 * 1024)], 'big.jpg', { type: 'image/jpeg' });

    vi.useFakeTimers();
    const promise = api.reportTask(5, 100, big, file('b.jpg'));
    const captured = promise.catch((e: any) => e);
    await vi.advanceTimersByTimeAsync(5000);
    const err = await captured;
    expect(err?.code).toBe('ERR_NETWORK');
    expect(calls).toBe(2);
  });
});
