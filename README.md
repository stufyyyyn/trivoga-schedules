# Public Poltava outage schedule

Validated public schedule from [Poltavaoblenergo](https://www.poe.pl.ua/disconnection/power-outages/).
No Telegram token, database credentials, subscriber identifiers or settings are stored here.

`data/poltava.json`: half-hour states for queues 1.1–6.2, Kyiv dates.
1 = power on, 2 = scheduled outage, 3 = switching window (power may be absent).

The collector runs on a standard GitHub Actions runner every five minutes, subject to
scheduler delays. Consumers must check `fetchedAt` and schedule dates before sending alerts.
If collection fails, the last file remains with its original timestamp.
