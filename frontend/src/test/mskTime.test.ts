import { describe, expect, it } from 'vitest';
import { msUntilNextMskMidnight } from '../utils/mskTime';

describe('msUntilNextMskMidnight', () => {
  it('полминуты до полуночи МСК', () => {
    const now = new Date('2026-10-22T20:59:30Z');
    expect(msUntilNextMskMidnight(now)).toBe(30000);
  });

  it('ровно полночь МСК — следующая через 24 часа', () => {
    const now = new Date('2026-10-22T21:00:00Z');
    expect(msUntilNextMskMidnight(now)).toBe(24 * 3600 * 1000);
  });

  it('момент срабатывания всегда 00:00:00 МСК независимо от таймзоны', () => {
    const now = new Date();
    const ms = msUntilNextMskMidnight(now);
    expect(ms).toBeGreaterThan(0);
    expect(ms).toBeLessThanOrEqual(24 * 3600 * 1000);
    const mskFire = new Date(now.getTime() + ms + 180 * 60000);
    expect(mskFire.getUTCHours()).toBe(0);
    expect(mskFire.getUTCMinutes()).toBe(0);
    expect(mskFire.getUTCSeconds()).toBe(0);
    expect(mskFire.getUTCMilliseconds()).toBe(0);
  });
});
