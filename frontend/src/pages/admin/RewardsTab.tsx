import { useCallback, useEffect, useState } from 'react';
import { api, type RewardCodeEntry, type RewardItem } from '../../api/endpoints';
import { mediaUrl } from '../../api/media';
import ConfirmDialog from '../../components/ConfirmDialog';

export default function RewardsTab() {
  const [items, setItems] = useState<RewardItem[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('1');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [codesDraft, setCodesDraft] = useState<Record<number, string>>({});
  const [codesList, setCodesList] = useState<Record<number, RewardCodeEntry[]>>({});
  const [askRemove, setAskRemove] = useState<RewardItem | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.adminRewardItems());
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось загрузить товары');
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function createItem() {
    const p = Number(price);
    if (!title.trim() || !p || p <= 0) {
      setError('Название и положительная цена обязательны');
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await api.adminCreateRewardItem({ title: title.trim(), description: description.trim() || null, price_crystals: p, is_active: true });
      setTitle('');
      setDescription('');
      setPrice('1');
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function removeItem() {
    if (!askRemove) return;
    const { id } = askRemove;
    setAskRemove(null);
    await api.adminDeleteRewardItem(id);
    await load();
  }

  async function uploadImage(id: number, file: File) {
    await api.adminUploadRewardImage(id, file);
    await load();
  }

  async function addCodes(id: number) {
    const raw = codesDraft[id] || '';
    const codes = raw.split('\n').map((s) => s.trim()).filter(Boolean);
    if (!codes.length) return;
    await api.adminAddCodes(id, codes);
    setCodesDraft((prev) => ({ ...prev, [id]: '' }));
    await load();
    await openCodes(id);
  }

  async function openCodes(id: number) {
    setCodesList((prev) => ({ ...prev, [id]: [] }));
    const codes = await api.adminListCodes(id);
    setCodesList((prev) => ({ ...prev, [id]: codes }));
  }

  async function removeCode(codeId: number, itemId: number) {
    await api.adminDeleteCode(codeId);
    await load();
    await openCodes(itemId);
  }

  return (
    <>
      <div className="fm-card">
        <h2>🏆 Лавка наград</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Товары за кристаллы (промокоды для «Фермы», «Драконов» и других приложений).
        </p>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
        <div style={{ display: 'grid', gap: 8 }}>
          <input className="fm-input" placeholder="Название товара" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="fm-input" placeholder="Описание (что даёт промокод)" value={description} onChange={(e) => setDescription(e.target.value)} />
          <div style={{ display: 'flex', gap: 8 }}>
            <input className="fm-input" style={{ maxWidth: 140 }} type="number" min={1} placeholder="Цена 💎" value={price} onChange={(e) => setPrice(e.target.value)} />
            <button className="fm-btn" onClick={createItem} disabled={busy}>Добавить товар</button>
          </div>
        </div>
      </div>

      {items.map((item) => (
        <div key={item.id} className="fm-card" style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {item.image_url && <img src={mediaUrl(item.image_url)} alt="" style={{ height: 44, borderRadius: 6 }} />}
            <strong style={{ fontSize: 16 }}>{item.title}</strong>
            <span className="fm-chip">💎 {item.price_crystals}</span>
            <span className="fm-chip">кодов: {item.codes_available}</span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <label className="fm-btn fm-btn-xs" style={{ cursor: 'pointer' }}>
                🖼
                <input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadImage(item.id, f); e.target.value = ''; }} />
              </label>
              <button className="fm-btn fm-btn-xs fm-btn-outline" onClick={() => openCodes(item.id)}>📜 Коды</button>
              <button className="fm-btn fm-btn-xs fm-btn-danger" onClick={() => setAskRemove(item)}>🗑</button>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            <textarea
              className="fm-input"
              style={{ flex: 1, minWidth: 200, minHeight: 64 }}
              placeholder="Промокоды — по одному в строке"
              value={codesDraft[item.id] || ''}
              onChange={(e) => setCodesDraft((prev) => ({ ...prev, [item.id]: e.target.value }))}
            />
            <button className="fm-btn fm-btn-sm" onClick={() => addCodes(item.id)}>Добавить коды</button>
          </div>
          {(codesList[item.id] || []).length > 0 && (
            <div style={{ marginTop: 10, maxHeight: 220, overflowY: 'auto' }}>
              {codesList[item.id].map((c) => (
                <div key={c.id} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '4px 0', fontSize: 14 }}>
                  <code style={{ background: 'var(--surface-strong)', padding: '2px 8px', borderRadius: 6 }}>{c.code}</code>
                  <span style={{ color: c.taken_by ? 'var(--success)' : 'var(--text-muted)', fontSize: 13 }}>
                    {c.taken_by ? `выдан ${c.taken_by}` : 'свободен'}
                  </span>
                  {!c.taken_by && (
                    <button className="fm-btn fm-btn-xs fm-btn-danger" style={{ marginLeft: 'auto' }} onClick={() => removeCode(c.id, item.id)}>✖</button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {askRemove && (
        <ConfirmDialog
          title={`Удалить товар «${askRemove.title}» вместе с кодами?`}
          confirmLabel="Удалить"
          onConfirm={removeItem}
          onCancel={() => setAskRemove(null)}
        />
      )}
    </>
  );
}
