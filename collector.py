"""Publish only public half-hour schedule states, without credentials or subscribers."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from pathlib import Path
import json
import urllib.parse
import urllib.request

QUEUES = [f'{q}.{s}' for q in range(1, 7) for s in (1, 2)]
MONTHS = ['січня','лютого','березня','квітня','травня','червня','липня','серпня','вересня','жовтня','листопада','грудня']
URL = 'https://www.poe.pl.ua/customs/newgpv-info.php'

def clock(index):
    return f'{index // 2:02d}:{30 * (index % 2):02d}'

class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.queue_cell = False
        self.rows = {}
        self.text = []
        self.queue = ''
        self.cells = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'table' and 'gpv-table' in classes:
            self.inside = True
        if not self.inside:
            return
        if tag == 'tr':
            self.queue, self.cells = '', []
        if tag == 'td':
            self.queue_cell = 'gpv-q' in classes
            if 'gpv-c' in classes:
                states = [i for i in (1, 2, 3) if f'gpv-s{i}' in classes]
                if len(states) != 1:
                    raise ValueError('Unknown operator state')
                self.cells.append((states[0], attrs.get('title', '')))

    def handle_data(self, data):
        self.text.append(data)
        if self.inside and self.queue_cell:
            self.queue += data.strip()

    def handle_endtag(self, tag):
        if tag == 'td':
            self.queue_cell = False
        if tag == 'tr' and self.inside and self.queue:
            if self.queue not in QUEUES or self.queue in self.rows or len(self.cells) != 48:
                raise ValueError('Incomplete operator queue')
            for index, (_, title) in enumerate(self.cells):
                if not title.startswith(f'{self.queue}: {clock(index)}–{clock(index + 1)} — '):
                    raise ValueError('Unexpected half-hour time')
            self.rows[self.queue] = [state for state, _ in self.cells]
        if tag == 'table':
            self.inside = False

def parse_day(html, day):
    table = Table()
    table.feed(html)
    expected = f'{day.day} {MONTHS[day.month - 1]} {day.year} року'
    if expected not in ' '.join(table.text) or set(table.rows) != set(QUEUES):
        raise ValueError('Missing source date or queues')
    return {'date': day.isoformat(), 'available': True, 'queues': table.rows}

def collect():
    today = datetime.now(ZoneInfo('Europe/Kyiv')).date()
    days = []
    for delta in (0, 1):
        day = today + timedelta(days=delta)
        data = urllib.parse.urlencode({'seldate': json.dumps({'date_in': day.strftime('%d-%m-%Y')})}).encode()
        request = urllib.request.Request(URL, data=data, headers={'User-Agent': 'TrivogaSchedule/1.0 (+https://github.com/stufyyyyn/trivoga-schedules)'})
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read(500001).decode('utf-8')
        if len(html) > 500000:
            raise ValueError('Oversized response')
        days.append({'date': day.isoformat(), 'available': False, 'queues': {}} if delta and not html.strip() else parse_day(html, day))
    output = {'provider': 'poltava-official', 'sourceUrl': 'https://www.poe.pl.ua/disconnection/power-outages/', 'fetchedAt': datetime.now(ZoneInfo('UTC')).isoformat(), 'days': days}
    path = Path('data/poltava.json')
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'Validated {len(QUEUES)} queues for {today}')

if __name__ == '__main__':
    collect()
