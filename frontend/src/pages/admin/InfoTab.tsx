import { useEffect, useState } from 'react';
import { api, type InfoBlock } from '../../api/endpoints';

export default function InfoTab() {
  const [blocks, setBlocks] = useState<InfoBlock[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.info()
      .then((d) => setBlocks(d.blocks))
      .catch(() => setError('Не удалось загрузить информацию'));
  }, []);

  if (!blocks) {
    return (
      <div className="fm-card" style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
        <span className="fm-spinner" />
      </div>
    );
  }

  function update(i: number, patch: Partial<InfoBlock>) {
    setBlocks((prev) => (prev ?? []).map((b, idx) => (idx === i ? { ...b, ...patch } : b)));
    setSaved(false);
  }

  function addBlock() {
    setBlocks((prev) => [...(prev ?? []), { title: '', text: '' }]);
    setSaved(false);
  }

  function removeBlock(i: number) {
    setBlocks((prev) => (prev ?? []).filter((_, idx) => idx !== i));
    setSaved(false);
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const d = await api.adminSetInfo(blocks ?? []);
      setBlocks(d.blocks);
      setError(null);
      setSaved(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось сохранить');
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="fm-card">
        <h2>ℹ️ Информация</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Блоки на странице «Информация» для игроков. Переносы строк сохраняются.
        </p>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="fm-btn fm-btn-outline" onClick={addBlock}>+ Добавить блок</button>
          <button className="fm-btn" onClick={save} disabled={saving}>
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
          {saved && <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Сохранено ✓</span>}
        </div>
      </div>

      {blocks.map((b, i) => (
        <div key={i} className="fm-card" style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <span className="fm-chip">{i + 1}</span>
            <button className="fm-btn fm-btn-outline fm-btn-xs" style={{ marginLeft: 'auto' }} onClick={() => removeBlock(i)}>
              Удалить
            </button>
          </div>
          <input
            className="fm-input"
            style={{ width: '100%', marginTop: 8 }}
            placeholder="Заголовок"
            value={b.title}
            onChange={(e) => update(i, { title: e.target.value })}
          />
          <textarea
            className="fm-input"
            style={{ width: '100%', marginTop: 8, minHeight: 100, resize: 'vertical' }}
            placeholder="Текст блока"
            value={b.text}
            onChange={(e) => update(i, { text: e.target.value })}
          />
        </div>
      ))}
    </>
  );
}
