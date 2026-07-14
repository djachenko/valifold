# valifold — Project Guide

## Что это

Python-библиотека для валидации файловых и папочных структур через флюентный DSL. Вся конфигурация описывается Python-кодом.

Опубликована на PyPI: `pip install valifold`

---

## Место в экосистеме

```
justin ──→ valifold (валидация структуры фотосетов)
```

В `justin` планируется заменить `structure.py` на valifold. Пока не сделано.

---

## Как выглядит DSL

```python
from valifold.dsl import folder, file, anything
from valifold.pattern import w

structure = folder(
    w("my_project"),
    file(w("README.md")),
    file(w("*.py")),
    folder(
        w("tests"),
        file(w("test_*.py")),
        anything(),
    ),
)
```

`w(pattern)` — glob-паттерн. `anything()` — разрешить любое содержимое.

---

## Status

- **Последнее** — Проблема 5: RegexPattern переведён на `re.fullmatch` (full-string matching, breaking change для v0.3.0) (2026-07-14)
- **Следующее** — Проблема 6 (fnmatch case-sensitivity) или Coveralls → codecov; остальные баги в fix-bugs-batch
- **Блокеры** — —
- **Состояние** — активная доработка перед v0.3.0

---

## Стек

- Python 3.10+, hatchling
- pytest, pytest-cov для тестов
- Typing: строгая

---

## Текущее состояние

- Версия `0.2.3` на PyPI
- **Единственный проект с чистым git (0 dirty)** — в хорошем состоянии
- Активно не развивается, но стабильно используется

---

## Что нужно сделать

- Завершить миграцию `structure.py` → valifold в `justin` (задача на стороне justin)
- При необходимости расширить DSL под нужды justin

---

## Git

Semantic commits: `feat:`, `fix:`, `refactor:`, `chore:`
