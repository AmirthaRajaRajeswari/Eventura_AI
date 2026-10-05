"""
Eventura AI — synthetic data seed script.

Generates ~95 vendors across Wedding / Birthday / College Fest event types
and 4-6 knowledge documents per event type.

All data is SYNTHETIC and used for demonstration purposes only.
Prices and vendor details do NOT represent real market information.

Usage:
    cd eventura/backend
    python -m app.db.seed    (or run this file directly)

Fixed random seed ensures reproducibility.
"""

from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

# Seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ── Cities ────────────────────────────────────────────────────────────────────
CITIES = [
    ("Chennai", "Tamil Nadu"),
    ("Mumbai", "Maharashtra"),
    ("Bangalore", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Kolkata", "West Bengal"),
    ("Delhi", "Delhi"),
    ("Pune", "Maharashtra"),
    ("Coimbatore", "Tamil Nadu"),
]


def _uid() -> str:
    return str(uuid.UUID(int=random.getrandbits(128)))


def _pick(lst: list):
    return lst[random.randint(0, len(lst) - 1)]


def _price(base: int, spread: float = 0.3) -> float:
    delta = base * spread
    return round(base + random.uniform(-delta, delta), -2)


# ──────────────────────────────────────────────────────────────────────────────
# Vendor templates
# ──────────────────────────────────────────────────────────────────────────────

VENDOR_TEMPLATES: list[dict] = [
    # ── Wedding venues ────────────────────────────────────────────────────────
    {
        "category": "venue",
        "event_types": ["wedding"],
        "name_templates": [
            "{city} Grand Convention Hall",
            "Sri {city} Palace",
            "Royal Heritage {city}",
            "Majestic Garden {city}",
            "{city} Banquet Royale",
            "The Grand {city} Resort",
            "Annapoorna Convention Centre {city}",
            "Lotus Mandap {city}",
        ],
        "base_price_range": (150_000, 600_000),
        "price_floor_pct": 0.80,
        "price_per_guest": None,
        "capacity_range": (200, 2000),
        "min_notice": 30,
        "rating_range": (3.5, 5.0),
        "tags": ["banquet", "AC", "stage", "parking", "catering-allowed"],
        "description": (
            "A premium wedding venue with full air conditioning, stage, "
            "ample parking, and modern amenities. [SYNTHETIC DATA]"
        ),
    },
    # ── Wedding catering ──────────────────────────────────────────────────────
    {
        "category": "catering",
        "event_types": ["wedding"],
        "name_templates": [
            "Sri {city} Catering Services",
            "{city} Feast Masters",
            "Grand Kitchen {city}",
            "Bharat Caterers {city}",
            "Shree Annadanam {city}",
            "Royal Catering Co. {city}",
            "Heritage Foods {city}",
            "Spice Garden Caterers {city}",
        ],
        "base_price_range": (0, 0),  # uses price_per_guest
        "price_floor_pct": 0.85,
        "price_per_guest": (300, 900),
        "capacity_range": (100, 3000),
        "min_notice": 14,
        "rating_range": (3.8, 5.0),
        "tags": ["vegetarian", "non-vegetarian", "south-indian", "multi-cuisine"],
        "description": (
            "Full-service wedding catering with live counters, buffet, "
            "and traditional menus. [SYNTHETIC DATA]"
        ),
    },
    # ── Wedding decoration ────────────────────────────────────────────────────
    {
        "category": "decoration",
        "event_types": ["wedding", "birthday"],
        "name_templates": [
            "{city} Dream Décor",
            "Floral Fantasy {city}",
            "Royal Blooms {city}",
            "Petals & Lights {city}",
            "Grandeur Events {city}",
        ],
        "base_price_range": (50_000, 250_000),
        "price_floor_pct": 0.78,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 7,
        "rating_range": (3.7, 5.0),
        "tags": ["floral", "LED", "mandap", "stage-decor", "entrance"],
        "description": (
            "End-to-end event decoration including floral arrangements, "
            "LED lighting, and stage setups. [SYNTHETIC DATA]"
        ),
    },
    # ── Photography ───────────────────────────────────────────────────────────
    {
        "category": "photography",
        "event_types": ["wedding", "birthday", "college_fest"],
        "name_templates": [
            "{city} Lens Studio",
            "Moments by {city}",
            "Shutter Stories {city}",
            "Pixel Perfect {city}",
            "Candid Canvas {city}",
        ],
        "base_price_range": (40_000, 150_000),
        "price_floor_pct": 0.82,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 7,
        "rating_range": (3.8, 5.0),
        "tags": ["candid", "traditional", "drone", "same-day-edit", "album"],
        "description": (
            "Professional photography and videography services with "
            "edited deliverables within 30 days. [SYNTHETIC DATA]"
        ),
    },
    # ── Makeup ────────────────────────────────────────────────────────────────
    {
        "category": "makeup",
        "event_types": ["wedding"],
        "name_templates": [
            "Bridal Glow Studio {city}",
            "Makeover Magic {city}",
            "Royal Bridal Makeup {city}",
            "Ananya Bridal {city}",
        ],
        "base_price_range": (15_000, 60_000),
        "price_floor_pct": 0.85,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 7,
        "rating_range": (4.0, 5.0),
        "tags": ["bridal", "party-makeup", "airbrush", "hair-styling"],
        "description": (
            "Professional bridal makeup and hair styling services. [SYNTHETIC DATA]"
        ),
    },
    # ── Music / DJ ────────────────────────────────────────────────────────────
    {
        "category": "music",
        "event_types": ["wedding", "birthday", "college_fest"],
        "name_templates": [
            "DJ Beats {city}",
            "{city} Rhythm Masters",
            "Sound Wave Events {city}",
            "Melody Makers {city}",
        ],
        "base_price_range": (20_000, 80_000),
        "price_floor_pct": 0.80,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 7,
        "rating_range": (3.7, 5.0),
        "tags": ["DJ", "live-band", "sound-system", "MC"],
        "description": (
            "DJ and live entertainment services for weddings and events. [SYNTHETIC DATA]"
        ),
    },
    # ── Priest / Ritual ───────────────────────────────────────────────────────
    {
        "category": "ritual_services",
        "event_types": ["wedding"],
        "name_templates": [
            "Pandit Services {city}",
            "Vedic Rituals {city}",
            "Shastra Ceremonies {city}",
        ],
        "base_price_range": (5_000, 25_000),
        "price_floor_pct": 0.90,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 3,
        "rating_range": (4.0, 5.0),
        "tags": ["vedic", "tamil", "hindi", "Telugu", "multi-ritual"],
        "description": (
            "Experienced priests for Hindu wedding rituals and ceremonies. [SYNTHETIC DATA]"
        ),
    },
    # ── Transport ─────────────────────────────────────────────────────────────
    {
        "category": "transport",
        "event_types": ["wedding", "birthday"],
        "name_templates": [
            "{city} Royal Coaches",
            "Luxury Rides {city}",
            "Event Transport Co. {city}",
        ],
        "base_price_range": (15_000, 60_000),
        "price_floor_pct": 0.82,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 3,
        "rating_range": (3.8, 5.0),
        "tags": ["AC-buses", "luxury-cars", "floral-car"],
        "description": (
            "Event transportation services including luxury vehicles and shuttle buses. [SYNTHETIC DATA]"
        ),
    },
    # ── Birthday venues ───────────────────────────────────────────────────────
    {
        "category": "venue",
        "event_types": ["birthday"],
        "name_templates": [
            "{city} Party Hall",
            "Fun Zone {city}",
            "Celebration Hub {city}",
            "Birthday Palace {city}",
        ],
        "base_price_range": (10_000, 80_000),
        "price_floor_pct": 0.80,
        "price_per_guest": None,
        "capacity_range": (20, 300),
        "min_notice": 3,
        "rating_range": (3.5, 5.0),
        "tags": ["party-hall", "AC", "projector", "kids-friendly"],
        "description": (
            "Vibrant party venue equipped for birthday celebrations. [SYNTHETIC DATA]"
        ),
    },
    # ── Birthday cake ─────────────────────────────────────────────────────────
    {
        "category": "cake",
        "event_types": ["birthday"],
        "name_templates": [
            "Sugar Craft {city}",
            "Bake & Celebrate {city}",
            "The Cake Studio {city}",
            "Custom Cakes {city}",
        ],
        "base_price_range": (2_000, 15_000),
        "price_floor_pct": 0.88,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 3,
        "rating_range": (4.0, 5.0),
        "tags": ["custom-design", "fondant", "photo-cake", "multi-tier"],
        "description": (
            "Custom birthday cakes with designer themes and multi-tier options. [SYNTHETIC DATA]"
        ),
    },
    # ── Birthday entertainer ──────────────────────────────────────────────────
    {
        "category": "entertainer",
        "event_types": ["birthday"],
        "name_templates": [
            "Magic Show {city}",
            "Fun Clowns {city}",
            "Kids Entertainment {city}",
        ],
        "base_price_range": (5_000, 20_000),
        "price_floor_pct": 0.85,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 3,
        "rating_range": (4.0, 5.0),
        "tags": ["magic", "clown", "balloon-art", "games"],
        "description": (
            "Professional entertainers for birthday parties. [SYNTHETIC DATA]"
        ),
    },
    # ── College Fest venues ───────────────────────────────────────────────────
    {
        "category": "venue",
        "event_types": ["college_fest"],
        "name_templates": [
            "{city} Auditorium",
            "Open Air Arena {city}",
            "Convention Centre {city}",
            "{city} Cultural Ground",
        ],
        "base_price_range": (30_000, 200_000),
        "price_floor_pct": 0.80,
        "price_per_guest": None,
        "capacity_range": (200, 5000),
        "min_notice": 14,
        "rating_range": (3.5, 5.0),
        "tags": ["auditorium", "open-air", "backstage", "green-room"],
        "description": (
            "Large auditorium or open-air venue for college festivals. [SYNTHETIC DATA]"
        ),
    },
    # ── Sound & Lights ────────────────────────────────────────────────────────
    {
        "category": "sound_lights",
        "event_types": ["college_fest"],
        "name_templates": [
            "Thunder Sound {city}",
            "Electra Lights {city}",
            "Pro AV {city}",
        ],
        "base_price_range": (30_000, 150_000),
        "price_floor_pct": 0.80,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 7,
        "rating_range": (3.8, 5.0),
        "tags": ["line-array", "moving-heads", "fog-machine", "LED-wall"],
        "description": (
            "Professional sound and lighting systems for large events. [SYNTHETIC DATA]"
        ),
    },
    # ── Stage ─────────────────────────────────────────────────────────────────
    {
        "category": "stage",
        "event_types": ["college_fest"],
        "name_templates": [
            "Stage Builders {city}",
            "Event Stage Co. {city}",
            "Platform Pro {city}",
        ],
        "base_price_range": (20_000, 100_000),
        "price_floor_pct": 0.80,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 7,
        "rating_range": (3.7, 5.0),
        "tags": ["modular-stage", "truss", "backdrop", "LED-backdrop"],
        "description": (
            "Modular stage design and installation for college festivals. [SYNTHETIC DATA]"
        ),
    },
    # ── Permissions / Security ────────────────────────────────────────────────
    {
        "category": "permissions_security",
        "event_types": ["college_fest"],
        "name_templates": [
            "Event Security {city}",
            "Safe Event Management {city}",
        ],
        "base_price_range": (10_000, 50_000),
        "price_floor_pct": 0.85,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 14,
        "rating_range": (3.8, 5.0),
        "tags": ["security", "crowd-management", "police-liaison", "CCTV"],
        "description": (
            "Event security and permission facilitation services. [SYNTHETIC DATA]"
        ),
    },
    # ── Performers ────────────────────────────────────────────────────────────
    {
        "category": "performers",
        "event_types": ["college_fest"],
        "name_templates": [
            "Star Acts {city}",
            "Campus Performers {city}",
            "Live Stage {city}",
        ],
        "base_price_range": (20_000, 200_000),
        "price_floor_pct": 0.82,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 14,
        "rating_range": (4.0, 5.0),
        "tags": ["stand-up", "band", "dancer", "anchor"],
        "description": (
            "Performers and anchors for college cultural festivals. [SYNTHETIC DATA]"
        ),
    },
    # ── Banners / Printing ────────────────────────────────────────────────────
    {
        "category": "banners_printing",
        "event_types": ["college_fest"],
        "name_templates": [
            "Print Masters {city}",
            "Banner World {city}",
            "Event Printing {city}",
        ],
        "base_price_range": (5_000, 30_000),
        "price_floor_pct": 0.85,
        "price_per_guest": None,
        "capacity_range": (None, None),
        "min_notice": 3,
        "rating_range": (3.8, 5.0),
        "tags": ["flex", "standee", "brochure", "entry-gate"],
        "description": (
            "Event banners, standees, and printing services. [SYNTHETIC DATA]"
        ),
    },
    # ── Catering (college_fest + birthday) ────────────────────────────────────
    {
        "category": "catering",
        "event_types": ["college_fest", "birthday"],
        "name_templates": [
            "Campus Bites {city}",
            "Event Snacks {city}",
            "Quick Feast {city}",
            "Stall Masters {city}",
        ],
        "base_price_range": (0, 0),
        "price_floor_pct": 0.85,
        "price_per_guest": (100, 400),
        "capacity_range": (50, 5000),
        "min_notice": 7,
        "rating_range": (3.5, 5.0),
        "tags": ["canteen", "stalls", "snacks", "meals"],
        "description": (
            "Catering services for college events and parties. [SYNTHETIC DATA]"
        ),
    },
]


def generate_vendors() -> list[dict]:
    vendors: list[dict] = []

    for tmpl in VENDOR_TEMPLATES:
        names_used = set()
        # Limit to 5 cities per template to keep total around 90-100
        sampled_cities = [CITIES[0]] + random.sample(CITIES[1:], min(4, len(CITIES) - 1))

        for city, state in sampled_cities:
            # Only 1 vendor per city per template to control total count
            vendor_count = 3 if city == "Chennai" and tmpl["category"] in {
                "venue",
                "decoration",
                "photography",
                "catering",
            } else 1

            for name_tmpl in random.sample(
                tmpl["name_templates"],
                min(vendor_count, len(tmpl["name_templates"]))
            ):
                name = name_tmpl.replace("{city}", city)
                if name in names_used:
                    continue
                names_used.add(name)

                # Pricing
                ppg = tmpl["price_per_guest"]
                if ppg:
                    per_guest = round(random.uniform(*ppg), -1)
                    base_price = 0.0
                else:
                    base_price = _price(
                        int((tmpl["base_price_range"][0] + tmpl["base_price_range"][1]) / 2),
                        0.3,
                    )
                    per_guest = None

                # Capacity
                cap_min, cap_max = tmpl["capacity_range"]
                if cap_min:
                    min_cap = random.randint(cap_min, cap_min + 100)
                    max_cap = random.randint(cap_min + 200, cap_max)
                else:
                    min_cap = None
                    max_cap = None

                price_floor_pct = tmpl["price_floor_pct"]
                effective_price = base_price if base_price > 0 else (per_guest or 0) * 200
                price_floor = round(effective_price * price_floor_pct, -2)

                vendor = {
                    "id": _uid(),
                    "name": name,
                    "category": tmpl["category"],
                    "event_types": tmpl["event_types"],
                    "city": city,
                    "state": state,
                    "base_price": base_price,
                    "price_per_guest": per_guest,
                    "price_floor": price_floor,
                    "min_capacity": min_cap,
                    "max_capacity": max_cap,
                    "rating": round(random.uniform(*tmpl["rating_range"]), 1),
                    "tags": tmpl["tags"],
                    "description": tmpl["description"],
                    "contact_email": f"contact@{name.lower().replace(' ', '').replace('.', '')[:20]}.example.com",
                    "contact_phone": f"+91 {random.randint(7000000000, 9999999999)}",
                    "min_notice_days": tmpl["min_notice"],
                    "is_active": True,
                    "is_synthetic": True,
                }
                vendors.append(vendor)

    # Ensure we have ~90-100 vendors — pad if needed
    print(f"Generated {len(vendors)} vendors")
    return vendors


def generate_availability(vendors: list[dict]) -> list[dict]:
    """
    Create availability calendar entries only for key event demo dates.

    Full availability is generated lazily in the database seeder via
    a SQL-based approach. This file only seeds the specific dates
    needed for demo scenarios.
    """
    availability = []
    # Key demo dates used in scenarios
    demo_dates = [
        "2026-12-20", "2026-12-21",  # Wedding demo
        "2027-01-15",                 # Birthday demo
        "2027-02-14", "2027-02-15", "2027-02-16",  # College fest demo
    ]

    for vendor in vendors:
        for d in demo_dates:
            # All demo dates available by default
            availability.append(
                {
                    "id": _uid(),
                    "vendor_id": vendor["id"],
                    "date": d,
                    "is_available": True,
                    "booked_by_session": None,
                }
            )

    return availability


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge documents
# ──────────────────────────────────────────────────────────────────────────────

KNOWLEDGE_DOCS: list[dict] = [
    # ── Wedding ───────────────────────────────────────────────────────────────
    {
        "document_id": "WED-CHECKLIST",
        "document_title": "Complete Wedding Planning Checklist",
        "event_types": ["wedding", "general"],
        "content": """
# Complete Wedding Planning Checklist [SYNTHETIC DOCUMENT]

## 12 Months Before
- Set overall budget and discuss with family
- Create a preliminary guest list
- Research and shortlist venues
- Book key vendors: venue, caterer, photographer

## 6 Months Before
- Confirm venue booking with deposit
- Finalize catering menu and head count estimate
- Book decoration, makeup, and music vendors
- Send save-the-dates

## 3 Months Before
- Finalize guest list (firm count)
- Order wedding attire
- Plan honeymoon if applicable
- Confirm all vendor contracts

## 1 Month Before
- Send final guest count to caterer
- Confirm vendor arrival times
- Create run-of-show timeline
- Prepare vendor payments

## 1 Week Before
- Confirm all vendors one final time
- Brief family on the timeline
- Prepare wedding day emergency kit
- Final venue walk-through

## Day Before
- Decorate venue (if allowed early access)
- Brief the wedding coordinator
- Rest and prepare

## Day Of
- Follow the run-of-show
- Assign point-of-contact for each vendor
- Enjoy the celebration!

## Budget Allocation Guidelines (approximate)
- Venue: 25-35% of budget
- Catering: 30-40% of budget
- Photography/Video: 10-15% of budget
- Decoration: 10-15% of budget
- Makeup & Attire: 5-10% of budget
- Music/Entertainment: 5-8% of budget
- Miscellaneous: 5-10% of budget
        """,
    },
    {
        "document_id": "WED-VENDORS",
        "document_title": "Wedding Vendor Requirements Guide",
        "event_types": ["wedding"],
        "content": """
# Wedding Vendor Requirements Guide [SYNTHETIC DOCUMENT]

## Venue
- Minimum capacity: must accommodate all guests + 20% buffer
- Required amenities: bridal room, groom room, kitchen access, parking
- Check: noise restrictions, alcohol policy, decoration permissions
- Ideal booking window: 6-12 months in advance

## Catering
- Confirm: vegetarian/non-vegetarian ratio in guest list
- Standard wedding buffet: 15-20 items minimum
- Items to include: starters, main course, dessert, beverages
- South Indian weddings: traditional meals on banana leaf often preferred
- Catering rate typically charged per plate (per guest)

## Photography & Videography
- Book: main photographer + assistant minimum
- Deliverables: edited photos (300+), highlight reel (3-5 min), full video
- Clarify: drone usage permissions at venue
- Turnaround: 4-6 weeks for edited content

## Decoration
- Themes for South Indian weddings: traditional, floral, contemporary fusion
- Mandatory: stage/mandap setup, entrance gate, seating area
- Popular: marigold garlands, jasmine strings, LED lighting
- Discuss: colour palette and theme alignment

## Priest / Pandit
- Book: 4-6 weeks in advance minimum
- Discuss: muhurtham timing and duration
- Confirm: rituals to be performed (nagaswaram, nalangu, etc.)
- Provide: full names, star signs (nakshatra) for ritual purposes

## Mandatory Categories for Wedding
1. venue
2. catering
3. decoration
4. photography
        """,
    },
    {
        "document_id": "WED-BUDGET",
        "document_title": "Wedding Budget Planning Guide",
        "event_types": ["wedding"],
        "content": """
# Wedding Budget Planning Guide [SYNTHETIC DOCUMENT]

## How to Allocate a Wedding Budget

For a typical South Indian wedding with 500 guests and ₹15 lakh budget:

### Sample Allocation
| Category | % of Budget | Amount (₹15L) |
|---|---|---|
| Venue | 28% | ₹4,20,000 |
| Catering | 35% | ₹5,25,000 |
| Decoration | 12% | ₹1,80,000 |
| Photography | 10% | ₹1,50,000 |
| Makeup | 5% | ₹75,000 |
| Music | 4% | ₹60,000 |
| Ritual Services | 3% | ₹45,000 |
| Transport | 3% | ₹45,000 |

## Cost Factors
- Guest count is the primary cost driver for catering
- Venue price varies significantly by city tier
- Premium dates (auspicious muhurthams) command higher prices
- Weekend bookings are typically 20-30% more expensive

## Cost Control Strategies
- Book vendors 6+ months in advance for better rates
- Negotiate package deals with vendors
- Combine catering and venue bookings for discounts
- Limit premium decoration to key areas (stage, entrance)
- Choose photographers with competitive pricing over big names

## Warning Signs
- Vendor quotes significantly below market rate
- No written contract offered
- Demands for full payment upfront
- Unwillingness to provide references
        """,
    },
    {
        "document_id": "WED-TIMELINE",
        "document_title": "Wedding Day Run-of-Show Template",
        "event_types": ["wedding"],
        "content": """
# Wedding Day Run-of-Show Template [SYNTHETIC DOCUMENT]

## Two-Day South Indian Wedding Timeline

### Day 1 (Muhurtham Day)

| Time | Activity | Owner | Duration |
|---|---|---|---|
| 05:00 | Vendor setup begins | Coordinator | 2 hrs |
| 06:00 | Decoration team arrives | Decorator | 4 hrs |
| 07:00 | Catering setup | Caterer | 3 hrs |
| 08:00 | Bride & Groom makeup | Makeup artist | 2 hrs |
| 09:00 | Family photo session | Photographer | 1 hr |
| 10:00 | Guest arrival begins | Coordinator | 1 hr |
| 11:00 | Muhurtham ceremony | Priest | 2 hrs |
| 13:00 | Wedding lunch | Caterer | 2 hrs |
| 15:00 | Afternoon rituals (Nalangu) | Priest | 2 hrs |
| 17:00 | Evening reception setup | Decorator | 2 hrs |
| 18:00 | Evening reception | - | 3 hrs |
| 21:00 | Dinner service | Caterer | 2 hrs |
| 23:00 | Vendor departure / teardown | Coordinator | 1 hr |

### Day 2 (Reception/Saddi)

| Time | Activity | Owner | Duration |
|---|---|---|---|
| 09:00 | Venue setup | Coordinator | 2 hrs |
| 11:00 | Guest arrival | - | 1 hr |
| 12:00 | Lunch | Caterer | 2 hrs |
| 14:00 | Afternoon program | MC | 2 hrs |
| 16:00 | Tea/snacks | Caterer | 1 hr |
| 17:00 | Closing ceremony | Priest | 1 hr |
| 18:00 | Family farewell | - | 1 hr |
| 19:00 | Vendor teardown | Coordinator | 2 hrs |
        """,
    },
    {
        "document_id": "WED-VENUE-POLICY",
        "document_title": "Venue Booking Policies and Conditions",
        "event_types": ["wedding", "birthday", "college_fest"],
        "content": """
# Venue Booking Policies and Conditions [SYNTHETIC DOCUMENT]

## Standard Venue Booking Terms

### Payment Terms
- Booking deposit: 25-50% of total venue cost
- Balance payment: 7 days before event
- Refund policy: varies by venue (typically 50% if cancelled 30+ days in advance)

### Cancellation Policy
- 90+ days before: Full refund minus processing fee
- 60-89 days before: 75% refund
- 30-59 days before: 50% refund
- Less than 30 days: No refund (force majeure exceptions apply)

### Usage Restrictions
- External catering: some venues restrict to empanelled caterers
- Decoration: no nailing to walls; only approved suspension systems
- Noise: music typically permitted until 10 PM
- Alcohol: check local license requirements

### Mandatory Requirements
- Event insurance recommended for >500 person events
- Police permission required for events with alcohol
- Fire safety clearance required for events >1000 people
- Parking: ratio of 1 space per 4 guests recommended

### Capacity Rules
- Maximum occupancy must not be exceeded
- Clear aisles and emergency exits must be maintained
- Setup/teardown time is in addition to event hours
        """,
    },
    {
        "document_id": "WED-TAMIL",
        "document_title": "Tamil Wedding Traditions and Requirements",
        "event_types": ["wedding"],
        "content": """
# Tamil Wedding Traditions and Requirements [SYNTHETIC DOCUMENT]

## Key Rituals in a Tamil Brahmin Wedding
1. Nischayathartham (engagement) — typically held separately
2. Kashi Yathirai — groom pretends to leave for Kashi
3. Oonjal (swing ceremony)
4. Muhurtham — the main ceremony at the auspicious time
5. Sapthapathi — seven steps around the sacred fire
6. Nalangu — playful post-wedding rituals

## Nagaswaram
Traditional South Indian wind instrument played during ceremonies.
- Required for traditional Tamil weddings
- Typically played from early morning (6 AM) through the ceremony
- Alternative: recorded nagaswaram music if live musicians unavailable

## Mandap Requirements
- Traditional Tamil mandap: simple, flower-decorated
- Mandatory: sacred fire (homam) space
- Coconut tree decorations on entrance (traditional)
- Banana plants at entrance (auspicious)

## Auspicious Timing (Muhurtham)
- Determined by astrologer based on birth stars of couple
- Typically between 6 AM–12 PM for morning ceremonies
- Ceremony duration: 1.5–3 hours depending on rituals

## Food Traditions
- Formal sit-down meal on banana leaf (elai saapadu)
- Mandatory items: rice, sambar, rasam, kootu, poriyal, payasam
- Serving: typically by professional servers walking along rows
- Second serving (additional rounds) expected

## Dress Code Traditions
- Bride: Kanjivaram silk saree (typically gifted by groom's family)
- Groom: Silk dhoti and shirt
- Close family: silk attire expected
        """,
    },
    # ── Birthday ──────────────────────────────────────────────────────────────
    {
        "document_id": "BDAY-PLANNING",
        "document_title": "Birthday Party Planning Guide",
        "event_types": ["birthday", "general"],
        "content": """
# Birthday Party Planning Guide [SYNTHETIC DOCUMENT]

## Planning Timeline

### 4-6 Weeks Before
- Decide theme and guest list
- Book venue
- Send invitations

### 2-3 Weeks Before
- Order custom cake
- Book entertainment (if applicable)
- Plan decoration

### 1 Week Before
- Confirm guest RSVPs
- Finalize food/beverages
- Prepare party favors

## Budget Allocation (₹50,000 example)
| Category | % | Amount |
|---|---|---|
| Venue | 25% | ₹12,500 |
| Catering | 35% | ₹17,500 |
| Cake | 10% | ₹5,000 |
| Decoration | 15% | ₹7,500 |
| Entertainment | 10% | ₹5,000 |
| Photography | 5% | ₹2,500 |

## Theme Ideas
- Kids: Cartoon characters, superheroes, princesses
- Adults: Decade themes, travel, favourite movies
- Milestone (18/21/50): Elegant or nostalgic themes
        """,
    },
    {
        "document_id": "BDAY-VENDORS",
        "document_title": "Birthday Vendor Selection Guide",
        "event_types": ["birthday"],
        "content": """
# Birthday Vendor Selection Guide [SYNTHETIC DOCUMENT]

## Mandatory Categories
1. venue
2. catering
3. decoration

## Optional But Popular
- cake (custom)
- entertainer (especially for kids)
- photography

## Venue Tips
- Home-based parties: reduce venue cost significantly
- Party halls: typically ₹5,000–₹50,000 depending on size
- Restaurant buyout: convenient for adult parties

## Catering Tips
- Finger foods and snacks work well for short parties
- Full meal service for evening parties
- Consider dietary restrictions and age group

## Entertainment Tips
- For children < 10: magician, clown, balloon artist
- For teenagers: DJ, game setup, photo booth
- For adults: live music, trivia games
        """,
    },
    {
        "document_id": "BDAY-KIDS",
        "document_title": "Kids Birthday Party Special Requirements",
        "event_types": ["birthday"],
        "content": """
# Kids Birthday Party Special Requirements [SYNTHETIC DOCUMENT]

## Safety Requirements
- All hired entertainers should have background checks
- Venue should be childproofed
- Food allergies must be communicated to caterer
- Age-appropriate activities only

## Food Considerations
- Avoid choking hazards for children under 3
- Popular: pizza, sandwiches, pasta, juice boxes
- Cake: consider common allergens (nuts, dairy)

## Activity Timing
- Keep party duration to 2-3 hours maximum for young children
- Schedule food after activities to prevent excitement-related issues
- Include a wind-down activity before departure

## Decoration Safety
- Avoid small balloon pieces that could be choking hazards
- Ensure decorations are secured and cannot fall
- Streamers and banners at adult height
        """,
    },
    # ── College Fest ──────────────────────────────────────────────────────────
    {
        "document_id": "FEST-PLANNING",
        "document_title": "College Fest Complete Planning Guide",
        "event_types": ["college_fest", "general"],
        "content": """
# College Fest Complete Planning Guide [SYNTHETIC DOCUMENT]

## Typical Fest Structure
- Technical events: coding, robotics, quizzes
- Cultural events: dance, music, drama, fine arts
- Pro-show: professional performer/band on final evening

## Planning Timeline

### 3 Months Before
- Form organizing committee with roles
- Seek institutional approval
- Finalize event calendar and categories
- Reach out to sponsors

### 2 Months Before
- Book venue, stage, sound, and lights
- Finalize pro-show performer
- Launch registration

### 1 Month Before
- Confirm all bookings
- Finalize schedule
- Assign coordinators per event
- Prepare contingency plans

### 1 Week Before
- Technical rehearsal for stage events
- Brief all volunteers
- Confirm catering arrangements

## Budget Allocation (₹5 lakh example)
| Category | % | Amount |
|---|---|---|
| Venue | 15% | ₹75,000 |
| Sound & Lights | 20% | ₹1,00,000 |
| Stage | 15% | ₹75,000 |
| Pro-show Performer | 25% | ₹1,25,000 |
| Catering | 15% | ₹75,000 |
| Printing & Banners | 5% | ₹25,000 |
| Security | 5% | ₹25,000 |

## Required Permissions
- Institution/university approval
- Local police intimation (for events >500 people)
- Fire NOC for indoor events
- Noise permit for outdoor/late-night events
        """,
    },
    {
        "document_id": "FEST-STAGE",
        "document_title": "College Fest Stage and Technical Requirements",
        "event_types": ["college_fest"],
        "content": """
# College Fest Stage and Technical Requirements [SYNTHETIC DOCUMENT]

## Stage Specifications
- Minimum stage dimensions: 40ft x 30ft for main stage
- Height: 3-4 feet from ground level
- Backstage access from both wings
- Green room: 2 minimum (performers and judges/VIPs)

## Sound System Requirements
- Line array speakers: minimum 2 stacks
- Subwoofers: 4 minimum for outdoor events
- Stage monitors: 4-6 wedge monitors
- Mixing console: 32 channel minimum
- Wireless microphones: 4 minimum (2 handheld + 2 lapel)
- DJ setup: CDJs + mixer

## Lighting Requirements
- Moving head lights: 8-12 minimum
- LED par cans: 20+ for wash lighting
- Follow spot: 1-2 minimum for performers
- Gobo lights for logo/pattern projection
- Hazers and fog machines for effect

## Power Requirements
- Generator: 80-100 KVA for full sound + lights
- Separate circuits for sound and lights
- UPS backup for mixing console

## Setup Timeline
- D-2: Stage construction begins
- D-1: Sound and lights rigging
- D-1 evening: Full technical rehearsal
- D-day: Final checks 3 hours before event
        """,
    },
    {
        "document_id": "FEST-PERMISSIONS",
        "document_title": "Event Permissions and Legal Requirements",
        "event_types": ["college_fest", "general"],
        "content": """
# Event Permissions and Legal Requirements [SYNTHETIC DOCUMENT]

## Required Permissions for Large Events (>500 people)

### Police Permissions
- File intimation with local police station 15 days before
- For events with >1000 attendees: formal permission letter required
- Night events (after 10 PM): special permission needed
- Provide: event details, venue, expected attendance, security arrangements

### Fire Department
- NOC required for indoor events >500 people
- Inspection of venue fire exits and extinguishers
- Application 21 days before event

### Noise Pollution
- Outdoor sound: permitted until 10 PM (varies by state)
- Sound levels: 65 dB(A) daytime, 55 dB(A) night (residential areas)
- Check local municipal noise ordinances

### FSSAI / Food Safety
- Temporary food stalls require FSSAI registration
- Caterers should provide valid FSSAI license

### Performer Contracts
- Written contract with all performers
- Advance: typically 50% of fee
- Cancellation clause: 30-day notice minimum

## Insurance
- Event liability insurance recommended for >1000 attendees
- Covers: accidents, property damage, cancellation
        """,
    },
    {
        "document_id": "GENERAL-DISRUPTION",
        "document_title": "Event Disruption and Contingency Planning",
        "event_types": ["wedding", "birthday", "college_fest", "general"],
        "content": """
# Event Disruption and Contingency Planning [SYNTHETIC DOCUMENT]

## Common Disruption Scenarios

### Vendor Cancellation
- Immediate action: Contact backup vendors
- Venue cancellation: Most critical — escalate immediately
- Catering: Secondary options within same city
- Other vendors: Usually replaceable within 48-72 hours

### Budget Changes
- 10-15% reduction: Negotiate with current vendors first
- 15-25% reduction: Consider downgrading one major category
- >25% reduction: Full replanning required

### Weather Events
- Outdoor events: Have indoor backup venue identified
- Monsoon season: Avoid outdoor events June-September
- Setup delays: Build 2-hour buffer into setup timeline

### Key Person Unavailability
- Priest/Pandit: Always have backup contact
- Key vendor staff: Request named lead + backup in contract

## Negotiation for Emergency Replacements
- Lead with urgency — vendors respond faster
- Expect 10-20% premium for short-notice bookings
- Check vendor availability first before price negotiation

## Communication Plan
- Create WhatsApp group with all vendor contacts
- Assign single point of contact per vendor
- Emergency contact list for venue and key family members
        """,
    },
]


def get_knowledge_chunks() -> list[dict]:
    """Split knowledge documents into overlapping chunks for retrieval."""
    chunks = []
    chunk_size = 800  # characters
    overlap = 100

    for doc in KNOWLEDGE_DOCS:
        content = doc["content"].strip()
        start = 0
        chunk_index = 0

        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_text = content[start:end]

            # Try to break at paragraph boundary — only if we haven't hit EOF
            if end < len(content):
                last_para = chunk_text.rfind("\n\n")
                if last_para > chunk_size // 2:
                    end = start + last_para + 2
                    chunk_text = content[start:end]

            text = chunk_text.strip()
            if text:
                chunks.append(
                    {
                        "id": _uid(),
                        "document_id": doc["document_id"],
                        "document_title": doc["document_title"],
                        "event_types": doc["event_types"],
                        "chunk_index": chunk_index,
                        "content": text,
                        "metadata_": {
                            "document_id": doc["document_id"],
                            "chunk_index": chunk_index,
                        },
                        "embedding": None,  # computed during seeding
                    }
                )
                chunk_index += 1

            # Advance — ensure we always move forward to avoid infinite loop
            next_start = end - overlap
            if next_start <= start:
                next_start = start + max(chunk_size - overlap, 1)
            start = next_start

    return chunks


def main() -> None:
    """Entry point — writes seed data to JSON files in data/."""
    output_dir = Path(__file__).parent

    vendors = generate_vendors()
    availability = generate_availability(vendors)
    chunks = get_knowledge_chunks()

    # Write vendors (compact)
    with open(output_dir / "vendors.json", "w", encoding="utf-8") as f:
        json.dump(vendors, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Wrote {len(vendors)} vendors -> data/vendors.json")

    # Write availability (compact)
    with open(output_dir / "availability.json", "w", encoding="utf-8") as f:
        json.dump(availability, f, separators=(",", ":"))
    print(f"Wrote {len(availability)} availability records -> data/availability.json")

    # Write knowledge chunks (compact)
    knowledge_dir = output_dir / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    with open(knowledge_dir / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Wrote {len(chunks)} knowledge chunks -> data/knowledge/chunks.json")


if __name__ == "__main__":
    main()
