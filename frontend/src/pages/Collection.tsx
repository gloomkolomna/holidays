import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { api, type Appearance, type Collection, type CollectionEntry, type Holiday } from '../api/endpoints';
import { mediaUrl } from '../api/media';
import MusicPlayer from '../components/MusicPlayer';
import ParticlesBackground from '../components/ParticlesBackground';
import { useSession } from '../context/SessionContext';
import { applySurfaceColor } from '../theme';

function dayLabel(day: string): string {
  return day.split('-').reverse().join('.');
}

function CollectionCell({ entry, onZoom }: { entry: CollectionEntry; onZoom: (url: string) => void }) {
  const { card, collected } = entry;
  return (
    <div className="fm-card" style={{ textAlign: 'center', opacity: collected ? 1 : 0.8 }}>
      {collected && card.image_url ? (
        <img
          src={mediaUrl(card.image_url)}
          alt={card.title}
          style={{ width: '100%', borderRadius: 8, cursor: 'zoom-in' }}
          onClick={() => onZoom(card.image_url!)}
        />
      ) : (
        <div
          style={{
            width: '100%',
            aspectRatio: '1',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--surface-strong)',
            fontSize: 28,
            border: '1px dashed var(--border)',
          }}
        >
          ❔
        </div>
      )}
      {collected && (
        <>
          <div style={{ fontSize: 14, marginTop: 6 }}>{card.title}</div>
          {card.day && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>🗓 {dayLabel(card.day)}</div>
          )}
        </>
      )}
    </div>
  );
}

export default function CollectionPage() {
  const { user } = useSession();
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [collection, setCollection] = useState<Collection | null>(null);
  const [selectedCat, setSelectedCat] = useState<number | null>(null);
  const [appearance, setAppearance] = useState<Appearance | null>(null);
  const [zoomImg, setZoomImg] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.holidaysList()
      .then((list) => {
        setHolidays(list);
        const active = list.find((h) => h.status === 'active') || list[0];
        if (active) setSelectedId(active.id);
      })
      .finally(() => setLoaded(true));
    api.appearance().then(setAppearance).catch(() => setAppearance(null));
  }, []);

  const loadCollection = useCallback(async (holidayId: number) => {
    try {
      const data = await api.collection(holidayId);
      setCollection(data);
      setSelectedCat(data.categories[0]?.id ?? null);
    } catch {
      setCollection(null);
      setSelectedCat(null);
    }
  }, []);

  useEffect(() => {
    if (selectedId != null) loadCollection(selectedId);
  }, [selectedId, loadCollection]);

  const surfaceHoliday = holidays.find((h) => h.id === selectedId);
  useEffect(() => {
    applySurfaceColor(surfaceHoliday?.bg_color);
    return () => applySurfaceColor(null);
  }, [surfaceHoliday?.bg_color]);

  if (!loaded) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
        <span className="fm-spinner" />
      </div>
    );
  }

  const selectedHoliday = holidays.find((h) => h.id === selectedId) || null;

  return (
    <div className="fm-rise">
      {(selectedHoliday?.animation_url || selectedHoliday?.animation_preset) && (
        <ParticlesBackground
          preset={selectedHoliday?.animation_url ? undefined : selectedHoliday?.animation_preset ?? undefined}
          imageUrl={selectedHoliday?.animation_url ? mediaUrl(selectedHoliday.animation_url) : null}
          size={selectedHoliday?.animation_size ?? 50}
          count={selectedHoliday?.animation_count}
          opacity={selectedHoliday?.animation_opacity}
        />
      )}
      {selectedHoliday?.audio_url && user?.music_enabled !== false && (
        <MusicPlayer src={mediaUrl(selectedHoliday.audio_url)} />
      )}

      {zoomImg && createPortal(
        <div
          onClick={() => setZoomImg(null)}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            background: 'rgba(0,0,0,0.88)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'zoom-out',
          }}
        >
          <img src={mediaUrl(zoomImg)} alt="" style={{ maxWidth: '90vw', maxHeight: '85vh', borderRadius: 10 }} />
        </div>,
        document.body,
      )}

      {holidays.length === 0 ? (
        <div className="fm-card">Праздников пока не было.</div>
      ) : (
        <>
          {appearance?.collection_bg_url && (
            <img
              src={mediaUrl(appearance.collection_bg_url)}
              alt=""
              style={{ width: '100%', borderRadius: 'var(--radius-lg)', marginBottom: 12, display: 'block' }}
            />
          )}

          <div className="fm-menu-tabs">
            {holidays.map((h) => (
              <button
                key={h.id}
                className={`fm-menu-tab${h.id === selectedId ? ' active' : ''}`}
                onClick={() => setSelectedId(h.id)}
              >
                {h.title}
              </button>
            ))}
          </div>

          {collection && (
            <>
              <div className="fm-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                  <h3 style={{ margin: 0 }}>{collection.title}</h3>
                  <span className="fm-chip">
                    {collection.collected === collection.total ? '🏆' : '🃏'}{' '}
                    {collection.collected}/{collection.total}
                  </span>
                </div>
                <div className="fm-progress" style={{ marginTop: 10 }}>
                  <div
                    className="fm-progress-fill"
                    style={{ width: `${collection.total ? (collection.collected / collection.total) * 100 : 0}%` }}
                  />
                </div>
              </div>

              <div className="fm-menu-tabs" style={{ justifyContent: 'center' }}>
                {collection.categories.map((cat) => (
                  <button
                    key={cat.id}
                    className={`fm-menu-tab${cat.id === selectedCat ? ' active' : ''}`}
                    onClick={() => setSelectedCat(cat.id)}
                  >
                    {cat.complete ? '🏆 ' : ''}{cat.title}
                  </button>
                ))}
              </div>

              {collection.categories
                .filter((cat) => cat.id === selectedCat)
                .map((cat) => {
                  const done = cat.cards.filter((c) => c.collected).length;
                  return (
                    <div key={cat.id} className="fm-card" style={{ marginTop: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                        <h3 style={{ margin: 0 }}>{cat.title}</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          {cat.complete && cat.trophy_image_url && (
                            <img src={mediaUrl(cat.trophy_image_url)} alt="Кубок" style={{ height: 44, borderRadius: 6 }} />
                          )}
                          <span className="fm-chip">
                            {cat.complete ? '🏆' : '🃏'} {done}/{cat.cards.length}
                          </span>
                        </div>
                      </div>
                      <div className="fm-grid" style={{ marginTop: 12 }}>
                        {cat.cards.map((entry) => (
                          <CollectionCell key={entry.card.id} entry={entry} onZoom={setZoomImg} />
                        ))}
                      </div>
                    </div>
                  );
                })}
            </>
          )}
        </>
      )}
    </div>
  );
}
