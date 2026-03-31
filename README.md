# yandex-wiki-mcp

MCP server для работы с [Яндекс Wiki](https://wiki.yandex.ru) через Claude Code и другие MCP-клиенты.

## Инструменты

| Инструмент | Описание |
|---|---|
| `wiki_get_page` | Получить страницу по slug (с контентом) |
| `wiki_get_page_by_id` | Получить страницу по числовому ID |
| `wiki_get_descendants` | Получить дерево подстраниц по slug |
| `wiki_get_descendants_by_id` | Получить дерево подстраниц по ID |
| `wiki_create_page` | Создать новую страницу |
| `wiki_update_page` | Обновить заголовок и/или контент страницы |
| `wiki_append_to_page` | Добавить текст в конец страницы |
| `wiki_delete_page` | Удалить страницу |
| `wiki_get_comments` | Получить комментарии страницы |
| `wiki_add_comment` | Добавить комментарий |
| `wiki_get_attachments` | Получить список вложений |
| `wiki_get_current_user` | Информация о текущем пользователе |

## Установка через uvx

```json
{
  "mcpServers": {
    "yandex-wiki": {
      "command": "uvx",
      "args": ["--python", "3.12", "yandex-wiki-mcp@latest"],
      "env": {
        "WIKI_IAM_TOKEN": "your-iam-token",
        "WIKI_CLOUD_ORG_ID": "your-cloud-org-id"
      }
    }
  }
}
```

Если у вас уже настроен Яндекс Трекер MCP — можно переиспользовать те же переменные:

```json
{
  "mcpServers": {
    "yandex-wiki": {
      "command": "uvx",
      "args": ["--python", "3.12", "yandex-wiki-mcp@latest"],
      "env": {
        "TRACKER_IAM_TOKEN": "your-iam-token",
        "TRACKER_CLOUD_ORG_ID": "your-cloud-org-id"
      }
    }
  }
}
```

Сервер принимает оба набора переменных (`WIKI_*` приоритетнее, `TRACKER_*` как запасной вариант).

## Аутентификация

Используется IAM-токен Яндекс Cloud. Получить токен:

```bash
yc iam create-token
```

IAM-токен действует до 12 часов. Для автообновления используйте [yt-refresh](https://github.com/MoshkaBortmanStar/yandex-wiki-mcp) скилл в Claude Code.

**Обязательные переменные окружения:**

| Переменная | Описание |
|---|---|
| `WIKI_IAM_TOKEN` или `TRACKER_IAM_TOKEN` | IAM-токен Яндекс Cloud |
| `WIKI_CLOUD_ORG_ID` или `TRACKER_CLOUD_ORG_ID` | ID организации Yandex Cloud (`X-Cloud-Org-Id`) |

## Добавление в Claude Code

```bash
claude mcp add yandex-wiki --scope user \
  -- uvx --python 3.12 yandex-wiki-mcp@latest
```

Затем добавьте env-переменные в `~/.claude.json` в секцию `mcpServers.yandex-wiki.env`.

## Локальная разработка

```bash
git clone https://github.com/MoshkaBortmanStar/yandex-wiki-mcp.git
cd yandex-wiki-mcp
uv venv && uv pip install -e .

export TRACKER_IAM_TOKEN=$(yc iam create-token)
export TRACKER_CLOUD_ORG_ID=your-org-id

python -m yandex_wiki_mcp
```

## Требования

- Python >= 3.10
- `mcp >= 1.0.0`
- `httpx >= 0.27.0`
