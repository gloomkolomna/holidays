import { describe, it, expect } from 'vitest';
import { isAlreadyAccepted, isNetworkError, maxAttemptsFor } from '../utils/upload';

describe('isNetworkError', () => {
  it('true только для сетевой ошибки без ответа', () => {
    expect(isNetworkError({ code: 'ERR_NETWORK' })).toBe(true);
    expect(isNetworkError({ code: 'ERR_NETWORK', response: undefined })).toBe(true);
  });

  it('false при наличии ответа, таймауте или отмене', () => {
    expect(isNetworkError({ code: 'ERR_NETWORK', response: { status: 500 } })).toBe(false);
    expect(isNetworkError({ code: 'ECONNABORTED' })).toBe(false);
    expect(isNetworkError({ code: 'ERR_CANCELED' })).toBe(false);
    expect(isNetworkError(null)).toBe(false);
    expect(isNetworkError(undefined)).toBe(false);
  });
});

describe('isAlreadyAccepted', () => {
  it('409/429 на повторной попытке — уже принято', () => {
    expect(isAlreadyAccepted({ response: { status: 409 } }, 2)).toBe(true);
    expect(isAlreadyAccepted({ response: { status: 429 } }, 3)).toBe(true);
  });

  it('первая попытка и другие статусы — не успех', () => {
    expect(isAlreadyAccepted({ response: { status: 409 } }, 1)).toBe(false);
    expect(isAlreadyAccepted({ response: { status: 400 } }, 2)).toBe(false);
    expect(isAlreadyAccepted({ response: { status: 500 } }, 2)).toBe(false);
    expect(isAlreadyAccepted({ code: 'ERR_NETWORK' }, 2)).toBe(false);
    expect(isAlreadyAccepted(null, 2)).toBe(false);
  });
});

describe('maxAttemptsFor', () => {
  it('3 попытки для обычного тела, 2 для тяжёлого (>5 МБ)', () => {
    expect(maxAttemptsFor(1024)).toBe(3);
    expect(maxAttemptsFor(5 * 1024 * 1024)).toBe(3);
    expect(maxAttemptsFor(5 * 1024 * 1024 + 1)).toBe(2);
    expect(maxAttemptsFor(45 * 1024 * 1024)).toBe(2);
  });
});
