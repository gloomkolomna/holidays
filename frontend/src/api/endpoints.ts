import client from './client';
import { compressImageSafe } from './media';

export interface MeUser {
  vk_id: number;
  role: string;
  status: string;
  display_name: string | null;
  crystals: number;
  music_enabled: boolean;
  is_member: boolean | null;
  created_at: string | null;
}

export interface HolidayCard {
  id: number;
  category_id: number;
  day: string | null;
  title: string;
  task_text: string | null;
  image_url: string | null;
  norm_crosses: number;
}

export interface HolidayCategory {
  id: number;
  title: string;
  norm_crosses: number;
  trophy_image_url: string | null;
  cards_count: number;
}

export interface HolidayCategoryDetail extends HolidayCategory {
  cards: HolidayCard[];
}

export interface Holiday {
  id: number;
  title: string;
  starts_at: string;
  ends_at: string;
  bg_image_url: string | null;
  bg_color: string | null;
  palette: string | null;
  animation_preset: string | null;
  animation_url: string | null;
  animation_size: number;
  animation_count: number;
  animation_opacity: number;
  audio_url: string | null;
  shop_enabled: boolean;
  status: 'upcoming' | 'active' | 'finished';
  days: string[];
  categories_count: number;
  cards_count: number;
}

export interface HolidayDetail extends Holiday {
  categories: HolidayCategoryDetail[];
}

export interface HolidayInput {
  title: string;
  starts_at: string;
  ends_at: string;
  bg_image_url?: string | null;
  bg_color?: string | null;
  palette?: string | null;
  animation_preset?: string | null;
  animation_size?: number;
  animation_count?: number;
  animation_opacity?: number;
  shop_enabled: boolean;
}

export interface GameState {
  holiday_id: number | null;
  holiday_title: string | null;
  day: string;
  today_cards: { card: HolidayCard; collected: boolean; is_current: boolean }[];
  active_task: {
    id: number;
    kind: string;
    required_crosses: number;
    card: HolidayCard;
  } | null;
  collected_count: number;
  cards_total: number;
}

export interface CollectionEntry {
  card: HolidayCard;
  collected: boolean;
  source: string | null;
  earned_at: string | null;
}

export interface CollectionCategory {
  id: number;
  title: string;
  norm_crosses: number;
  trophy_image_url: string | null;
  complete: boolean;
  cards: CollectionEntry[];
}

export interface Collection {
  holiday_id: number;
  title: string;
  collected: number;
  total: number;
  categories: CollectionCategory[];
}

export interface Appearance {
  game_bg_url: string | null;
  collection_bg_url: string | null;
}

export interface LogEntry {
  id: number;
  source: string;
  level: string;
  event: string | null;
  method: string | null;
  path: string | null;
  status_code: number | null;
  message: string | null;
  details: Record<string, unknown> | null;
  user_id: number | null;
  created_at: string;
}

export interface ShopCard {
  id: number;
  title: string;
  task_text: string | null;
  image_url: string | null;
  day: string | null;
  norm_crosses: number;
  penalty_crosses: number;
}

export interface ShopHoliday {
  holiday_id: number;
  title: string;
  cards: ShopCard[];
}

export interface Shop {
  open: boolean;
  reason: 'open' | 'weekday' | 'holiday_active';
  active_holiday_title: string | null;
  active_holiday_ends_at: string | null;
  holidays: ShopHoliday[];
  has_active_task: boolean;
  penalty_crosses: number;
}

export interface Trophy {
  holiday_id: number;
  title: string;
  category_id: number;
  category_title: string;
  crystals: number;
  trophy_image_url: string | null;
  awarded_at: string;
}

export interface RewardItem {
  id: number;
  title: string;
  description: string | null;
  image_url: string | null;
  price_crystals: number;
  codes_available: number;
}

export interface Purchase {
  id: number;
  item_title: string;
  code: string;
  created_at: string;
}

