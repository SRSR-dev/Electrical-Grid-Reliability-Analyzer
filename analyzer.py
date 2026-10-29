"""Small, transparent electrical grid reliability analysis project.

Dataset contains outage EVENTS. Each event affects some customers for a number of minutes.
Metrics here use the standard customer-based definitions:
  SAIFI = sum(customers_affected) / customers_served
  SAIDI = sum(customers_affected * duration_minutes) / customers_served
  CAIDI = SAIDI / SAIFI, if any customers were interrupted.

Example data are fictional and are NOT Con Edison operating data.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def load_events(path: Path) -> list[dict]:
    events = []
    with path.open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        required = {'event_id', 'date', 'neighborhood', 'cause', 'duration_minutes', 'customers_affected'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f'CSV must contain columns: {", ".join(sorted(required))}')
        for row in reader:
            try:
                duration = float(row['duration_minutes'])
                affected = int(row['customers_affected'])
                date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid data in event {row.get('event_id', '?')}: {exc}") from exc
            if duration < 0 or affected < 0:
                raise ValueError(f"Negative duration or customer count in event {row['event_id']}")
            events.append({'event_id': row['event_id'], 'date': date,
                           'neighborhood': row['neighborhood'], 'cause': row['cause'],
                           'duration_minutes': duration, 'customers_affected': affected})
    return events


def calculate_metrics(events: list[dict], customers_served: int) -> dict:
    if customers_served <= 0:
        raise ValueError('customers_served must be positive')
    interruptions = sum(e['customers_affected'] for e in events)
    customer_minutes = sum(e['customers_affected'] * e['duration_minutes'] for e in events)
    saifi = interruptions / customers_served
    saidi = customer_minutes / customers_served
    caidi = customer_minutes / interruptions if interruptions else 0.0
    return {'events': len(events), 'customers_served': customers_served,
            'customer_interruptions': interruptions, 'customer_interruption_minutes': customer_minutes,
            'saifi': saifi, 'saidi_minutes': saidi, 'caidi_minutes': caidi}


def make_charts(events: list[dict], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    monthly = defaultdict(float)
    by_cause = defaultdict(float)
    for e in events:
        minutes = e['duration_minutes'] * e['customers_affected']
        monthly[e['date'].strftime('%Y-%m')] += minutes
        by_cause[e['cause']] += minutes

    months = sorted(monthly)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(months, [monthly[m] for m in months])
    ax.set(title='Customer-interruption minutes by month', xlabel='Month', ylabel='Customer-minutes')
    ax.tick_params(axis='x', rotation=40)
    fig.tight_layout()
    fig.savefig(output / 'monthly_impact.png', dpi=150)
    plt.close(fig)

    causes = sorted(by_cause, key=by_cause.get)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(causes, [by_cause[c] for c in causes])
    ax.set(title='Customer-interruption minutes by reported cause', xlabel='Customer-minutes')
    fig.tight_layout()
    fig.savefig(output / 'cause_impact.png', dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyze fictional or supplied electric outage event records.')
    parser.add_argument('--data', type=Path, default=ROOT / 'data' / 'sample_outages.csv')
    parser.add_argument('--customers-served', type=int, default=10000,
                        help='Total customers served in the fictional example (default: 10000)')
    parser.add_argument('--output', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    events = load_events(args.data)

    seen_ids = set()

    for event in events:
        event_id = event['event_id']

        if not event_id or not event_id.strip():
            raise ValueError("An outage event is missing its ID.")

        if event_id in seen_ids:
            raise ValueError(f"Duplicate outage ID: {event_id}")

        seen_ids.add(event_id)

        if event['customers_affected'] > args.customers_served:
            raise ValueError(
                f"Event {event_id} affects more customers "
                f"than the system serves."
            )

        metrics = calculate_metrics(events, args.customers_served)
    make_charts(events, args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['metric', 'value'])
        writer.writerows(metrics.items())
    print(f"Events: {metrics['events']} | Customers served: {metrics['customers_served']:,}")
    print(f"SAIFI: {metrics['saifi']:.4f} interruptions/customer")
    print(f"SAIDI: {metrics['saidi_minutes']:.2f} minutes/customer")
    print(f"CAIDI: {metrics['caidi_minutes']:.2f} minutes/interruption")
    print(f"Saved summary and charts to: {args.output}")


if __name__ == '__main__':
    main()
