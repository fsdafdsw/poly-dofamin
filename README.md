# Polymarket Portfolio Telegram Alert

Скрипт принимает обычный публичный адрес кошелька, пытается определить через `GET https://gamma-api.polymarket.com/public-profile` соответствующий user profile address Polymarket, затем получает текущие позиции через `GET https://data-api.polymarket.com/positions` и отправляет сообщение в Telegram, если:

- какая-либо купленная позиция выросла больше чем на 30% относительно средней цены покупки;
- ваша позиция по рынку в итоге выиграла;
- ваша позиция по рынку в итоге проиграла.

Поведение:
- берёт открытые позиции пользователя;
- отдельно проверяет redeemable-позиции, чтобы поймать выигравшие рынки;
- подтягивает market status по slug, чтобы аккуратно определить проигравшие рынки после resolution;
- считает рост как `(curPrice - avgPrice) / avgPrice * 100`;
- отправляет алерт только при первом пересечении порога;
- если позиция потом снова падает ниже порога, триггер взводится заново.

## Быстрый запуск

1. Создайте виртуальное окружение:

```bash
cd /Users/slava/Downloads/poly-dofamin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Заполните `.env` на основе `.env.example`:

```env
POLYMARKET_WALLET_ADDRESS=0xYOUR_PUBLIC_WALLET_ADDRESS
TELEGRAM_BOT_TOKEN=123456789:your_bot_token
TELEGRAM_CHAT_ID=123456789
```

Важно: по документации Polymarket endpoint `/positions` ждёт `user profile address`, а `public-profile` умеет принимать адрес кошелька и возвращать `proxyWallet`. Поэтому здесь нужен обычный публичный адрес, а скрипт сам пытается резолвить его в нужный профильный адрес.

3. Проверьте без отправки в Telegram:

```bash
python3 main.py --dry-run
```

4. Запустите один проход с отправкой:

```bash
python3 main.py
```

5. Для постоянного мониторинга:

```bash
python3 main.py --loop
```

По умолчанию проверка идёт каждые 300 секунд.

## Настройки

Через `.env`:

- `ALERT_THRESHOLD_PERCENT=30`
- `POLL_INTERVAL_SECONDS=300`
- `REQUEST_TIMEOUT_SECONDS=20`
- `POSITIONS_PAGE_LIMIT=200`
- `STATE_PATH=state/portfolio_alert_state.json`
- `POLYMARKET_DATA_API_URL=https://data-api.polymarket.com`
- `POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com`

Через CLI:

```bash
python3 main.py --threshold-percent 150
python3 main.py --loop --poll-interval-seconds 120
```

## Как получить Telegram credentials

### `TELEGRAM_BOT_TOKEN`

- найдите в Telegram `@BotFather`;
- выполните `/newbot`;
- сохраните токен.

### `TELEGRAM_CHAT_ID`

- откройте чат с ботом и отправьте ему любое сообщение;
- откройте:

```text
https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```

- найдите `message.chat.id`.

## GitHub Actions каждые 15 минут

Workflow уже добавлен в [portfolio-alert.yml](/Users/slava/Downloads/poly-dofamin/.github/workflows/portfolio-alert.yml). После публикации репозитория на GitHub добавьте в `Settings -> Secrets and variables -> Actions` три секрета:

- `POLYMARKET_WALLET_ADDRESS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

После этого workflow будет сам запускаться каждые 15 минут и дополнительно его можно будет стартовать вручную из вкладки `Actions`.
State подавления повторных алертов сохраняется прямо в репозиторий через автокоммит `state/portfolio_alert_state.json`, так что бот не будет писать каждые 15 минут по одной и той же позиции, пока она просто остаётся выше порога.

## Локальный cron вместо loop

Если не хотите держать процесс открытым, можно запускать раз в 5 минут через cron:

```cron
*/5 * * * * cd /Users/slava/Downloads/poly-dofamin && /usr/bin/python3 main.py >> /tmp/poly-dofamin.log 2>&1
```

Если используете виртуальное окружение, подставьте путь к интерпретатору из `.venv/bin/python`.

## Примечания

- Состояние отправленных алертов хранится в `state/portfolio_alert_state.json`.
- Если Telegram недоступен или токены неверны, скрипт завершится с ошибкой.
- Скрипт ориентируется на поля `avgPrice` и `curPrice`, которые возвращает официальный endpoint Polymarket `/positions`.
- Для `WIN` бот опирается на `redeemable=true` либо на resolved market с settlement price `1.0` для вашего outcome.
- Для `LOSS` бот опирается на resolved market с settlement price `0.0` для вашего outcome.
- Для GitHub Actions state-файл хранится в репозитории и обновляется автоматически после прохода workflow.