export interface Rewards {
  crystals: number;
  trophies: Trophy[];
  items: RewardItem[];
  purchases: Purchase[];
}

export interface DailyStatRow {
  card_id: number;
  title: string;
  holiday_id: number;
  holiday_title: string;
  count: number;
}

export interface PlayerCollectionEntry {
  holiday_id: number;
  title: string;
  collected: number;
  total: number;
  full: boolean;
}

export interface PlayerEntry {
  vk_id: number;
  display_name: string;
  role: string;
  crystals: number;
  cards_total: number;
  collections: PlayerCollectionEntry[];
}

export interface PlayerTaskEntry {
  id: number;
  kind: string;
  required_crosses: number;
  taken_at: string | null;
  holiday_title: string;
  card_title: string;
  card_task_text: string | null;
  card_image_url: string | null;
  card_day: string | null;
}

export interface PlayerCardEntry {
  card_id: number;
  title: string;
  image_url: string | null;
  day: string | null;
  category_title: string;
  holiday_id: number;
  holiday_title: string;
  source: string;
  earned_at: string | null;
}

export interface PlayerReportEntry {
  id: number;
  amount: number;
  photo_before: string | null;
  photo_after: string | null;
  photo_preview: string | null;
  photo_saga: string | null;
  created_at: string | null;
  card_title: string;
  holiday_title: string;
}

export interface InfoBlock {
  title: string;
  text: string;
}

export interface PlayerDetail {
  player: PlayerEntry;
  active_task: PlayerTaskEntry | null;
  cards: PlayerCardEntry[];
  reports: PlayerReportEntry[];
}

export interface DailyStats {
  day: string;
  total_cards: number;
  total_players: number;
  rows: DailyStatRow[];
}

export interface RewardCodeEntry {
  id: number;
  code: string;
  taken_by: number | null;
  taken_at: string | null;
}

