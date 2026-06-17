# WC — World Cup Odds Analysis

2026 FIFA World Cup group-stage odds collection, signal analysis, and match prediction.

## Cursor Cloud specific instructions

- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`
- Match schedule and IDs: `worldcup_fids.json`
- Odds data: `data/w500/` (500.com history), `data/qiu/overview/` (球球初终盘)
- Do **not** re-run collectors unless the user asks — data is committed for offline analysis

### Common commands

```bash
# Predict or review a date (default: next upcoming)
python predict.py
python predict.py 2026-06-18

# Update finished match scores
python collectors/update_scores.py

# Validate data completeness
python tools/validate_data.py --finished

# Re-fetch empty 500.com AH/OU (needs network)
python collectors/collect_500.py --repair --finished

# Refresh qiu overview for finished matches
python collectors/collect_qiu.py --finished --force

# Regenerate HTML reports → output/
python reports/build_predict_report.py
python reports/build_dashboard.py
python reports/build_backtest.py
python reports/build_deep_analysis.py
python reports/build_simple_odds.py
```

### Collectors (need network)

```bash
python collectors/collect_500.py
python collectors/collect_qiu.py [date]
python collectors/collector.py qiu
```

Collectors call `odds.500.com` and `bifen.qiuqiushidao.com`.

### Core logic

- `predict.py` — `analyze_match_core()` is the single source of truth for predictions
- Reports import from `predict.py`; keep logic changes there
