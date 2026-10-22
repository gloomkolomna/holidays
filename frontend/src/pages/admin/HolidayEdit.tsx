import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, type HolidayCard, type HolidayCategoryDetail, type HolidayDetail, type HolidayInput } from '../../api/endpoints';
import { errorMessage } from '../../api/errors';
import { mediaUrl } from '../../api/media';
import ConfirmDialog from '../../components/ConfirmDialog';
import { PALETTES } from '../../theme';

function toLocalInput(iso: string): string {
  return iso.slice(0, 10);
}

function dayLabel(day: string): string {
  return day.split('-').reverse().join('.');
}

function emptyForm(): HolidayInput {
  const now = new Date();
  return {
    title: '',
    starts_at: toLocalInput(new Date(now.getTime() + 24 * 3600 * 1000).toISOString()),
    ends_at: toLocalInput(new Date(now.getTime() + 5 * 24 * 3600 * 1000).toISOString()),
    animation_size: 50,
    animation_count: 14,
    animation_opacity: 100,
    shop_enabled: true,
  };
}

interface SlotDraft {
  title: string;
  task: string;
}

function GridView({ detail }: { detail: HolidayDetail }) {
  if (detail.categories.length === 0 || detail.days.length === 0) return null;

  return (
    <div className="fm-card" style={{ marginTop: 12 }}>
      <h3>Сетка праздника</h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
        Категории × дни. ✅ — карточка заполнена, ⬜ — пусто. Клик по строке — к категории.
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table className="fm-table">
          <thead>
            <tr>
              <th>Категория</th>
              {detail.days.map((d) => (
                <th key={d} style={{ textAlign: 'center' }}>{dayLabel(d)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {detail.categories.map((cat) => {
              const byDay = new Map(cat.cards.filter((c) => c.day !== null).map((c) => [c.day, c]));
              return (
                <tr
                  key={cat.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => document.getElementById(`cat-${cat.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                >
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {cat.title} <span style={{ color: 'var(--text-muted)' }}>({cat.norm_crosses})</span>
                  </td>
                  {detail.days.map((d) => {
                    const card = byDay.get(d);
                    const filled = !!card?.title.trim();
                    return (
                      <td key={d} style={{ textAlign: 'center' }} title={card ? (filled ? card.title : 'пусто') : '—'}>
                        {card ? (filled ? '✅' : '⬜') : '—'}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function HolidayEdit() {
  const { id } = useParams();
  const holidayId = id ? Number(id) : null;
  const isEdit = holidayId != null && !Number.isNaN(holidayId);

  const navigate = useNavigate();
  const [form, setForm] = useState<HolidayInput>(emptyForm());
  const [detail, setDetail] = useState<HolidayDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(!isEdit);

  const [newCategoryTitle, setNewCategoryTitle] = useState('');
  const [newCategoryNorm, setNewCategoryNorm] = useState('500');
  const [extraTitle, setExtraTitle] = useState('');
  const [extraTask, setExtraTask] = useState('');
  const [extraCat, setExtraCat] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<Record<number, SlotDraft>>({});
  const [editExtra, setEditExtra] = useState<number | null>(null);
  const [savedFlash, setSavedFlash] = useState<number | null>(null);
  const [editCat, setEditCat] = useState<{ id: number; title: string; norm: string } | null>(null);
  const [askRemoveCat, setAskRemoveCat] = useState<{ id: number; title: string } | null>(null);
  const [askRemoveCard, setAskRemoveCard] = useState<{ id: number; title: string } | null>(null);

  const loadDetail = useCallback(async (hid: number) => {
    try {
      const d = await api.adminHolidayDetail(hid);
      setDetail(d);
      setForm({
        title: d.title,
        starts_at: toLocalInput(d.starts_at),
        ends_at: toLocalInput(d.ends_at),
        bg_image_url: d.bg_image_url,
        bg_color: d.bg_color,
        palette: d.palette,
        animation_preset: d.animation_preset,
        animation_size: d.animation_size,
        animation_count: d.animation_count,
        animation_opacity: d.animation_opacity,
        shop_enabled: d.shop_enabled,
      });
    } catch (e: any) {
      setError(errorMessage(e, 'Праздник не найден'));
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (holidayId != null) loadDetail(holidayId);
  }, [holidayId, loadDetail]);

  async function submit() {
    setBusy(true);
    setError(null);
    const payload = { ...form, starts_at: `${form.starts_at}T00:00`, ends_at: `${form.ends_at}T23:59` };
    try {
      if (isEdit && holidayId != null) {
        await api.adminUpdateHoliday(holidayId, payload);
        navigate('/admin/holidays');
      } else {
        const created = await api.adminCreateHoliday(payload);
        navigate(`/admin/holidays/${created.id}`);
      }
    } catch (e: any) {
      setError(errorMessage(e, 'Ошибка сохранения'));
    } finally {
      setBusy(false);
    }
  }

  async function addCategory() {
    if (!holidayId || !newCategoryTitle.trim()) return;
    const norm = Number(newCategoryNorm);
    if (!norm || norm <= 0) {
      setError('Норма крестиков должна быть положительным числом');
      return;
    }
    setError(null);
    try {
      await api.adminCreateCategory(holidayId, { title: newCategoryTitle.trim(), norm_crosses: norm });
      setNewCategoryTitle('');
      setNewCategoryNorm('500');
      await loadDetail(holidayId);
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось создать категорию'));
    }
  }

  async function saveCategory() {
    if (!holidayId || !editCat) return;
    const norm = Number(editCat.norm);
    if (!editCat.title.trim() || !norm || norm <= 0) {
      setError('Название и положительная норма обязательны');
      return;
    }
    setError(null);
    try {
      await api.adminUpdateCategory(holidayId, editCat.id, {
        title: editCat.title.trim(),
        norm_crosses: norm,
      });
      setEditCat(null);
      await loadDetail(holidayId);
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось сохранить категорию'));
    }
  }

  async function removeCategory() {
    if (!holidayId || !askRemoveCat) return;
    const { id } = askRemoveCat;
    setAskRemoveCat(null);
    await api.adminDeleteCategory(holidayId, id);
    await loadDetail(holidayId);
  }

  function draftFor(card: HolidayCard): SlotDraft {
    return drafts[card.id] ?? { title: card.title, task: card.task_text || '' };
  }

  function setDraft(card: HolidayCard, patch: Partial<SlotDraft>) {
    setDrafts((prev) => {
      const cur = prev[card.id] ?? { title: card.title, task: card.task_text || '' };
      return { ...prev, [card.id]: { ...cur, ...patch } };
    });
  }

  async function saveSlot(cardId: number) {
    if (!holidayId) return;
    const draft = drafts[cardId];
    if (!draft) return;
    setError(null);
    try {
      await api.adminUpdateCard(holidayId, cardId, {
        title: draft.title.trim(),
        task_text: draft.task.trim() || null,
      });
      setSavedFlash(cardId);
      setTimeout(() => setSavedFlash((cur) => (cur === cardId ? null : cur)), 1500);
      await loadDetail(holidayId);
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[cardId];
        return next;
      });
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось сохранить карточку'));
    }
  }

  async function uploadSlotImage(cardId: number, file: File) {
    if (!holidayId) return;
    await api.adminUploadCardImage(holidayId, cardId, file);
    await loadDetail(holidayId);
  }

  async function clearSlotImage(cardId: number) {
    if (!holidayId) return;
    await api.adminClearCardImage(holidayId, cardId);
    await loadDetail(holidayId);
  }

  async function uploadBg(file: File) {
    if (!holidayId) return;
    await api.adminUploadHolidayBg(holidayId, file);
    await loadDetail(holidayId);
  }

  async function uploadAnimation(file: File) {
    if (!holidayId) return;
    setError(null);
    try {
      await api.adminUploadHolidayAnimation(holidayId, file);
      await loadDetail(holidayId);
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось загрузить анимацию'));
    }
  }

  async function clearAnimation() {
    if (!holidayId) return;
    await api.adminClearHolidayAnimation(holidayId);
    await loadDetail(holidayId);
  }

  async function uploadAudio(file: File) {
    if (!holidayId) return;
    setError(null);
    try {
      await api.adminUploadHolidayAudio(holidayId, file);
      await loadDetail(holidayId);
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось загрузить музыку'));
    }
  }

  async function clearAudio() {
    if (!holidayId) return;
    await api.adminClearHolidayAudio(holidayId);
    await loadDetail(holidayId);
  }

  async function uploadCatTrophy(catId: number, file: File) {
    if (!holidayId) return;
    await api.adminUploadCategoryTrophy(holidayId, catId, file);
    await loadDetail(holidayId);
  }

  async function clearCatTrophy(catId: number) {
    if (!holidayId) return;
    await api.adminClearCategoryTrophy(holidayId, catId);
    await loadDetail(holidayId);
  }

  async function addExtraCard() {
    if (!holidayId || !extraTitle.trim()) return;
    await api.adminCreateExtraCard(holidayId, {
      category_id: extraCat ?? detail?.categories[0]?.id ?? null,
      title: extraTitle.trim(),
      task_text: extraTask.trim() || null,
    });
    setExtraTitle('');
    setExtraTask('');
    await loadDetail(holidayId);
  }

  async function removeExtraCard() {
    if (!holidayId || !askRemoveCard) return;
    const { id } = askRemoveCard;
    setAskRemoveCard(null);
    await api.adminDeleteCard(holidayId, id);
    await loadDetail(holidayId);
  }

  async function saveExtraCard(cardId: number) {
    if (!holidayId) return;
    const draft = drafts[cardId];
    if (!draft || !draft.title.trim()) return;
    setError(null);
    try {
      await api.adminUpdateCard(holidayId, cardId, {
        title: draft.title.trim(),
        task_text: draft.task.trim() || null,
      });
      setEditExtra(null);
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[cardId];
        return next;
      });
      await loadDetail(holidayId);
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось сохранить карточку'));
    }
  }

  function categoryHeader(cat: HolidayCategoryDetail) {
    if (editCat && editCat.id === cat.id) {
      return (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', flex: 1 }}>
          <input
            className="fm-input"
            style={{ flex: 2, minWidth: 140 }}
            value={editCat.title}
            onChange={(e) => setEditCat({ ...editCat, title: e.target.value })}
            placeholder="Название категории"
          />
          <input
            className="fm-input"
            style={{ flex: 1, minWidth: 100 }}
            type="number"
            min={1}
            value={editCat.norm}
            onChange={(e) => setEditCat({ ...editCat, norm: e.target.value })}
            placeholder="Норма"
          />
          <button className="fm-btn fm-btn-sm" onClick={saveCategory}>💾</button>
          <button className="fm-btn fm-btn-sm fm-btn-outline" onClick={() => setEditCat(null)}>✖</button>
        </div>
      );
    }
    return (
      <>
        <h3 style={{ margin: 0 }}>{cat.title}</h3>
        <span className="fm-chip">норма: {cat.norm_crosses} крестиков</span>
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>дней: {cat.cards_count}</span>
        <button
          className="fm-btn fm-btn-xs fm-btn-outline"
          onClick={() => setEditCat({ id: cat.id, title: cat.title, norm: String(cat.norm_crosses) })}
        >
          ✏️ Норма/название
        </button>
        {cat.trophy_image_url && (
          <>
            <img src={mediaUrl(cat.trophy_image_url)} alt="Кубок" style={{ height: 32, borderRadius: 4 }} />
            <button className="fm-btn fm-btn-xs fm-btn-danger" onClick={() => clearCatTrophy(cat.id)}>✖ Кубок</button>
          </>
        )}
        <label className="fm-btn fm-btn-xs fm-btn-outline" style={{ cursor: 'pointer' }}>
          🏆 Кубок
          <input
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = '';
              if (f) uploadCatTrophy(cat.id, f);
            }}
          />
        </label>
        <button
          className="fm-btn fm-btn-xs fm-btn-danger"
          style={{ marginLeft: 'auto' }}
          onClick={() => setAskRemoveCat({ id: cat.id, title: cat.title })}
        >
          🗑
        </button>
      </>
    );
  }

  return (
    <>
      <div className="fm-card">
        <h2>{isEdit ? 'Редактирование праздника' : 'Новый праздник'}</h2>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        {!loaded ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
            <span className="fm-spinner" />
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            <input
              className="fm-input"
              placeholder="Название (Хеллоуин, Рождество…)"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 10 }}>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', minWidth: 0 }}>
                Начало (С)
                <input
                  className="fm-input"
                  type="date"
                  value={form.starts_at}
                  onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
                />
              </label>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', minWidth: 0 }}>
                Окончание (ПО)
                <input
                  className="fm-input"
                  type="date"
                  value={form.ends_at}
                  onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
                />
              </label>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
              Начало — в 00:00, окончание — в 23:59 (МСК), время задаётся автоматически.
              Дни праздника: {(detail?.days || []).map(dayLabel).join(', ') || '—'}.
              Сетка карточек пересоздаётся при смене дат (пустые слоты исчезнувших дней удаляются, заполненные остаются).
            </p>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', flex: 1, minWidth: 160 }}>
                Анимация (пресет)
                <select
                  className="fm-input"
                  value={form.animation_preset || 'none'}
                  onChange={(e) => setForm({ ...form, animation_preset: e.target.value === 'none' ? null : e.target.value })}
                >
                  <option value="none">без анимации</option>
                  <option value="confetti">конфетти 🎊</option>
                  <option value="snow">снежинки ❄️</option>
                  <option value="sparkles">искры ✨</option>
                </select>
              </label>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', flex: 1, minWidth: 160 }}>
                Палитра
                <select
                  className="fm-input"
                  value={form.palette || 'default'}
                  onChange={(e) => setForm({ ...form, palette: e.target.value === 'default' ? null : e.target.value })}
                >
                  {Object.entries(PALETTES).map(([key, p]) => (
                    <option key={key} value={key}>{p.label}</option>
                  ))}
                </select>
              </label>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', flex: 1, minWidth: 150 }}>
                Размер силуэта: {form.animation_size ?? 50}%
                <input
                  type="range"
                  min={10}
                  max={100}
                  step={5}
                  value={form.animation_size ?? 50}
                  onChange={(e) => setForm({ ...form, animation_size: Number(e.target.value) })}
                  style={{ width: '100%', padding: 8, background: 'transparent', border: 'none' }}
                />
              </label>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', flex: 1, minWidth: 150 }}>
                Количество: {form.animation_count ?? 14}
                <input
                  type="range"
                  min={1}
                  max={40}
                  step={1}
                  value={form.animation_count ?? 14}
                  onChange={(e) => setForm({ ...form, animation_count: Number(e.target.value) })}
                  style={{ width: '100%', padding: 8, background: 'transparent', border: 'none' }}
                />
              </label>
              <label style={{ fontSize: 14, color: 'var(--text-muted)', flex: 1, minWidth: 150 }}>
                Прозрачность: {form.animation_opacity ?? 100}%
                <input
                  type="range"
                  min={10}
                  max={100}
                  step={5}
                  value={form.animation_opacity ?? 100}
                  onChange={(e) => setForm({ ...form, animation_opacity: Number(e.target.value) })}
                  style={{ width: '100%', padding: 8, background: 'transparent', border: 'none' }}
                />
              </label>
              <label style={{ fontSize: 15, color: 'var(--text-secondary)', display: 'flex', gap: 6, alignItems: 'center', paddingTop: 14 }}>
                <input
                  type="checkbox"
                  checked={form.shop_enabled}
                  onChange={(e) => setForm({ ...form, shop_enabled: e.target.checked })}
                />
                Магазин выкупа
              </label>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="fm-btn" onClick={submit} disabled={busy}>
                {busy ? <span className="fm-spinner" /> : isEdit ? 'Сохранить' : 'Создать праздник'}
              </button>
              <button className="fm-btn fm-btn-outline" onClick={() => navigate('/admin/holidays')}>
                К списку
              </button>
            </div>
          </div>
        )}
      </div>

      {isEdit && detail && (
        <>
          <div className="fm-card" style={{ marginTop: 12 }}>
            <h3>Фон праздника</h3>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
                🖼 Загрузить фон
                <input
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    e.target.value = '';
                    if (f) uploadBg(f);
                  }}
                />
              </label>
              {detail.bg_image_url && (
                <img src={mediaUrl(detail.bg_image_url)} alt="" style={{ height: 40, borderRadius: 6 }} />
              )}
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                Виден игрокам на главной во время праздника (перекрывает общий фон игры)
              </span>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexBasis: '100%' }}>
                <label style={{ fontSize: 14, color: 'var(--text-muted)', display: 'flex', gap: 8, alignItems: 'center' }}>
                  Цвет подложки (без картинки фона)
                  <input
                    type="color"
                    value={form.bg_color || '#1a1030'}
                    onChange={(e) => setForm({ ...form, bg_color: e.target.value })}
                    style={{ width: 44, height: 32, border: 'none', background: 'none', cursor: 'pointer' }}
                  />
                </label>
                {form.bg_color && (
                  <button className="fm-btn fm-btn-xs fm-btn-outline" onClick={() => setForm({ ...form, bg_color: null })}>
                    ✖ По умолчанию
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="fm-card" style={{ marginTop: 12 }}>
            <h3>Анимация и музыка праздника</h3>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
              <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
                🌫 Загрузить силуэт (PNG)
                <input
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    e.target.value = '';
                    if (f) uploadAnimation(f);
                  }}
                />
              </label>
              {detail.animation_url && (
                <>
                  <img src={mediaUrl(detail.animation_url)} alt="" style={{ height: 48, borderRadius: 6 }} />
                  <button className="fm-btn fm-btn-xs fm-btn-danger" onClick={clearAnimation}>✖ Убрать</button>
                </>
              )}
              <span style={{ fontSize: 13, color: 'var(--text-muted)', flexBasis: '100%' }}>
                Свой силуэт летает по всему экрану, как конфетти. Белая подложка убирается автоматически; размер — ползунком в форме выше.
              </span>
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
                🎵 Загрузить музыку
                <input
                  type="file"
                  accept="audio/*"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    e.target.value = '';
                    if (f) uploadAudio(f);
                  }}
                />
              </label>
              {detail.audio_url && (
                <>
                  <span style={{ fontSize: 14, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>🎧 {detail.audio_url.split('/').pop()}</span>
                  <button className="fm-btn fm-btn-xs fm-btn-danger" onClick={clearAudio}>✖ Убрать</button>
                </>
              )}
              <span style={{ fontSize: 13, color: 'var(--text-muted)', flexBasis: '100%' }}>
                Играет по кругу во время праздника; игрок может отключить её в профиле.
              </span>
            </div>
          </div>

          <div className="fm-card" style={{ marginTop: 12 }}>
            <h3>🛒 Карточки магазина (без даты)</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Доступны игрокам только через магазин (после праздника, выкуп 1000 крестиков).
            </p>
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input
                  className="fm-input"
                  style={{ flex: 2, minWidth: 140 }}
                  placeholder="Название карточки"
                  value={extraTitle}
                  onChange={(e) => setExtraTitle(e.target.value)}
                />
                <select
                  className="fm-input"
                  style={{ flex: 1, minWidth: 130 }}
                  value={extraCat ?? detail.categories[0]?.id ?? ''}
                  onChange={(e) => setExtraCat(Number(e.target.value))}
                >
                  {detail.categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.title}</option>
                  ))}
                </select>
              </div>
              <input
                className="fm-input"
                placeholder="Задание (необязательно)"
                value={extraTask}
                onChange={(e) => setExtraTask(e.target.value)}
              />
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                <button className="fm-btn" onClick={addExtraCard} disabled={!extraTitle.trim()}>Добавить карточку</button>
              </div>
            </div>
            <div className="fm-grid" style={{ marginTop: 12 }}>
              {detail.categories.flatMap((c) => c.cards.filter((card) => card.day === null)).map((card) => {
                const draft = draftFor(card);
                const editing = editExtra === card.id;
                return (
                  <div key={card.id} className="fm-card" style={{ textAlign: 'center' }}>
                    {card.image_url ? (
                      <img src={mediaUrl(card.image_url)} alt="" style={{ width: '100%', borderRadius: 8, marginBottom: 6 }} />
                    ) : (
                      <div style={{ fontSize: 30, marginBottom: 6 }}>🎴</div>
                    )}
                    {editing ? (
                      <>
                        <input
                          className="fm-input"
                          placeholder="Название карточки"
                          value={draft.title}
                          onChange={(e) => setDraft(card, { title: e.target.value })}
                          style={{ marginBottom: 6 }}
                        />
                        <input
                          className="fm-input"
                          placeholder="Задание (необязательно)"
                          value={draft.task}
                          onChange={(e) => setDraft(card, { task: e.target.value })}
                          style={{ marginBottom: 8 }}
                        />
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                          <button
                            className="fm-btn fm-btn-xs"
                            disabled={!drafts[card.id]?.title.trim()}
                            onClick={() => saveExtraCard(card.id)}
                          >
                            💾 Сохранить
                          </button>
                          <button
                            className="fm-btn fm-btn-xs fm-btn-outline"
                            onClick={() => {
                              setEditExtra(null);
                              setDrafts((prev) => {
                                const next = { ...prev };
                                delete next[card.id];
                                return next;
                              });
                            }}
                          >
                            ✖ Отмена
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        <div style={{ fontSize: 15 }}>{card.title}</div>
                        {card.task_text && (
                          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>{card.task_text}</div>
                        )}
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginTop: 6, flexWrap: 'wrap' }}>
                          <label className="fm-btn fm-btn-xs" style={{ cursor: 'pointer' }}>
                            🖼
                            <input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadSlotImage(card.id, f); e.target.value = ''; }} />
                          </label>
                          <button
                            className="fm-btn fm-btn-xs fm-btn-outline"
                            onClick={() => {
                              setEditExtra(card.id);
                              setDraft(card, {});
                            }}
                          >
                            ✏️
                          </button>
                          <button className="fm-btn fm-btn-xs fm-btn-danger" onClick={() => setAskRemoveCard({ id: card.id, title: card.title })}>🗑</button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <GridView detail={detail} />

          <div className="fm-card" style={{ marginTop: 12 }}>
            <h3>Категории карточек</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              У каждой категории своя норма. Для каждой категории автоматически создана
              сетка карточек по дням праздника — заполните название, задание и картинку.
            </p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <input
                className="fm-input"
                style={{ flex: 2, minWidth: 160 }}
                placeholder="Название категории (Наряды, Декор, Угощения…)"
                value={newCategoryTitle}
                onChange={(e) => setNewCategoryTitle(e.target.value)}
              />
              <input
                className="fm-input"
                style={{ flex: 1, minWidth: 110 }}
                type="number"
                min={1}
                placeholder="Норма"
                value={newCategoryNorm}
                onChange={(e) => setNewCategoryNorm(e.target.value)}
              />
              <button className="fm-btn" onClick={addCategory} disabled={!newCategoryTitle.trim()}>
                Добавить категорию
              </button>
            </div>
          </div>

          {detail.categories.map((cat) => (
            <div key={cat.id} id={`cat-${cat.id}`} className="fm-card" style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                {categoryHeader(cat)}
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr',
                  gap: 10,
                  marginTop: 12,
                }}
              >
                {cat.cards.filter((card: HolidayCard) => card.day !== null).map((card: HolidayCard) => {
                  const draft = draftFor(card);
                  const isSaved = savedFlash === card.id;
                  return (
                    <div
                      key={card.id}
                      className="fm-card"
                      style={{
                        borderColor: card.title.trim() ? 'var(--border)' : 'rgba(244,213,141,0.12)',
                        opacity: card.title.trim() ? 1 : 0.85,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <strong style={{ fontSize: 15 }}>🗓 {card.day ? dayLabel(card.day) : '—'}</strong>
                        {isSaved && <span style={{ fontSize: 13, color: 'var(--success)' }}>✓ Сохранено</span>}
                      </div>
                      {card.image_url && (
                        <img
                          src={mediaUrl(card.image_url)}
                          alt=""
                          style={{ width: '100%', borderRadius: 8, marginBottom: 8, objectFit: 'cover', maxHeight: 110 }}
                        />
                      )}
                      <input
                        className="fm-input"
                        placeholder="Название карточки"
                        value={draft.title}
                        onChange={(e) => setDraft(card, { title: e.target.value })}
                        style={{ marginBottom: 6 }}
                      />
                      <input
                        className="fm-input"
                        placeholder="Задание (вышейте тыкву 40×40)"
                        value={draft.task}
                        onChange={(e) => setDraft(card, { task: e.target.value })}
                        style={{ marginBottom: 8 }}
                      />
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <label className="fm-btn fm-btn-xs" style={{ cursor: 'pointer' }}>
                          🖼 Картинка
                          <input
                            type="file"
                            accept="image/*"
                            style={{ display: 'none' }}
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              if (f) uploadSlotImage(card.id, f);
                              e.target.value = '';
                            }}
                          />
                        </label>
                        {card.image_url && (
                          <button className="fm-btn fm-btn-xs fm-btn-outline" onClick={() => clearSlotImage(card.id)}>
                            ✖ Картинку
                          </button>
                        )}
                        <button
                          className="fm-btn fm-btn-xs fm-btn-outline"
                          onClick={() => saveSlot(card.id)}
                          disabled={!drafts[card.id]}
                        >
                          💾 Сохранить
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {detail.categories.length === 0 && loaded && (
            <div className="fm-card" style={{ marginTop: 12, textAlign: 'center' }}>
              <p style={{ color: 'var(--text-muted)' }}>
                Создайте хотя бы одну категорию — сетка карточек по дням сгенерируется автоматически.
              </p>
            </div>
          )}
        </>
      )}

      {askRemoveCat && (
        <ConfirmDialog
          title={`Удалить категорию «${askRemoveCat.title}» вместе с её карточками?`}
          confirmLabel="Удалить"
          onConfirm={removeCategory}
          onCancel={() => setAskRemoveCat(null)}
        />
      )}
      {askRemoveCard && (
        <ConfirmDialog
          title={`Удалить карточку «${askRemoveCard.title}»?`}
          confirmLabel="Удалить"
          onConfirm={removeExtraCard}
          onCancel={() => setAskRemoveCard(null)}
        />
      )}
    </>
  );
}
