"""Submission checks. Accuracy is scored later, once EMI publishes the day's interim prices.
Prices may be zero or negative: the lowest daily mean at OTA2201 since 2023 was NZ$0.011/MWh,
and a nodal price can fall below zero, so any finite number is accepted."""

import json
import math
from pathlib import Path

from ale_verify import write

TASK = json.loads(Path("/home/user/input/task.json").read_text())
OUTPUT = Path("/home/user/output")


def forecast_problems(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["forecast.json is not an object"]
    problems = []
    if data.get("run_date") != TASK["run_date"]:
        problems.append(f"run_date must be {TASK['run_date']}")
    entries = data.get("forecasts")
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        return [*problems, "forecasts must be a list of objects"]
    dates = [entry.get("target_date") for entry in entries]
    if sorted(map(str, dates)) != sorted(TASK["target_dates"]):
        problems.append(f"target dates must be exactly {TASK['target_dates']}, got {dates}")
    levels = [str(level) for level in TASK["quantile_levels"]]
    for entry in entries:
        quantiles = entry.get("quantiles")
        if not isinstance(quantiles, dict) or sorted(quantiles) != sorted(levels):
            problems.append(f"{entry.get('target_date')}: quantile keys must be {levels}")
            continue
        values = [quantiles[level] for level in levels]
        if not all(
            isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)
            for v in values
        ):
            problems.append(f"{entry.get('target_date')}: values must be finite numbers")
        elif any(low > high for low, high in zip(values, values[1:], strict=False)):
            problems.append(f"{entry.get('target_date')}: quantiles decrease")
    return problems


def forecast_valid() -> dict:
    try:
        data = json.loads((OUTPUT / "forecast.json").read_text())
    except (OSError, ValueError) as exc:
        return {"score": 0.0, "diagnostic": f"forecast.json is unreadable: {exc}"}
    problems = forecast_problems(data)
    return {
        "score": float(not problems),
        "diagnostic": "; ".join(problems)[:2000] or "valid forecast",
    }


# Only the forecast is checked. Agents are asked to save their materials for the offline
# replay, but how they list them does not decide whether the forecast counts.
forecast_result = forecast_valid()
write({"reward": forecast_result["score"], "forecast_valid": forecast_result})
