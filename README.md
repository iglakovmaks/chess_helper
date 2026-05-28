# Chess Helper

Chess Helper — desktop-приложение с интерактивной шахматной доской и автоматическими подсказками лучшего хода от Stockfish.

![Chess Helper](website/assets/icon.png)

## Скачать

- Сайт проекта: **https://iglakovmaks.github.io/chess_helper_site/**
- macOS: `ChessHelper.dmg`
- Windows: `ChessHelper-Setup.exe`

## Что умеет приложение

- Ручной ввод позиции на доске (клики и перетаскивание фигур).
- Переключение стороны: играть за белых или чёрных.
- Автоматическая подсказка лучшего хода для текущей позиции.
- Визуальная стрелка рекомендованного хода на доске.
- История ходов, `Новая партия`, `Отменить ход`.
- Удобный pop-up для превращения пешки.
- Оффлайн-анализ через локальный движок Stockfish.

## Технологии

- Python 3
- Tkinter
- python-chess
- Stockfish (UCI)
- PyInstaller

## Запуск для разработки

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Сборка приложения

Важно: сборку нужно делать на той же ОС, для которой вы собираете приложение.

```bash
python -m pip install -r requirements.txt -r requirements-build.txt
python build_app.py
```

Опции:

```bash
python build_app.py --stockfish /path/to/stockfish
python build_app.py --icon /path/to/icon
python build_app.py --no-zip
```

### Windows (автоматизированная сборка)

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

Опции:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1 -StockfishPath C:\path\to\stockfish.exe
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1 -NoZip
```

### Windows через GitHub Actions

В репозитории есть workflow: `.github/workflows/build-windows.yml`.

- Запуск: **Actions → Build Windows Release → Run workflow**
- Результат: артефакт `ChessHelper-windows`

## Структура репозитория

- `app.py` — основное приложение.
- `build_app.py` — сборка через PyInstaller.
- `build_windows.ps1` — локальная автоматическая сборка Windows.
- `ChessHelperInstaller.iss` — Inno Setup-скрипт для `.exe`-инсталлятора.
- `website/` — лендинг и стили сайта загрузки.

## Примечание

Сборочные артефакты (`dist/`, `build/`, `release/`, `website/downloads/`) исключены из репозитория и не публикуются в исходниках.

## Автор

- GitHub: https://github.com/iglakovmaks

## License

MIT License. См. `LICENSE`.
