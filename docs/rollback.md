# Откат к версии до исправлений код-ревью (2026-10-22)

## Точки отката

| Тег | Коммит | Что это |
|-----|--------|---------|
| `pre-review-fixes` | `d7b3994` | Состояние **до** исправлений по код-ревью |
| `review-fixes` | `3e711cf` | Состояние **сразу после** исправлений |

Исправления — это 9 коммитов `6b8d38b..3e711cf`. Они уже запушены в `origin/main`,
поэтому `git reset --hard` ничего не теряет: коммиты всегда можно вернуть тегом
`review-fixes` или через `origin/main`.

## Важное про миграции

В исправления входят две миграции, и обе **только создают/удаляют индексы**
(данные игроков не трогают, откат без потерь):

- `cb6a714ce613` — уникальные индексы лавки наград (`uq_rewardpurchase_code`,
  `uq_rewardcode_item_code`);
- `71fb5c8a0768` — индексы горячих запросов.

Старый код корректно работает с новой схемой БД, НО `alembic upgrade head`
на старом коде упадёт: в его папке миграций нет ревизии `71fb5c8a0768`,
на которую указывает БД. Поэтому порядок отката всегда такой:
**сначала откатить миграции (на новом коде), потом откатывать код**.

Ревизия, на которую откатываемся: `efc52c9790ed` (последняя до исправлений).

## Локально (dev, Windows)

```powershell
# 1. Ещё на новой версии — откатить миграции дев-БД:
cd api
.\venv\Scripts\python.exe -m alembic downgrade efc52c9790ed

# 2. Откатить код:
cd ..
git reset --hard pre-review-fixes

# 3. Перезапустить:
.\dev.ps1
```

## На сервере (если исправления уже задеплоены)

```bash
cd /opt/holidays/api
source venv/bin/activate
python -m alembic downgrade efc52c9790ed

cd /opt/holidays
git fetch origin
git reset --hard pre-review-fixes
systemctl restart holidays-api
```

Если нужно откатить ещё и **данные** (не только код) — восстановление из
полного архива: `./deploy/deploy.sh -recovery` (интерактивно, перед
распаковкой сам создаёт резервную копию текущего состояния).

## Вернуться к исправленной версии

```powershell
git fetch origin
git reset --hard review-fixes    # или origin/main, если после фиксов были ещё коммиты

cd api
.\venv\Scripts\python.exe -m alembic upgrade head
```

## Проверка, где мы сейчас

```powershell
git log --oneline -1                 # текущий коммит
git describe --tags                  # ближайший тег
cd api; .\venv\Scripts\python.exe -m alembic current   # текущая ревизия БД
```
