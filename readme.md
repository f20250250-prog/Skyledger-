# Skyledger — Aviation ERP for Odoo

An aviation management module built on Odoo that handles everything from network planning and fleet management to smart ticket pricing and passenger loyalty.

---

## Features

**Network & Scheduling**
Define airports, routes, and seat classes. Flight schedules auto-generate flight numbers and track state from draft through boarding, departure, landing, and completion.

**Smart Pricing Engine**
Every ticket price is calculated automatically using base fare, live Jet A-1 fuel surcharge, red-eye discount (15% off for 00:00–04:00 departures), weather surcharge, cargo subsidy, demand surge as occupancy rises, and a competitor cap that prevents pricing above 115% of the market average.

**Fleet Management**
Extends Odoo's fleet module with aircraft profiles — cabin seat configuration, range, cruise speed, and fuel capacity. Total seats flow directly into flight schedules.

**IoT Sensor Simulation**
Simulated engine temperature and fuel level readings per aircraft. Readings outside safe thresholds trigger an alert flag and are logged for review.

**Maintenance & Safety**
Aircraft with an open Emergency (AOG) maintenance request cannot be confirmed for flight. Completing a flight updates the aircraft odometer, and if it crosses a configurable threshold, a preventive maintenance request is raised automatically.

**Loyalty Programme**
Passengers earn frequent flyer points per flight based on distance and cabin class. Points unlock Silver (3% off), Gold (7% off), and Platinum (10% off) tiers applied automatically at booking.

**Invoicing**
Confirming a ticket generates an itemised invoice with separate lines for base fare, fuel surcharge, and any discounts. Prices are quoted in USD with an AED conversion.

**Analytics**
RASM and CASM dashboard with graph and pivot views, grouped by route and month.

---

## Installation

1. Copy the `aviation_erp` folder into your Odoo addons path
2. Restart Odoo and go to Apps → Update App List
3. Search for **Skyledger** and install

To upgrade after changes:
```
odoo-bin -u aviation_erp
```

## Dependencies

- `fleet`
- `maintenance`
- `account`
- `crm`
- `loyalty`

---

## Pre-loaded Data

The module ships with four airports (LOS, DXB, LHR, JFK) and two routes (LOS-DXB, DXB-LHR) ready to use out of the box.