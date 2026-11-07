import { useCallback, useEffect, useState } from 'react';
import { api, type AdminRewardPurchase, type RewardItem } from '../../api/endpoints';
import { errorMessage } from '../../api/errors';
import { mediaUrl } from '../../api/media';
import ConfirmDialog from '../../components/ConfirmDialog';

type Draft = {
  title: string;
  description: string;
  price: string;
  percent: string;
  is_active: boolean;
};

const STATUS_LABELS = {
  available: 'Доступна',
  active: 'Действует',
  used: 'Использована',
  revoked: 'Обнулена',
};

function draftOf(item: RewardItem): Draft {
  return {
    title: item.title,
    description: item.description || '',
    price: String(item.price_crystals),
    percent: String(item.effect_config.percent || 5),
    is_active: item.is_active,
  };
}

export default function RewardsTab() {
  const [items, setItems] = useState<RewardItem[]>([]);
  const [purchases, setPurchases] = useState<AdminRewardPurchase[]>([]);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [askRevoke, setAskRevoke] = useState<AdminRewardPurchase | null>(null);

  const load = useCallback(async () => {
    try {
      const [nextItems, nextPurchases] = await Promise.all([
        api.adminRewardItems(),
        api.adminRewardPurchases(),
      ]);
      setItems(nextItems);
      setPurchases(nextPurchases);
      setDrafts(Object.fromEntries(nextItems.map((item) => [item.id, draftOf(item)])));
      setError(null);
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось загрузить награды'));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function change(itemId: number, patch: Partial<Draft>) {
    setDrafts((current) => ({
      ...current,
      [itemId]: { ...current[itemId], ...patch },
    }));
  }

  async function save(item: RewardItem) {
    const draft = drafts[item.id];
    const price = Number(draft.price);
    const percent = Number(draft.percent);
    if (!draft.title.trim() || !Number.isInteger(price) || price <= 0) {
      setError('Название и положительная цена в кристаллах обязательны');
      return;
    }
    if (item.effect_type === 'external_zakaz_discount' && (!Number.isInteger(percent) || percent < 1 || percent > 99)) {
      setError('Скидка должна быть целым числом от 1 до 99');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.adminUpdateRewardItem(item.id, {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        price_crystals: price,
        is_active: draft.is_active,
        ...(item.effect_type === 'external_zakaz_discount' ? { effect_config: { percent } } : {}),
      });
      await load();
    } catch (e: any) {
      setError(errorMessage(e, 'Не удалось сохранить награду'));
    } finally {
      setBusy(false);
    }
  }

  async function uploadImage(id: number, file: File) {
    await api.adminUploadRewardImage(id, file);
    await load();
  }

  async function revoke() {
    if (!askRevoke) return;
    setBusy(true);
    setError(null);
    try {
      await api.adminRevokeReward(askRevoke.id);
      setAskRevoke(null);
      await load();
    } catch (e: any) {
      setAskRevoke(null);
      setError(errorMessage(e, 'Не удалось обнулить награду'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="fm-card">
        <h2>🏆 Пресеты наград</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Набор наград задаётся в коде. Здесь можно менять название, описание, изображение,
          цену в кристаллах и процент скидки в «Магазине игр».
        </p>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}
      </div>

      {items.map((item) => {
        const draft = drafts[item.id];
        if (!draft) return null;
        return (
          <div key={item.id} className="fm-card" style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              {item.image_url && <img src={mediaUrl(item.image_url)} alt="" style={{ height: 54, borderRadius: 6 }} />}
              <strong>{item.preset_key}</strong>
              <label className="fm-btn fm-btn-xs" style={{ cursor: 'pointer' }}>
                Изображение
                <input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadImage(item.id, f); e.target.value = ''; }} />
              </label>
            </div>
            <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
              <input className="fm-input" value={draft.title} onChange={(e) => change(item.id, { title: e.target.value })} />
              <textarea className="fm-input" style={{ minHeight: 70 }} value={draft.description} onChange={(e) => change(item.id, { description: e.target.value })} />
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <label>Цена, кристаллов <input className="fm-input" style={{ maxWidth: 110 }} type="number" min={1} value={draft.price} onChange={(e) => change(item.id, { price: e.target.value })} /></label>
                {item.effect_type === 'external_zakaz_discount' && (
                  <label>Скидка, % <input className="fm-input" style={{ maxWidth: 110 }} type="number" min={1} max={99} value={draft.percent} onChange={(e) => change(item.id, { percent: e.target.value })} /></label>
                )}
                <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input type="checkbox" checked={draft.is_active} onChange={(e) => change(item.id, { is_active: e.target.checked })} />
                  Показывать в лавке
                </label>
                <button className="fm-btn fm-btn-sm" disabled={busy} onClick={() => save(item)}>Сохранить</button>
              </div>
            </div>
          </div>
        );
      })}

      <div className="fm-card" style={{ marginTop: 16 }}>
        <h2>Награды игроков</h2>
        {purchases.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Покупок пока нет.</p>}
        {purchases.map((purchase) => (
          <div key={purchase.id} className="fm-card" style={{ marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <strong style={{ flex: 1, minWidth: 180 }}>{purchase.item_title}</strong>
              <span className="fm-chip">{STATUS_LABELS[purchase.status]}</span>
              {(purchase.status === 'available' || purchase.status === 'active' || (purchase.status === 'used' && purchase.effect_type.startsWith('external_'))) && (
                <button className="fm-btn fm-btn-xs fm-btn-danger" disabled={busy} onClick={() => setAskRevoke(purchase)}>Обнулить</button>
              )}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
              {purchase.display_name || `Игрок ${purchase.user_id}`} · VK ID {purchase.user_id} · покупка №{purchase.id}
            </div>
            {purchase.last_error && <div style={{ fontSize: 13, color: 'var(--danger)', marginTop: 4 }}>{purchase.last_error}</div>}
          </div>
        ))}
      </div>

      {askRevoke && (
        <ConfirmDialog
          title={`Обнулить награду «${askRevoke.item_title}»?`}
          text="Доступная или действующая награда перестанет работать. Для внешней награды будет отправлен отзыв в другое приложение."
          confirmLabel="Обнулить"
          busy={busy}
          onConfirm={revoke}
          onCancel={() => setAskRevoke(null)}
        />
      )}
    </>
  );
}
