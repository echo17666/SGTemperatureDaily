import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

SGT = timezone(timedelta(hours=8))
API_KEY = os.environ.get("WEATHER_API_KEY", "")
API_URL = (
    f"https://api.weather.com/v3/wx/observations/current"
    f"?apiKey={API_KEY}"
    f"&language=en-US&units=m&format=json&icaoCode=WSSS"
)


def fetch_temperature():
    req = urllib.request.Request(API_URL)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["temperature"]


def update_data(now, temperature):
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H:%M")
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{date_str}.json")

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            records = json.load(f)
    else:
        records = []

    records.append({"time": time_str, "temperature": temperature})
    with open(filepath, "w") as f:
        json.dump(records, f, indent=2)

    return date_str, records


def generate_svg_chart(date_str, records):
    if not records:
        return

    width = 800
    height = 400
    pad_left = 60
    pad_right = 30
    pad_top = 40
    pad_bottom = 60
    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bottom

    temps = [r["temperature"] for r in records]
    temp_min = min(temps) - 2
    temp_max = max(temps) + 2
    if temp_max == temp_min:
        temp_max = temp_min + 4

    def x_pos(i):
        if len(records) == 1:
            return pad_left + chart_w / 2
        return pad_left + i * chart_w / (len(records) - 1)

    def y_pos(t):
        return pad_top + chart_h - (t - temp_min) / (temp_max - temp_min) * chart_h

    # Build polyline points
    points = " ".join(f"{x_pos(i):.1f},{y_pos(r['temperature']):.1f}" for i, r in enumerate(records))

    # Build grid lines and Y-axis labels
    grid_lines = []
    y_labels = []
    step = max(1, round((temp_max - temp_min) / 5))
    y_val = int(temp_min)
    while y_val <= temp_max:
        y = y_pos(y_val)
        if pad_top <= y <= pad_top + chart_h:
            grid_lines.append(f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" y2="{y:.1f}" stroke="#e0e0e0" stroke-width="1"/>')
            y_labels.append(f'<text x="{pad_left - 10}" y="{y:.1f}" text-anchor="end" dominant-baseline="middle" fill="#666" font-size="12">{y_val}\u00b0C</text>')
        y_val += step

    # X-axis labels (show every N labels to avoid overlap)
    x_labels = []
    label_interval = max(1, len(records) // 10)
    for i, r in enumerate(records):
        if i % label_interval == 0 or i == len(records) - 1:
            x = x_pos(i)
            x_labels.append(f'<text x="{x:.1f}" y="{pad_top + chart_h + 20}" text-anchor="middle" fill="#666" font-size="11">{r["time"]}</text>')

    # Find first occurrence of max temperature
    max_temp = max(temps)
    max_idx = temps.index(max_temp)
    max_cx = x_pos(max_idx)
    max_cy = y_pos(max_temp)
    max_marker = f'<circle cx="{max_cx:.1f}" cy="{max_cy:.1f}" r="4" fill="#e74c3c"/>'
    max_label = f'<text x="{max_cx:.1f}" y="{max_cy - 10:.1f}" text-anchor="middle" fill="#e74c3c" font-size="13" font-weight="bold">{max_temp}\u00b0C</text>'

    # Latest value label
    last_label = ""
    if records:
        lx = x_pos(len(records) - 1)
        ly = y_pos(records[-1]["temperature"])
        last_label = f'<text x="{lx + 8:.1f}" y="{ly:.1f}" fill="#e74c3c" font-size="13" font-weight="bold" dominant-baseline="middle">{records[-1]["temperature"]}\u00b0C</text>'

    display_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <rect width="{width}" height="{height}" fill="white" rx="8"/>
  <text x="{width/2}" y="25" text-anchor="middle" font-size="16" font-weight="bold" fill="#333">Singapore Temperature (WSSS) - {display_date}</text>
  {"".join(grid_lines)}
  {"".join(y_labels)}
  {"".join(x_labels)}
  <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + chart_h}" stroke="#ccc" stroke-width="1"/>
  <line x1="{pad_left}" y1="{pad_top + chart_h}" x2="{width - pad_right}" y2="{pad_top + chart_h}" stroke="#ccc" stroke-width="1"/>
  <polyline points="{points}" fill="none" stroke="#e74c3c" stroke-width="2"/>
  {max_marker}
  {max_label}
  {last_label}
</svg>'''

    chart_path = os.path.join(os.path.dirname(__file__), "..", "chart.svg")
    with open(chart_path, "w") as f:
        f.write(svg)


def update_readme(date_str):
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    display_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    content = f"""# Singapore Weather Monitor

Real-time temperature monitoring for Singapore Changi Airport (WSSS).

Data collected every 5 minutes from 10:00 to 18:00 (UTC+8) via GitHub Actions.

## Today's Temperature ({display_date})

![Temperature Chart](chart.svg)

## Data

Historical data files are stored in the [`data/`](data/) directory, one JSON file per day.
"""
    with open(readme_path, "w") as f:
        f.write(content)


def main():
    now = datetime.now(SGT)
    print(f"Current time (SGT): {now.strftime('%Y-%m-%d %H:%M:%S')}")

    temperature = fetch_temperature()
    print(f"Temperature: {temperature}\u00b0C")

    date_str, records = update_data(now, temperature)
    print(f"Data file: data/{date_str}.json ({len(records)} records)")

    generate_svg_chart(date_str, records)
    print("Chart updated: chart.svg")

    update_readme(date_str)
    print("README updated")


if __name__ == "__main__":
    main()
