# yandex-wiki-mcp

MCP-сервер для работы с [Яндекс Вики](https://wiki.yandex.ru) из Claude Code и других MCP-клиентов.
Работает через публичный API Вики (`https://api.wiki.yandex.net/v1`) по stdio.

Это форк [MoshkaBortmanStar/yandex-wiki-mcp](https://github.com/MoshkaBortmanStar/yandex-wiki-mcp).
Сверх исходного проекта: вход по OAuth-токену Яндекс ID, чтение и запись динамических таблиц,
поиск, история правок страниц, пояснения API в текстах ошибок. Пакет `yandex-wiki-mcp-server` на PyPI
принадлежит исходному проекту и этих возможностей не содержит, поэтому форк ставится из git.

## Инструменты

| Инструмент | Описание |
|---|---|
| `wiki_get_page` | Страница по slug с содержимым; динамические таблицы раскрываются в Markdown |
| `wiki_get_page_by_id` | Страница по числовому ID, в том числе в старой ревизии (`revision_id`) |
| `wiki_get_descendants` | Дерево подстраниц по slug |
| `wiki_get_descendants_by_id` | Дерево подстраниц по ID |
| `wiki_search` | Полнотекстовый поиск по страницам и файлам |
| `wiki_get_revisions` | История правок страницы |
| `wiki_create_page` | Создать страницу |
| `wiki_update_page` | Изменить заголовок и/или содержимое страницы |
| `wiki_append_to_page` | Дописать текст в конец страницы |
| `wiki_delete_page` | Удалить страницу |
| `wiki_get_comments` | Комментарии страницы |
| `wiki_add_comment` | Добавить комментарий |
| `wiki_get_attachments` | Список вложений страницы |
| `wiki_get_grid` | Динамическая таблица по UUID (Markdown со столбцом `row_id` или JSON) |
| `wiki_update_grid_cells` | Изменить ячейки динамической таблицы |
| `wiki_add_grid_rows` | Добавить строки в динамическую таблицу |
| `wiki_get_current_user` | Текущий пользователь |

### Динамические таблицы

Таблицы (`{% wgrid id="UUID" %}`) не входят в текст страницы. `wiki_get_page` и
`wiki_get_page_by_id` по умолчанию подставляют под каждый маркер таблицу Markdown со столбцом
`row_id`; `expand_grids=false` возвращает исходный текст. Слаги столбцов для записи отдаёт
`wiki_get_grid` с `format=json`.

Старые табличные страницы (`page_type=grid`) публичный API не отдаёт: вместо пустой страницы
инструменты возвращают ошибку с подсказкой выгрузить таблицу из интерфейса (⋯ → Экспорт → CSV).

## Аутентификация

Основной способ: **OAuth-токен Яндекс ID** (`y0_…`). Он действует около года и подходит и для
Вики, и для Яндекс Трекера. Получить его можно через своё OAuth-приложение с правами
«Чтение/Запись Wiki» на https://oauth.yandex.ru.

Запасной способ: IAM-токен Яндекс Cloud (`yc iam create-token`). Он действует до 12 часов, и
его придётся регулярно обновлять в настройках клиента.

| Переменная | Описание |
|---|---|
| `WIKI_OAUTH_TOKEN` | OAuth-токен Яндекс ID, схема `OAuth`. Запасные имена: `TRACKER_OAUTH_TOKEN`, `TRACKER_TOKEN` |
| `WIKI_IAM_TOKEN` | IAM-токен Яндекс Cloud, схема `Bearer`; используется, только если OAuth-токен не задан. Запасное имя: `TRACKER_IAM_TOKEN` |
| `WIKI_CLOUD_ORG_ID` | ID организации Yandex Cloud, заголовок `X-Cloud-Org-Id`. Запасное имя: `TRACKER_CLOUD_ORG_ID` |

Переменные читаются при каждом запросе. Без токена сервер всё равно запускается, и каждый
инструмент возвращает ошибку с перечнем нужных переменных.

Имена `TRACKER_TOKEN` и `TRACKER_CLOUD_ORG_ID` совпадают с переменными
[yandex-tracker-mcp](https://github.com/aikts/yandex-tracker-mcp), поэтому настройки сервера
Трекера можно скопировать без изменений.

## Установка в Claude Code

```bash
claude mcp add yandex-wiki --scope user \
  -e WIKI_OAUTH_TOKEN=<y0_-токен> \
  -e WIKI_CLOUD_ORG_ID=<id организации> \
  -- uvx --from git+https://github.com/ssubbotin/yandex-wiki-mcp@master yandex-wiki-mcp-server
```

Или вручную в `~/.claude.json` (и в любом другом MCP-клиенте):

```json
{
  "mcpServers": {
    "yandex-wiki": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/ssubbotin/yandex-wiki-mcp@master",
        "yandex-wiki-mcp-server"
      ],
      "env": {
        "WIKI_OAUTH_TOKEN": "y0_...",
        "WIKI_CLOUD_ORG_ID": "your-cloud-org-id"
      }
    }
  }
}
```

`uvx` кэширует собранную версию. Чтобы подтянуть свежий `master`, перезапустите сервер с
`uvx --refresh --from git+…` или выполните `uv cache clean yandex-wiki-mcp-server`.

## Если сервер не подключается

Запустите команду из настроек вручную и передайте ей запрос initialize: так видна настоящая
ошибка, которую клиент показывает лишь как «connection closed».

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  | uvx --from git+https://github.com/ssubbotin/yandex-wiki-mcp@master yandex-wiki-mcp-server
```

Сервер написан под `mcp` 1.x (`mcp>=1.0.0,<2`). В `mcp` 2.x изменился интерфейс низкоуровневого
сервера, и без этого ограничения он падает при запуске с ошибкой
`'Server' object has no attribute 'list_tools'`.

## Локальная разработка

```bash
git clone https://github.com/ssubbotin/yandex-wiki-mcp.git
cd yandex-wiki-mcp
uv sync

export WIKI_OAUTH_TOKEN=<y0_-токен>
export WIKI_CLOUD_ORG_ID=<id организации>
uv run python -m yandex_wiki_mcp        # сервер на stdio
uv run python -m unittest -v            # тесты (без сети, запросы подменяются)
```

## Требования

- Python 3.10 или новее
- `mcp>=1.0.0,<2`
- `httpx>=0.27.0`