export const api = {
  me(): Promise<MeUser> {
    return client.get('/me').then((r) => r.data);
  },

  holidaysList(): Promise<Holiday[]> {
    return client.get('/holidays').then((r) => r.data);
  },

  activeHoliday(): Promise<HolidayDetail> {
    return client.get('/holidays/active').then((r) => r.data);
  },

  holidayDetail(id: number): Promise<HolidayDetail> {
    return client.get(`/holidays/${id}`).then((r) => r.data);
  },

  adminHolidays(status?: string): Promise<Holiday[]> {
    return client.get('/admin/holidays', { params: status ? { status } : {} }).then((r) => r.data);
  },

  adminHolidayDetail(id: number): Promise<HolidayDetail> {
    return client.get(`/admin/holidays/${id}`).then((r) => r.data);
  },

  adminCreateHoliday(data: HolidayInput): Promise<HolidayDetail> {
    return client.post('/admin/holidays', data).then((r) => r.data);
  },

  adminUpdateHoliday(id: number, data: HolidayInput): Promise<HolidayDetail> {
    return client.put(`/admin/holidays/${id}`, data).then((r) => r.data);
  },

  adminDeleteHoliday(id: number): Promise<void> {
    return client.delete(`/admin/holidays/${id}`).then(() => undefined);
  },

  adminCreateCategory(holidayId: number, data: { title: string; norm_crosses: number }): Promise<HolidayCategory> {
    return client.post(`/admin/holidays/${holidayId}/categories`, data).then((r) => r.data);
  },

  adminUpdateCategory(holidayId: number, categoryId: number, data: { title: string; norm_crosses: number }): Promise<HolidayCategory> {
    return client.put(`/admin/holidays/${holidayId}/categories/${categoryId}`, data).then((r) => r.data);
  },

  adminDeleteCategory(holidayId: number, categoryId: number): Promise<void> {
    return client.delete(`/admin/holidays/${holidayId}/categories/${categoryId}`).then(() => undefined);
  },

  adminUpdateCard(
    holidayId: number,
    cardId: number,
    data: { title: string; task_text?: string | null },
  ): Promise<HolidayCard> {
    return client.put(`/admin/holidays/${holidayId}/cards/${cardId}`, data).then((r) => r.data);
  },

  adminCreateExtraCard(
    holidayId: number,
    data: { category_id?: number | null; title: string; task_text?: string | null },
  ): Promise<HolidayCard> {
    return client.post(`/admin/holidays/${holidayId}/extra-cards`, data).then((r) => r.data);
  },

  adminDeleteCard(holidayId: number, cardId: number): Promise<void> {
    return client.delete(`/admin/holidays/${holidayId}/cards/${cardId}`).then(() => undefined);
  },

  adminUploadCategoryTrophy(holidayId: number, categoryId: number, file: File): Promise<{ trophy_image_url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/holidays/${holidayId}/categories/${categoryId}/trophy-image`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data);
  },

  adminClearCategoryTrophy(holidayId: number, categoryId: number): Promise<void> {
    return client.delete(`/admin/holidays/${holidayId}/categories/${categoryId}/trophy-image`).then(() => undefined);
  },

  adminPlayers(search?: string): Promise<PlayerEntry[]> {
    return client.get('/admin/players', { params: search ? { search } : {} }).then((r) => r.data);
  },

  adminPlayer(vkId: number): Promise<PlayerDetail> {
    return client.get(`/admin/players/${vkId}`).then((r) => r.data);
  },

  myReports(): Promise<PlayerReportEntry[]> {
    return client.get('/game/reports/my').then((r) => r.data);
  },

  info(): Promise<{ blocks: InfoBlock[] }> {
    return client.get('/info').then((r) => r.data);
  },

  adminSetInfo(blocks: InfoBlock[]): Promise<{ blocks: InfoBlock[] }> {
    return client.put('/admin/info', { blocks }).then((r) => r.data);
  },

  adminStatsDaily(day?: string): Promise<DailyStats> {
    return client.get('/admin/stats/daily', { params: day ? { day } : {} }).then((r) => r.data);
  },

  adminClearCardImage(holidayId: number, cardId: number): Promise<void> {
    return client.delete(`/admin/holidays/${holidayId}/cards/${cardId}/image`).then(() => undefined);
  },

  adminUploadCardImage(holidayId: number, cardId: number, file: File): Promise<{ image_url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/holidays/${holidayId}/cards/${cardId}/image`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  adminUploadHolidayAnimation(holidayId: number, file: File): Promise<{ animation_url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/holidays/${holidayId}/animation`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  adminClearHolidayAnimation(holidayId: number): Promise<void> {
    return client.delete(`/admin/holidays/${holidayId}/animation`).then(() => undefined);
  },

  adminUploadHolidayAudio(holidayId: number, file: File): Promise<{ audio_url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/holidays/${holidayId}/audio`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  adminClearHolidayAudio(holidayId: number): Promise<void> {
    return client.delete(`/admin/holidays/${holidayId}/audio`).then(() => undefined);
  },

  setMusicEnabled(enabled: boolean): Promise<MeUser> {
    return client.put('/me/music', { music_enabled: enabled }).then((r) => r.data);
  },

  adminUploadHolidayBg(holidayId: number, file: File): Promise<{ bg_image_url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/holidays/${holidayId}/bg-image`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  gameState(): Promise<GameState> {
    return client.get('/game/state').then((r) => r.data);
  },

  takeCard(cardId: number): Promise<GameState['active_task']> {
    return client.post(`/game/cards/${cardId}/take`).then((r) => r.data);
  },

  abandonTask(taskId: number): Promise<void> {
    return client.post(`/game/tasks/${taskId}/abandon`).then(() => undefined);
  },

  reportTask(
    taskId: number,
    amount: number,
    before: File,
    after: File,
    mode: 'norm' | 'penalty' = 'norm',
    preview?: File | null,
    saga?: File | null,
  ): Promise<{ ok: boolean; card_id: number; collected: boolean; mode: string }> {
    const compresses: Promise<File>[] = [compressImageSafe(before), compressImageSafe(after)];
    if (preview) compresses.push(compressImageSafe(preview));
    if (saga) compresses.push(compressImageSafe(saga));
    return Promise.all(compresses).then((files) => {
      const [b, a, p, s] = files;
      const form = new FormData();
      form.append('amount', String(amount));
      form.append('mode', mode);
      form.append('photo_before', b);
      form.append('photo_after', a);
      if (p) form.append('photo_preview', p);
      if (s) form.append('photo_saga', s);
      return client
        .post(`/game/tasks/${taskId}/report`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        .then((r) => r.data);
    });
  },

  collection(holidayId: number): Promise<Collection> {
    return client.get('/game/collection', { params: { holiday_id: holidayId } }).then((r) => r.data);
  },

  shop(): Promise<Shop> {
    return client.get('/shop').then((r) => r.data);
  },

  shopTake(cardId: number): Promise<{ ok: boolean; task_id: number; card_id: number; required_crosses: number }> {
    return client.post('/shop/take', { card_id: cardId }).then((r) => r.data);
  },

  rewards(): Promise<Rewards> {
    return client.get('/rewards').then((r) => r.data);
  },

  buyReward(itemId: number): Promise<{ ok: boolean; purchase_id: number; code: string; crystals_left: number }> {
    return client.post('/rewards/buy', { item_id: itemId }).then((r) => r.data);
  },

  adminRewardItems(): Promise<RewardItem[]> {
    return client.get('/admin/rewards/items').then((r) => r.data);
  },

  adminCreateRewardItem(data: { title: string; description?: string | null; price_crystals: number; is_active: boolean }): Promise<RewardItem> {
    return client.post('/admin/rewards/items', data).then((r) => r.data);
  },

  adminUpdateRewardItem(itemId: number, data: { title: string; description?: string | null; price_crystals: number; is_active: boolean }): Promise<RewardItem> {
    return client.put(`/admin/rewards/items/${itemId}`, data).then((r) => r.data);
  },

  adminDeleteRewardItem(itemId: number): Promise<void> {
    return client.delete(`/admin/rewards/items/${itemId}`).then(() => undefined);
  },

  adminUploadRewardImage(itemId: number, file: File): Promise<{ image_url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/rewards/items/${itemId}/image`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data);
  },

  adminAddCodes(itemId: number, codes: string[]): Promise<{ added: number; available: number }> {
    return client.post(`/admin/rewards/items/${itemId}/codes`, { codes }).then((r) => r.data);
  },

  adminListCodes(itemId: number): Promise<RewardCodeEntry[]> {
    return client.get(`/admin/rewards/items/${itemId}/codes`).then((r) => r.data);
  },

  adminDeleteCode(codeId: number): Promise<void> {
    return client.delete(`/admin/rewards/codes/${codeId}`).then(() => undefined);
  },

  appearance(): Promise<Appearance> {
    return client.get('/appearance').then((r) => r.data);
  },

  adminUploadAppearance(kind: 'game_bg' | 'collection_bg', file: File): Promise<{ url: string }> {
    const form = new FormData();
    form.append('file', file);
    return client
      .post(`/admin/appearance/${kind}/image`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data);
  },

  adminClearAppearance(kind: 'game_bg' | 'collection_bg'): Promise<void> {
    return client.delete(`/admin/appearance/${kind}/image`).then(() => undefined);
  },

  adminLogs(level?: string, limit = 50): Promise<LogEntry[]> {
    return client
      .get('/admin/logs', { params: { ...(level ? { level } : {}), limit } })
      .then((r) => r.data);
  },

  adminGameState(): Promise<{ game_open: boolean }> {
    return client.get('/admin/settings/game').then((r) => r.data);
  },

  adminSetGameState(game_open: boolean): Promise<{ game_open: boolean }> {
    return client.put('/admin/settings/game', { game_open }).then((r) => r.data);
  },
};
