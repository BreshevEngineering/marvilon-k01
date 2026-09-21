# K01 Center — панель доказательств

Это локальный комплект интерфейса и HTTP-транспорта для существующего диспетчера. CAD, BOM и требования он не изменяет. Инженерные вердикты не вычисляет. При отсутствии движка или evidence показывает MISSING/ERROR.

## Запуск на вашей Windows

Распакуйте архив. Откройте терминал в распакованной папке и выполните:

```cmd
py -3 install.py --repo-root "D:\BreshevEngineering\marvilon-k01"
py -3 "D:\BreshevEngineering\marvilon-k01\center\panel\server.py" --repo-root "D:\BreshevEngineering\marvilon-k01"
```

Браузер откроется на http://127.0.0.1:8791 . Окно сервера оставьте открытым. Остановка — Ctrl+C. Если порт занят, используйте `--port 8792`. Пакеты Python не нужны: только стандартная библиотека Python 3.10+.

Установщик копирует файлы в `center/panel`. Существующий Center не удаляется, предыдущая версия panel резервируется. Известная точная версия присланного `tools/run.py` получает команду `center`. Более новая/другая версия диспетчера сохраняется. В этом случае прямой запуск выше работает независимо от интеграции команды center. Это новый интерфейс над вашими данными, не замена текущего reducer.

Если `tools/run.py`, `run.cmd` и canonical CLI отсутствуют, установщик раскладывает присланный диспетчер в ожидаемую им структуру. Самостоятельная установка не создаёт отсутствующие domain scripts. На действующем repository `run.cmd` не заменяется.

## Что изменено относительно v8

- Убраны инженерные числа и безусловные PASS/FROZEN из HTML.
- Overview: вердикт источника, дата расчёта, свежесть, причины блокеров и next_action, если передан.
- Nodes/requirements/gates и их зависимости; полный исходный граф доступен для просмотра.
- EBOM/MBOM: реальные строки, материалы, supplier, количество, статус и manufacturing transformations.
- Реестр артефактов: открытие/скачивание; preview PDF/PNG/JPEG/BMP. Только зарегистрированные пути.
- История последних 200 запусков и последних 12 Git commits; HEAD/branch. Данные Git читаются без commit/push.
- Источники: путь, physical SHA-256, время файла; semantic hashes остаются в исходных записях и доступны в раскрываемых деталях. Центр не выдаёт хеш файла за семантическую эквивалентность.
- Проверка физических inputs хешей, если источник их передал. Несовпадение показывается рядом с сохранённым вердиктом; источник не переписывается.
- Поиск по ID, причинам, материалам и файлам.
- Кнопки verdict/audit/selftest передают подкоманду существующему run.cmd; Linux — tools/run.py. Одновременный запуск второй команды через панель блокируется.
- Коды возврата показываются как execution result, а не автоматически как engineering PASS.

## Источники и конфигурация

`center/panel/config.json` сохраняется при повторной установке. Пример:

```json
{
  "verdict": "evidence/verdict.json",
  "graph": "control/graph.json",
  "ebom": "reports/bom/current/K01_EBOM_A001_CURRENT.json",
  "mbom": "reports/bom/current/K01_MBOM_A001_CURRENT.json",
  "artifacts": "evidence/current/K01_EVIDENCE_INDEX.json",
  "ledger": "evidence/ledger.jsonl",
  "cad_root": "D:/Marvilon/K01",
  "commands": {
    "verdict": ["verdict"],
    "audit": ["audit"],
    "selftest": ["selftest"]
  }
}
```

Если при первой установке verdict.json отсутствует, но есть `evidence/current/K01_CENTER_VIEW.json`, установщик явно записывает этот путь в config. Автоматического поиска «самого нового похожего файла» нет. Для актуального producer с другим путём меняйте конкретное поле. Ни один файл handoff не используется по умолчанию.

`cad_root` по умолчанию не задан. Для открытия native результатов за пределами repository задайте его как выше. Не подставляйте весь диск. Файлы вне разрешённых корней отображаются OUTSIDE_ROOT. Symlink-переход проверяется после разрешения пути.

## Контракт чтения — чтобы не обещать совместимость с неизвестными данными

Вердикт: JSON object, строка `overall`, `verdict` либо `status`; `nodes`, `requirements`, `gates`, `blockers` — list либо dictionary записей. Запись: `id`, `status`, `reasons`, optional `next_action`, `depends_on` и дополнительные поля. Дополнительные поля видны в «Исходная запись».

BOM: JSON object с `rows` или `items`, `status`, `issues`/`reasons`. Поддержаны поля PartNo/part_no, Description/description, Qty/qty/quantity, Material/material_authority/material, MakeBuy/make_buy, Supplier/supplier, release_status/release/status. Отсутствующий статус строки не превращается в PASS.

Artifacts: list или object с `artifacts`, `entries`, `items`; каждая запись содержит `id`, `path`/`file_path` и optional status. Индекс, содержащий только references на другие индексы, требует адаптации; центр не рекурсивно собирает случайные документы. CSV открывается текстом, PDF/изображения поддерживают preview; CAD скачивается и открывается пользователем в native приложении.

Ledger: JSONL. Ошибочные строки видны как diagnostic; hash-chain validation выполняет ваш engine/guard, центр её не заявляет. Git commits — история версий исходников, не автоматическая история выпуска изделий.

## Что обнаружено в присланном run.py

Присланный ZIP содержит только run.py и run.cmd. `tools/k01_verdict.py`, graph и domain scripts не приложены. Без них verdict не заработает; панель не заменяет их выдуманным reducer. Запуск отображает реальную ошибку.

Присланный run.cmd ожидает run.py в tools/, хотя внутри ZIP оба лежат рядом. В комплекте соблюдается ожидаемое размещение при новой установке. Остальной текущий CLI не заменяется по догадке.

В присланном диспетчере CAD availability привязана к pywin32; это не доказывает доступность/недоступность вашего C# SW2018 адаптера. Поэтому snapshot/build-all не добавлены в кнопки панели.

В том же диспетчере есть `--force` и неполное принуждение repo_guard. Панель не предлагает force. Существование локального Git hook само по себе не делает его необходным; обязательные release проверки нужно выполнять в release pipeline/CI. В этом комплекте правила выпуска и hooks не менялись.

HTTP API здесь выполняет только транспортную функцию: фиксированная команда из конфигурации → canonical dispatcher → журнал. В нём нет формул, release rules или самостоятельных CAD actions. Server привязан к loopback, проверяет Host/Origin и per-session token. Для multi-user/cloud это не готовая authentication-система.

## Проверки

Автоматические проверки: MISSING/ERROR, сохранение reasons/semantic hash, изменение input без подмены engineering verdict, path escape, malformed ledger, zero quantity, loopback HTTP/CSRF/command allowlist, сохранение неизвестного dispatcher. JavaScript syntax проверен Node.

Визуальный browser QA, выполнение Windows CMD и SolidWorks здесь не проводились. Полную совместимость с самым новым current-state schema нельзя подтвердить без соответствующих файлов.

## Дальнейшая интеграция

Действующий engine пишет verdict/evidence, панель читает его. Для подключения дополнительной подкоманды используйте только существующий dispatcher и конкретную allowlist запись после проверки её входов/guard. Не добавляйте произвольные shell строки или параметры из браузера. Для тяжёлых native действий отдельно требуется согласованный job lifecycle; по умолчанию они не включены.

Следующие инженерные работы K01 остаются P007/J2 closure, реальный D006, физическая сила fixed-coil и EBOM/MBOM. Центр отображает их доказательства; установка панели не закрывает эти вопросы.
