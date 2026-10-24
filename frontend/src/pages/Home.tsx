import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { Swiper, SwiperSlide } from 'swiper/react';
import type { Swiper as SwiperClass } from 'swiper';
import 'swiper/css';
import { api, type GameState, type HolidayCard, type HolidayDetail } from '../api/endpoints';
import { errorMessage } from '../api/errors';
import { mediaUrl } from '../api/media';
import ConfirmDialog from '../components/ConfirmDialog';
import MusicPlayer from '../components/MusicPlayer';
import ParticlesBackground from '../components/ParticlesBackground';
import { useSession } from '../context/SessionContext';
import { msUntilNextMskMidnight } from '../utils/mskTime';
import type { UploadFailMeta } from '../utils/upload';
import { applySurfaceColor } from '../theme';

function dayLabel(day: string): string {
  return day.split('-').reverse().join('.');
}

export default function Home() {
  const { user } = useSession();
  const [state, setState] = useState<GameState | null>(null);
  const [holiday, setHoliday] = useState<HolidayDetail | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justCollected, setJustCollected] = useState<string | null>(null);
  const [newDayNotice, setNewDayNotice] = useState(false);
  const [zoomImg, setZoomImg] = useState<string | null>(null);
  const [askAbandon, setAskAbandon] = useState(false);
  const swiperRef = useRef<SwiperClass | null>(null);
  const [nav, setNav] = useState({ idx: 0, beg: true, end: false });

  const [amount, setAmount] = useState('');
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [sagaFile, setSagaFile] = useState<File | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await api.gameState();
      setState(s);
      if (s.holiday_id != null) {
        api.holidayDetail(s.holiday_id).then(setHoliday).catch(() => setHoliday(null));
      } else {
        setHoliday(null);
      }
    } catch {
      setState(null);
      setHoliday(null);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const schedule = () => {
      timer = setTimeout(() => {
        setNewDayNotice(true);
        load();
        schedule();
      }, msUntilNextMskMidnight());
    };
    schedule();
    return () => clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!newDayNotice) return;
    const t = setTimeout(() => setNewDayNotice(false), 6000);
    return () => clearTimeout(t);
  }, [newDayNotice]);

  useEffect(() => {
    applySurfaceColor(holiday?.bg_color);
    return () => applySurfaceColor(null);
  }, [holiday?.bg_color]);

  async function take(cardId: number) {
    setBusy(true);
    setError(null);
    try {
      await api.takeCard(cardId);
      await load();
    } catch (e: any) {
      if (errorMessage(e, '') === 'Эта карточка показывается в другой день') {
        setNewDayNotice(true);
        await load();
      } else {
        setError(errorMessage(e, 'Не удалось принять карточку'));
      }
    } finally {
      setBusy(false);
    }
  }

  async function submitReport(mode: 'norm' | 'penalty') {
    if (!state?.active_task || !beforeFile || !afterFile) return;
    setBusy(true);
    setError(null);
    const startedAt = Date.now();
    try {
      await api.me().catch(() => {});
      const res = await api.reportTask(
        state.active_task.id,
        Number(amount),
        beforeFile,
        afterFile,
        mode,
        previewFile,
        sagaFile,
      );
      if (res.collected) setJustCollected(state.active_task.card.title);
      setAmount('');
      setBeforeFile(null);
      setAfterFile(null);
      setPreviewFile(null);
      setSagaFile(null);
      await load();
    } catch (e: any) {
      if (e?.response) setError(errorMessage(e, 'Не удалось отправить отчёт — попробуйте ещё раз'));
      else {
        setError('Нет связи с сервером — проверьте интернет и попробуйте ещё раз');
        const meta = e?.uploadMeta as UploadFailMeta | undefined;
        api.clientLog({
          event: 'report_upload_failed',
          elapsed_ms: Date.now() - startedAt,
          code: String(e?.code ?? ''),
          task_id: state.active_task.id,
          files: [beforeFile, afterFile, previewFile, sagaFile]
            .filter((f): f is File => !!f)
            .map((f) => ({ name: f.name, size: f.size, type: f.type })),
          sent: meta?.sent ?? [],
          uploaded_bytes: meta?.uploadedBytes ?? 0,
          attempts: meta?.attempts ?? 1,
        }).catch(() => {});
      }
    } finally {
      setBusy(false);
    }
  }

  const task = state?.active_task ?? null;
  const isPenaltyTask = task?.kind === 'penalty';
  const holidayActive = state?.holiday_id != null;
  const abandonText = holidayActive
    ? 'Карточка не попадёт в коллекцию, но её можно будет принять снова.'
    : 'Карточка не попадёт в коллекцию — добрать её можно будет в Магазине по выходным.';

  async function abandon() {
    if (!task) return;
    setBusy(true);
    setError(null);
    try {
      await api.abandonTask(task.id);
      setAskAbandon(false);
      setAmount('');
      setBeforeFile(null);
      setAfterFile(null);
      setPreviewFile(null);
      setSagaFile(null);
      await load();
    } catch (e: any) {
      setAskAbandon(false);
      setError(errorMessage(e, 'Не удалось отказаться от задания'));
    } finally {
      setBusy(false);
    }
  }

  const zoomPortal = zoomImg && createPortal(
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
  );

  const abandonPortal = askAbandon && task && (
    <ConfirmDialog
      title="Отказаться от задания?"
      text={abandonText}
      confirmLabel="Отказаться"
      busy={busy}
      onConfirm={abandon}
      onCancel={() => setAskAbandon(false)}
    />
  );

  const taskBlock = task ? (
    <div className="fm-card" style={{ marginTop: 12 }}>
      <h3>Активное задание</h3>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        {task.card.image_url ? (
          <img
            src={mediaUrl(task.card.image_url)}
            alt=""
            style={{ width: 72, height: 72, borderRadius: 10, objectFit: 'cover', cursor: 'zoom-in' }}
            onClick={() => setZoomImg(task.card.image_url)}
          />
        ) : (
          <div style={{ width: 72, height: 72, borderRadius: 10, background: 'var(--surface-strong)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30 }}>🎴</div>
        )}
        <div>
          <div style={{ fontSize: 18 }}>{task.card.title}</div>
          {task.card.task_text && (
            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 2 }}>
              {task.card.task_text}
            </div>
          )}
          <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 4 }}>
            Вышейте {task.required_crosses} крестиков и приложите фото
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
        <input
          className="fm-input"
          type="number"
          min={1}
          placeholder={`Крестиков (норма ${task.required_crosses})`}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
            📷 Фото «до»{beforeFile ? ' ✓' : ''}
            <input
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => { setBeforeFile(e.target.files?.[0] || null); e.target.value = ''; }}
            />
          </label>
          <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
            📷 Фото «после»{afterFile ? ' ✓' : ''}
            <input
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => { setAfterFile(e.target.files?.[0] || null); e.target.value = ''; }}
            />
          </label>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
            🖼 Превью{previewFile ? ' ✓' : ''}
            <input
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => { setPreviewFile(e.target.files?.[0] || null); e.target.value = ''; }}
            />
          </label>
          <label className="fm-btn fm-btn-outline" style={{ cursor: 'pointer' }}>
            📖 Сага{sagaFile ? ' ✓' : ''}
            <input
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => { setSagaFile(e.target.files?.[0] || null); e.target.value = ''; }}
            />
          </label>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: isPenaltyTask ? '1fr' : '1fr 1fr', gap: 10 }}>
          <button
            className="fm-btn"
            disabled={busy || !beforeFile || !afterFile || !amount}
            onClick={() => submitReport('norm')}
          >
            {busy ? <span className="fm-spinner" /> : `✅ ${isPenaltyTask ? 'Сдать · ' : 'Норма · '}${task.required_crosses}`}
          </button>
          {!isPenaltyTask && (
            <button
              className="fm-btn fm-btn-outline"
              disabled={busy || !beforeFile || !afterFile || !amount}
              onClick={() => submitReport('penalty')}
            >
              ⚠️ Штраф · {task.required_crosses * 2}
            </button>
          )}
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
          {isPenaltyTask
            ? 'Выкупленное задание сдаётся по норме 1000 крестиков — отказаться от него нельзя.'
            : 'Фото «до» и «после» обязательны, «превью» и «сага» — по желанию. «Штраф» закрывает задание двойной нормой.'}
        </p>
        {!isPenaltyTask && (
          <button
            className="fm-btn fm-btn-outline"
            disabled={busy}
            onClick={() => setAskAbandon(true)}
          >
            Отказаться от задания
          </button>
        )}
        {holidayActive && !isPenaltyTask && (
          <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
            Пока задание не сдано, другую карточку принять нельзя — или откажитесь от него.
          </p>
        )}
      </div>
    </div>
  ) : null;

  if (!loaded) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
        <span className="fm-spinner" />
      </div>
    );
  }

  if (!state || !holidayActive) {
    return (
      <div className="fm-rise">
        {zoomPortal}
        {abandonPortal}
        {justCollected && (
          <div className="fm-card fm-pop" style={{ marginBottom: 12, textAlign: 'center', borderColor: 'var(--success)' }}>
            <div style={{ fontSize: 30 }}>🃏✨</div>
            Карточка «{justCollected}» в коллекции!
          </div>
        )}
        {error && (
          <div className="fm-card" style={{ marginBottom: 12, color: 'var(--danger)' }}>{error}</div>
        )}
        {taskBlock}
        <div className="fm-card" style={task ? { marginTop: 12 } : undefined}>
          {task ? (
            <>
              <h2>🎉 Праздник завершён</h2>
              <p style={{ color: 'var(--text-secondary)' }}>
                Праздник закончился, но взятое задание ещё действует —{' '}
                {isPenaltyTask ? 'сдайте его выше.' : 'сдайте его или откажитесь от него выше.'}
              </p>
            </>
          ) : (
            <>
              <h2>🎉 Скоро праздник!</h2>
              <p style={{ color: 'var(--text-secondary)' }}>
                Активного праздника сейчас нет. Когда он начнётся, здесь появятся
                карточки заданий на каждый день.
              </p>
            </>
          )}
        </div>
        <div className="fm-card" style={{ marginTop: 12 }}>
          <h3>Как это работает</h3>
          <ul style={{ color: 'var(--text-secondary)', lineHeight: 1.6, paddingLeft: 20 }}>
            <li>Каждый день праздника — новые карточки по одной из каждой категории</li>
            <li>Отчитывайтесь фото «до/после» и числом крестиков</li>
            <li>Собранные карточки пополняют коллекцию тематики</li>
            <li>Полная коллекция — кристалл и кубок</li>
          </ul>
        </div>
      </div>
    );
  }

  const openCards = state.today_cards;

  return (
    <div className="fm-rise">
      {(holiday?.animation_url || holiday?.animation_preset) && (
        <ParticlesBackground
          preset={holiday?.animation_url ? undefined : holiday?.animation_preset ?? undefined}
          imageUrl={holiday?.animation_url ? mediaUrl(holiday.animation_url) : null}
          size={holiday?.animation_size ?? 50}
          count={holiday?.animation_count}
          opacity={holiday?.animation_opacity}
        />
      )}
      {holiday?.audio_url && user?.music_enabled !== false && (
        <MusicPlayer src={mediaUrl(holiday.audio_url)} />
      )}

      {zoomPortal}
      {abandonPortal}

      {justCollected && (
        <div className="fm-card fm-pop" style={{ marginBottom: 12, textAlign: 'center', borderColor: 'var(--success)' }}>
          <div style={{ fontSize: 30 }}>🃏✨</div>
          Карточка «{justCollected}» в коллекции!
        </div>
      )}

      {newDayNotice && (
        <div className="fm-card fm-pop" style={{ marginBottom: 12, textAlign: 'center' }}>
          <div style={{ fontSize: 30 }}>🗓✨</div>
          Начался новый день — карточки обновились
        </div>
      )}

      <div className="fm-card">
        <h2>{state.holiday_title}</h2>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <span className="fm-chip">🗓 День: {dayLabel(state.day)}</span>
          <Link className="fm-btn fm-btn-sm fm-btn-outline" to="/collection">
            🃏 Коллекция {state.collected_count}/{state.cards_total}
          </Link>
        </div>
        <div className="fm-progress" style={{ marginTop: 10 }}>
          <div
            className="fm-progress-fill"
            style={{ width: `${state.cards_total ? (state.collected_count / state.cards_total) * 100 : 0}%` }}
          />
        </div>
      </div>

      {error && (
        <div className="fm-card" style={{ marginTop: 12, color: 'var(--danger)' }}>{error}</div>
      )}

      {taskBlock}

      {openCards.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <Swiper
            spaceBetween={12}
            slidesPerView={1.15}
            centeredSlides={openCards.length > 1}
            onSwiper={(s: SwiperClass) => {
              swiperRef.current = s;
              if (openCards.length === 1) s.allowSlidePrev = false;
              setNav({ idx: s.activeIndex, beg: s.isBeginning, end: s.isEnd });
            }}
            onSlideChange={(s: SwiperClass) => setNav({ idx: s.activeIndex, beg: s.isBeginning, end: s.isEnd })}
          >
            {openCards.map(({ card, collected, is_current }: { card: HolidayCard; collected: boolean; is_current: boolean }) => (
              <SwiperSlide key={card.id}>
                <div className="fm-card" style={{ textAlign: 'center', height: '100%' }}>
                  {card.image_url ? (
                    <img
                      src={mediaUrl(card.image_url)}
                      alt={card.title}
                      style={{
                        width: '100%',
                        maxHeight: 240,
                        objectFit: 'contain',
                        borderRadius: 10,
                        cursor: 'zoom-in',
                        background: 'var(--surface-strong)',
                      }}
                      onClick={() => setZoomImg(card.image_url)}
                    />
                  ) : (
                    <div
                      style={{
                        width: '100%',
                        height: 180,
                        borderRadius: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'var(--surface-strong)',
                        fontSize: 44,
                      }}
                    >
                      🎴
                    </div>
                  )}
                  <h3 style={{ marginTop: 10, marginBottom: 4 }}>{card.title}</h3>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span className="fm-chip">норма: {card.norm_crosses} крестиков</span>
                  </div>
                  {card.task_text && (
                    <p style={{ color: 'var(--text-secondary)', fontSize: 15, marginTop: 8, marginBottom: 0 }}>
                      {card.task_text}
                    </p>
                  )}
                  <div style={{ marginTop: 12 }}>
                    {collected ? (
                      <span className="fm-chip">✓ Уже в коллекции</span>
                    ) : is_current ? (
                      <span className="fm-chip">⏳ Ваше активное задание</span>
                    ) : (
                      <button
                        className="fm-btn"
                        disabled={busy || !!task}
                        onClick={() => take(card.id)}
                      >
                        Принять
                      </button>
                    )}
                  </div>
                </div>
              </SwiperSlide>
            ))}
          </Swiper>
          {openCards.length > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 8 }}>
              <button
                className="fm-btn fm-btn-sm fm-btn-outline"
                disabled={nav.beg}
                onClick={() => swiperRef.current?.slidePrev()}
              >
                ←
              </button>
              <span style={{ fontSize: 14, color: 'var(--text-muted)', minWidth: 40, textAlign: 'center' }}>
                {nav.idx + 1} / {openCards.length}
              </span>
              <button
                className="fm-btn fm-btn-sm fm-btn-outline"
                disabled={nav.end}
                onClick={() => swiperRef.current?.slideNext()}
              >
                →
              </button>
            </div>
          )}
          {task && (
            <p style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', marginTop: 6 }}>
              Остальные карточки дня доступны после сдачи текущего задания.
            </p>
          )}
        </div>
      )}

      {openCards.length === 0 && !task && (
        <div className="fm-card" style={{ marginTop: 12, textAlign: 'center' }}>
          <div style={{ fontSize: 30 }}>🌙</div>
          {state.cards_total > 0 && state.collected_count >= state.cards_total ? (
            <>Все карточки собраны — коллекция полная!</>
          ) : (
            <>На сегодня карточек нет — загляните завтра. Хороших стежков!</>
          )}
        </div>
      )}
    </div>
  );
}
