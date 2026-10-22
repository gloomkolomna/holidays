import { describe, expect, it } from 'vitest';
import { errorMessage } from '../api/errors';

describe('errorMessage', () => {
  it('возвращает строковый detail', () => {
    const e = { response: { data: { detail: 'Праздник не активен' } } };
    expect(errorMessage(e, 'fallback')).toBe('Праздник не активен');
  });

  it('достаёт message из объектного detail гейтов', () => {
    const e = { response: { data: { detail: { code: 'members_only', message: 'Нужна подписка' } } } };
    expect(errorMessage(e, 'fallback')).toBe('Нужна подписка');
  });

  it('склеивает массив 422 из msg', () => {
    const e = { response: { data: { detail: [{ msg: 'Поле обязательно' }, { msg: 'Неверная дата' }, {}] } } };
    expect(errorMessage(e, 'fallback')).toBe('Поле обязательно; Неверная дата');
  });

  it('отдаёт fallback при пустом detail и без ответа', () => {
    expect(errorMessage({}, 'Ошибка сети')).toBe('Ошибка сети');
    expect(errorMessage(null, 'Ошибка сети')).toBe('Ошибка сети');
    expect(errorMessage({ response: { data: {} } }, 'Ошибка сети')).toBe('Ошибка сети');
  });
});
