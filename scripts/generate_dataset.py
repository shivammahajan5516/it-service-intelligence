#!/usr/bin/env python3
"""
Synthetic dataset generator for the IT Service Intelligence Platform.

Fictional company: Northbridge Managed Services Ltd (a UK managed IT
services provider). ALL DATA IS SYNTHETIC. No real customers, people
or incidents are represented.

The generator is fully deterministic for a given --seed. It produces:

    data/raw/tickets.csv
    data/raw/customers.csv
    data/raw/agents.csv
    data/raw/support_teams.csv
    data/raw/sla_targets.csv
    data/raw/calendar.csv
    data/raw/incident_categories.csv
    data/raw/manifest.json              (row counts + SHA-256 per file)
    data/reference/dq_injection_log.csv (answer key of injected DQ issues)

Design principle: business patterns are produced by explicit,
documented mechanisms (see docs/06_synthetic_data_design.md), not by
hard-coding the outputs. KPIs are therefore *emergent* and must be
measured, not assumed.

Usage:
    python scripts/generate_dataset.py               # default seed 42
    python scripts/generate_dataset.py --seed 7 --out /tmp/x
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------
DEFAULT_SEED = 42
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2025-12-31")
SNAPSHOT = pd.Timestamp("2025-12-31 23:59:59")  # extract taken at this moment
TARGET_BASE_TICKETS = 22_000                     # before spikes / duplicates
PRIORITIES = ["P1", "P2", "P3", "P4"]
TS_FMT = "%Y-%m-%d %H:%M:%S"

# England & Wales bank holidays for the dataset period
UK_BANK_HOLIDAYS = {
    "2024-01-01": "New Year's Day", "2024-03-29": "Good Friday",
    "2024-04-01": "Easter Monday", "2024-05-06": "Early May Bank Holiday",
    "2024-05-27": "Spring Bank Holiday", "2024-08-26": "Summer Bank Holiday",
    "2024-12-25": "Christmas Day", "2024-12-26": "Boxing Day",
    "2025-01-01": "New Year's Day", "2025-04-18": "Good Friday",
    "2025-04-21": "Easter Monday", "2025-05-05": "Early May Bank Holiday",
    "2025-05-26": "Spring Bank Holiday", "2025-08-25": "Summer Bank Holiday",
    "2025-12-25": "Christmas Day", "2025-12-26": "Boxing Day",
}

# team_id, name, tier, primary location, operating model, headcount
TEAMS = [
    ("T01", "Service Desk", "L1", "Manchester Hub", "24x7", 18),
    ("T02", "End User Computing", "L2", "Manchester Hub", "Business Hours", 10),
    ("T03", "Network Operations", "L2/L3", "London HQ", "24x7", 7),
    ("T04", "Infrastructure & Cloud", "L3", "London HQ", "Business Hours + On-call", 11),
    ("T05", "Application Support", "L2/L3", "Bristol Office", "Business Hours", 12),
    ("T06", "Identity & Access Management", "L2", "Glasgow Hub", "Business Hours", 7),
    ("T07", "Security Operations", "L3", "London HQ", "24x7", 8),
    ("T08", "Database Services", "L3", "Bristol Office", "Business Hours + On-call", 7),
]
TWENTY_FOUR_SEVEN = {"T01", "T03", "T07"}

# subcategory_id, category, subcategory, team, complexity, is_service_request,
# volume weight, can_be_monitoring_alert
CATEGORIES = [
    ("SC01", "Access & Identity", "Password Reset", "T01", "Low", True, 4.6, False),
    ("SC02", "Access & Identity", "Account Lockout", "T01", "Low", False, 3.6, False),
    ("SC03", "Access & Identity", "MFA Issue", "T06", "Medium", False, 3.2, False),
    ("SC04", "Access & Identity", "Permission Request", "T06", "Low", True, 3.6, False),
    ("SC05", "Access & Identity", "SSO Failure", "T06", "High", False, 1.6, True),
    ("SC06", "Hardware", "Laptop / Desktop Fault", "T02", "Medium", False, 4.4, False),
    ("SC07", "Hardware", "Printer Issue", "T02", "Low", False, 2.6, False),
    ("SC08", "Hardware", "Peripheral Request", "T02", "Low", True, 2.0, False),
    ("SC09", "Hardware", "Mobile Device", "T02", "Medium", False, 2.0, False),
    ("SC10", "Software", "Software Installation", "T02", "Low", True, 3.4, False),
    ("SC11", "Software", "Licensing", "T02", "Low", True, 1.8, False),
    ("SC12", "Software", "Application Crash", "T05", "Medium", False, 3.0, False),
    ("SC13", "Software", "Performance Degradation", "T05", "High", False, 2.4, True),
    ("SC14", "Email & Collaboration", "Mailbox Issue", "T01", "Low", False, 4.8, False),
    ("SC15", "Email & Collaboration", "Microsoft Teams", "T01", "Low", False, 4.0, False),
    ("SC16", "Email & Collaboration", "SharePoint / OneDrive", "T01", "Medium", False, 3.2, False),
    ("SC17", "Network", "VPN Connectivity", "T03", "Medium", False, 4.2, False),
    ("SC18", "Network", "Wi-Fi", "T03", "Medium", False, 2.8, False),
    ("SC19", "Network", "LAN / Switching", "T03", "High", False, 2.2, True),
    ("SC20", "Network", "Firewall Rule Change", "T03", "Medium", True, 2.2, False),
    ("SC21", "Network", "DNS / DHCP", "T03", "High", False, 1.6, True),
    ("SC22", "Infrastructure", "Server Outage", "T04", "High", False, 1.8, True),
    ("SC23", "Infrastructure", "Storage Capacity", "T04", "Medium", False, 2.0, True),
    ("SC24", "Infrastructure", "Backup Failure", "T04", "Medium", False, 2.4, True),
    ("SC25", "Infrastructure", "Virtualisation", "T04", "High", False, 1.6, True),
    ("SC26", "Cloud Services", "Azure Resource Issue", "T04", "High", False, 2.4, True),
    ("SC27", "Cloud Services", "AWS Resource Issue", "T04", "High", False, 1.4, True),
    ("SC28", "Cloud Services", "Cloud Access Request", "T04", "Low", True, 1.8, False),
    ("SC29", "Business Applications", "ERP Issue", "T05", "High", False, 2.6, False),
    ("SC30", "Business Applications", "CRM Issue", "T05", "Medium", False, 2.4, False),
    ("SC31", "Business Applications", "Integration / API Failure", "T05", "High", False, 2.0, True),
    ("SC32", "Security", "Phishing Report", "T07", "Low", False, 2.6, False),
    ("SC33", "Security", "Malware Detection", "T07", "High", False, 1.0, True),
    ("SC34", "Security", "Suspicious Sign-in", "T07", "Medium", False, 1.6, True),
    ("SC35", "Security", "Data Loss Prevention Alert", "T07", "Medium", False, 1.0, True),
    ("SC36", "Database", "Query Performance", "T08", "High", False, 1.4, True),
    ("SC37", "Database", "Database Connectivity", "T08", "Medium", False, 1.2, True),
    ("SC38", "Database", "Backup / Restore Request", "T08", "Medium", True, 1.0, False),
    ("SC39", "Database", "Data Correction Request", "T08", "Low", True, 1.2, False),
]

ROOT_CAUSES_BY_CATEGORY = {
    "Access & Identity": {"User Error": .45, "Configuration Error": .20, "Known Error": .10,
                          "Software Defect": .05, "Change-Related": .08,
                          "Security Threat": .04, "Undetermined": .08},
    "Hardware": {"Hardware Failure": .50, "User Error": .15, "Configuration Error": .10,
                 "Third-Party / Vendor": .10, "Software Defect": .05, "Undetermined": .10},
    "Software": {"Software Defect": .35, "Configuration Error": .20, "Change-Related": .12,
                 "Capacity / Performance": .10, "Known Error": .10, "User Error": .08,
                 "Undetermined": .05},
    "Email & Collaboration": {"User Error": .30, "Configuration Error": .25,
                              "Third-Party / Vendor": .15, "Known Error": .10,
                              "Change-Related": .10, "Undetermined": .10},
    "Network": {"Configuration Error": .30, "Network Connectivity": .20,
                "Third-Party / Vendor": .15, "Hardware Failure": .10, "Change-Related": .15,
                "Capacity / Performance": .05, "Undetermined": .05},
    "Infrastructure": {"Capacity / Performance": .25, "Hardware Failure": .20,
                       "Configuration Error": .18, "Change-Related": .17,
                       "Software Defect": .10, "Third-Party / Vendor": .05,
                       "Undetermined": .05},
    "Cloud Services": {"Configuration Error": .35, "Change-Related": .20,
                       "Third-Party / Vendor": .20, "Capacity / Performance": .15,
                       "Undetermined": .10},
    "Business Applications": {"Software Defect": .35, "Change-Related": .20,
                              "Configuration Error": .15, "Third-Party / Vendor": .10,
                              "Known Error": .10, "User Error": .05, "Undetermined": .05},
    "Security": {"Security Threat": .60, "User Error": .20, "Configuration Error": .10,
                 "Undetermined": .10},
    "Database": {"Capacity / Performance": .30, "Configuration Error": .20,
                 "Software Defect": .15, "Change-Related": .20, "User Error": .05,
                 "Undetermined": .10},
}

# Multiplier on hands-on work time by root cause
ROOT_CAUSE_TIME_MULT = {
    "Change-Related": 1.35, "Third-Party / Vendor": 1.70, "Hardware Failure": 1.30,
    "Capacity / Performance": 1.20, "User Error": 0.65, "Known Error": 0.95,
    "Configuration Error": 1.00, "Software Defect": 1.25, "Security Threat": 1.10,
    "Network Connectivity": 1.15, "Undetermined": 1.25, "Service Request": 1.00,
}

RESOLUTION_TYPES_BY_ROOT = {
    "User Error": {"User Education": .70, "Configuration Change": .20, "No Fault Found": .10},
    "Configuration Error": {"Configuration Change": .75, "Workaround": .15, "Permanent Fix": .10},
    "Software Defect": {"Permanent Fix": .45, "Workaround": .40, "Vendor Fix": .15},
    "Hardware Failure": {"Hardware Replacement": .80, "Workaround": .20},
    "Third-Party / Vendor": {"Vendor Fix": .70, "Workaround": .30},
    "Change-Related": {"Change Rollback": .50, "Configuration Change": .35, "Permanent Fix": .15},
    "Capacity / Performance": {"Configuration Change": .45, "Permanent Fix": .35, "Workaround": .20},
    "Known Error": {"Workaround": .75, "Permanent Fix": .25},
    "Security Threat": {"Threat Contained": .80, "User Education": .20},
    "Network Connectivity": {"Configuration Change": .40, "Vendor Fix": .35, "Workaround": .25},
    "Undetermined": {"No Fault Found": .60, "Workaround": .40},
    "Service Request": {"Request Fulfilled": 1.0},
}

# Chronic issues for "problem customers" (recurring incidents)
CHRONIC_SUBCATS = ["SC17", "SC31", "SC24", "SC05", "SC13", "SC29", "SC18", "SC16"]

REGIONS = {"London": .22, "South East": .16, "Midlands": .14, "North West": .14,
           "Yorkshire & North East": .11, "South West": .08, "Scotland": .09, "Wales": .06}
INDUSTRIES = {"Financial Services": .16, "Healthcare": .11, "Retail": .12,
              "Manufacturing": .11, "Public Sector": .10, "Education": .08,
              "Professional Services": .12, "Logistics": .08, "Energy & Utilities": .05,
              "Technology": .07}
COMPANY_SIZES = ["SME", "Mid-Market", "Enterprise", "Large Enterprise"]

FIRST_NAMES = ["Oliver", "Amelia", "Harry", "Isla", "Jack", "Ava", "George", "Mia",
               "Noah", "Freya", "Leo", "Grace", "Arthur", "Lily", "Muhammad", "Sophie",
               "Oscar", "Evie", "Charlie", "Poppy", "Jacob", "Ella", "Thomas", "Chloe",
               "Ethan", "Priya", "Aarav", "Zara", "Daniel", "Hannah", "Callum", "Niamh",
               "Rhys", "Ffion", "Kofi", "Amara", "Liam", "Aisha", "Samuel", "Megan",
               "Ryan", "Rosie", "Adam", "Holly", "Joshua", "Erin", "Lewis", "Imogen",
               "Ravi", "Leah", "Tomasz", "Ewa", "Marcus", "Jade", "Owen", "Kirsty",
               "Fraser", "Eilidh", "Hamza", "Yasmin"]
LAST_NAMES = ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson",
              "Davies", "Patel", "Robinson", "Wright", "Thompson", "Evans", "Walker",
              "White", "Roberts", "Green", "Hall", "Wood", "Jackson", "Clarke", "Khan",
              "Hughes", "Edwards", "Turner", "Lewis", "Morris", "Campbell", "Murray",
              "Kaur", "Singh", "Ali", "Okafor", "Mensah", "Kowalski", "Nowak", "Reid",
              "Fraser", "Price", "Bennett", "Shaw", "Ahmed", "Hussain", "Begum", "Mitchell",
              "Carter", "Phillips", "Parker", "Morgan", "Bell", "Cooper", "Ward", "Cox",
              "Richardson", "Watson", "Gray", "Marshall", "Owen", "Lloyd", "Stewart"]
NAME_PREFIX = ["Ashford", "Brightwater", "Calder", "Dunmore", "Elmstead", "Fairhaven",
               "Greystone", "Hartwell", "Ironbridge", "Juniper", "Kingsmere", "Larkfield",
               "Marlow", "Northgate", "Oakridge", "Pennine", "Quayside", "Redbrook",
               "Severn", "Thornbury", "Ullswater", "Vale", "Westcliff", "Yarrow",
               "Albion", "Beacon", "Clifton", "Dalton", "Eden", "Foxley", "Glenmore",
               "Holloway", "Kestrel", "Linden", "Medway", "Newbury", "Orchard", "Pembroke",
               "Ribble", "Stanmore", "Tamar", "Wexford", "Abbey", "Bramley", "Cotswold",
               "Derwent", "Exmoor", "Falcon", "Granite", "Heron", "Lomond", "Moorland",
               "Nevis", "Osprey", "Portland", "Riverside", "Sterling", "Tyne", "Windsor",
               "Avon"]
NAME_SUFFIX = {
    "Financial Services": ["Capital", "Financial", "Wealth", "Insurance", "Bank", "Partners"],
    "Healthcare": ["Health", "Medical", "Care Group", "Clinics", "Pharma"],
    "Retail": ["Retail", "Stores", "Brands", "Outlets", "Home"],
    "Manufacturing": ["Engineering", "Manufacturing", "Industries", "Components", "Plastics"],
    "Public Sector": ["Council", "Housing Trust", "Authority", "Services"],
    "Education": ["Academy Trust", "College", "Learning", "Schools Trust"],
    "Professional Services": ["Consulting", "Legal", "Accountants", "Advisory", "Associates"],
    "Logistics": ["Logistics", "Freight", "Distribution", "Transport"],
    "Energy & Utilities": ["Energy", "Power", "Water", "Renewables"],
    "Technology": ["Software", "Digital", "Systems", "Technologies", "Labs"],
}
LEGAL_FORM = {"Public Sector": [""], "Education": [""]}


def _choice(rng, options: dict, size=None):
    keys = list(options.keys())
    p = np.array(list(options.values()), dtype=float)
    return rng.choice(keys, size=size, p=p / p.sum())


# ---------------------------------------------------------------------------
# Dimension tables
# ---------------------------------------------------------------------------
def build_calendar() -> pd.DataFrame:
    d = pd.date_range(START, END, freq="D")
    cal = pd.DataFrame({"date": d})
    cal["date_key"] = cal["date"].dt.strftime("%Y%m%d").astype(int)
    cal["year"] = cal["date"].dt.year
    cal["quarter"] = cal["date"].dt.quarter
    cal["month"] = cal["date"].dt.month
    cal["month_name"] = cal["date"].dt.strftime("%B")
    cal["year_month"] = cal["date"].dt.strftime("%Y-%m")
    iso = cal["date"].dt.isocalendar()
    cal["iso_year"] = iso["year"].astype(int)
    cal["iso_week"] = iso["week"].astype(int)
    cal["day_of_month"] = cal["date"].dt.day
    cal["day_of_week"] = cal["date"].dt.dayofweek + 1  # 1 = Monday (ISO)
    cal["day_name"] = cal["date"].dt.strftime("%A")
    cal["is_weekend"] = cal["day_of_week"] >= 6
    ds = cal["date"].dt.strftime("%Y-%m-%d")
    cal["is_uk_bank_holiday"] = ds.isin(UK_BANK_HOLIDAYS.keys())
    cal["holiday_name"] = ds.map(UK_BANK_HOLIDAYS)
    cal["is_working_day"] = ~cal["is_weekend"] & ~cal["is_uk_bank_holiday"]
    fy_start = np.where(cal["month"] >= 4, cal["year"], cal["year"] - 1)
    cal["fiscal_year"] = [f"FY{y}/{(y + 1) % 100:02d}" for y in fy_start]
    cal["fiscal_quarter"] = ((cal["month"] - 4) % 12) // 3 + 1
    cal["date"] = cal["date"].dt.strftime("%Y-%m-%d")
    return cal[["date_key", "date", "year", "quarter", "month", "month_name", "year_month",
                "iso_year", "iso_week", "day_of_month", "day_of_week", "day_name",
                "is_weekend", "is_uk_bank_holiday", "holiday_name", "is_working_day",
                "fiscal_year", "fiscal_quarter"]]


def build_sla_targets() -> pd.DataFrame:
    # (response_hours, resolution_hours) per priority
    rules = {
        "Platinum": [(0.25, 4), (0.5, 8), (2, 24), (8, 72)],
        "Gold": [(0.5, 4), (1, 12), (4, 36), (12, 96)],
        "Silver": [(1, 8), (2, 24), (8, 72), (24, 120)],
        "Bronze": [(2, 12), (4, 36), (12, 96), (48, 168)],
    }
    rows, i = [], 1
    for level, targets in rules.items():
        for prio, (resp, res) in zip(PRIORITIES, targets):
            rows.append({"sla_rule_id": f"SLA{i:02d}", "sla_level": level, "priority": prio,
                         "response_target_hours": resp, "resolution_target_hours": res,
                         "clock_basis": "Elapsed calendar hours",
                         "effective_from": "2023-01-01", "effective_to": None})
            i += 1
    return pd.DataFrame(rows)


def build_categories() -> pd.DataFrame:
    df = pd.DataFrame(CATEGORIES, columns=["subcategory_id", "category", "subcategory",
                                           "default_team_id", "complexity_tier",
                                           "is_service_request", "_w", "_mon"])
    cat_ids = {c: f"CAT{i + 1:02d}" for i, c in enumerate(df["category"].unique())}
    df.insert(1, "category_id", df["category"].map(cat_ids))
    return df


def build_teams() -> pd.DataFrame:
    return pd.DataFrame(TEAMS, columns=["team_id", "team_name", "support_tier",
                                        "primary_location", "operating_model",
                                        "planned_headcount"])


def unique_names(rng, n):
    seen, out = set(), []
    while len(out) < n:
        nm = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if nm not in seen:
            seen.add(nm)
            out.append(nm)
    return out


def build_agents(rng, teams: pd.DataFrame) -> pd.DataFrame:
    rows, names = [], unique_names(rng, 80)
    k = 0
    locations = ["Manchester Hub", "London HQ", "Bristol Office", "Glasgow Hub"]
    for t in teams.itertuples():
        for j in range(t.planned_headcount):
            if j == 0:
                exp = "Lead"
            else:
                exp = rng.choice(["Junior", "Intermediate", "Senior"], p=[.36, .42, .22])
            # Network Ops and EUC carry more juniors (hiring backfill) -> synthetic pattern
            if t.team_id in ("T03", "T02") and exp == "Intermediate" and rng.random() < .35:
                exp = "Junior"
            if t.team_id in TWENTY_FOUR_SEVEN:
                shift = rng.choice(["Early", "Day", "Late", "Night"], p=[.22, .40, .22, .16])
            else:
                shift = rng.choice(["Early", "Day", "Late"], p=[.22, .58, .20])
            if exp == "Lead":
                shift = "Day"
            loc_r = rng.random()
            location = (t.primary_location if loc_r < .68 else
                        "Remote (UK)" if loc_r < .93 else rng.choice(locations))
            emp = rng.choice(["Permanent", "Contractor", "Outsourced Partner"],
                             p=[.78, .12, .10])
            if exp == "Lead":
                emp = "Permanent"
            years = {"Junior": (0.3, 2), "Intermediate": (2, 5), "Senior": (5, 12),
                     "Lead": (6, 14)}[exp]
            start = START - pd.Timedelta(days=int(rng.uniform(*years) * 365))
            rows.append({"agent_id": f"AGT-{k + 1:03d}", "agent_name": names[k],
                         "team_id": t.team_id, "experience_level": exp, "shift": shift,
                         "location": location, "employment_type": emp,
                         "start_date": start.strftime("%Y-%m-%d")})
            k += 1
    return pd.DataFrame(rows)


def build_customers(rng, n=500) -> pd.DataFrame:
    industry = _choice(rng, INDUSTRIES, n)
    size = rng.choice(COMPANY_SIZES, n, p=[.34, .32, .24, .10])
    region = _choice(rng, REGIONS, n)
    contract = rng.choice(["Fully Managed", "Co-Managed", "Ad-hoc Support"], n,
                          p=[.50, .35, .15])
    sla_by_size = {"SME": [.03, .17, .45, .35], "Mid-Market": [.08, .32, .42, .18],
                   "Enterprise": [.22, .45, .28, .05], "Large Enterprise": [.45, .40, .15, 0]}
    sla = np.array([rng.choice(["Platinum", "Gold", "Silver", "Bronze"], p=sla_by_size[s])
                    for s in size])
    # 84% existing before 2024, 16% onboarded during the dataset period
    since = []
    for _ in range(n):
        if rng.random() < .84:
            since.append(pd.Timestamp("2012-01-01") +
                         pd.Timedelta(days=int(rng.uniform(0, (START - pd.Timestamp("2012-01-01")).days))))
        else:
            since.append(START + pd.Timedelta(days=int(rng.uniform(0, 640))))
    names, used = [], set()
    for ind in industry:
        while True:
            suffix = rng.choice(NAME_SUFFIX[ind])
            form = "" if ind in ("Public Sector", "Education") else rng.choice(
                [" Ltd", " Ltd", " plc", " Group", " LLP" if ind == "Professional Services" else " Ltd"])
            nm = f"{rng.choice(NAME_PREFIX)} {suffix}{form}"
            if nm not in used:
                used.add(nm)
                names.append(nm)
                break
    csms = ["Hannah Lloyd", "Kofi Mensah", "Isla Murray", "Daniel Price", "Priya Kaur",
            "Owen Bell"]
    df = pd.DataFrame({
        "customer_id": [f"CUST-{i + 1:04d}" for i in range(n)],
        "customer_name": names, "industry": industry, "company_size": size,
        "region": region, "contract_type": contract, "sla_level": sla,
        "customer_since": [d.strftime("%Y-%m-%d") for d in since],
        "customer_success_manager": rng.choice(csms, n),
    })
    return df


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------
def next_business_open(ts: pd.Timestamp) -> pd.Timestamp:
    """Next 08:00 on a working day (Mon-Fri, not bank holiday)."""
    d = ts.normalize()
    if ts.hour < 8 and d.dayofweek < 5 and d.strftime("%Y-%m-%d") not in UK_BANK_HOLIDAYS:
        return d + pd.Timedelta(hours=8)
    d = d + pd.Timedelta(days=1)
    while d.dayofweek >= 5 or d.strftime("%Y-%m-%d") in UK_BANK_HOLIDAYS:
        d += pd.Timedelta(days=1)
    return d + pd.Timedelta(hours=8)


def is_out_of_hours(ts: pd.Timestamp) -> bool:
    return (ts.dayofweek >= 5 or ts.hour < 8 or ts.hour >= 18
            or ts.strftime("%Y-%m-%d") in UK_BANK_HOLIDAYS)


SHIFT_HOURS = {"Early": range(6, 14), "Day": range(8, 17), "Late": range(14, 22),
               "Night": list(range(22, 24)) + list(range(0, 6))}


def generate_tickets(rng, customers, agents, teams, cats, sla, cal):
    dates = pd.to_datetime(cal["date"])
    t_frac = ((dates - START).dt.days / (END - START).days).to_numpy()
    dow_f = np.array([1.20, 1.12, 1.06, 1.00, 0.90, 0.28, 0.22])[dates.dt.dayofweek]
    hol_f = np.where(cal["is_uk_bank_holiday"], 0.30, 1.0)
    month_f = dates.dt.month.map({1: 1.06, 2: 1.02, 3: 1.03, 4: .98, 5: 1.0, 6: 1.0,
                                  7: .97, 8: .90, 9: 1.04, 10: 1.03, 11: 1.02,
                                  12: .86}).to_numpy()
    lam = (1 + 0.38 * t_frac) * dow_f * hol_f * month_f
    lam = lam * TARGET_BASE_TICKETS / lam.sum()
    daily_n = rng.poisson(lam)

    hour_wd = np.array([.4, .3, .25, .25, .3, .5, 1.2, 2.8, 6.0, 9.0, 9.5, 8.5, 6.5,
                        7.5, 8.5, 8.0, 7.0, 5.0, 2.8, 1.8, 1.4, 1.1, .8, .6])
    hour_we = np.array([.8] * 7 + [1.5] * 12 + [.9] * 5)

    # customer propensity
    size_w = customers["company_size"].map({"SME": .5, "Mid-Market": 1.0, "Enterprise": 2.0,
                                            "Large Enterprise": 3.4}).to_numpy()
    cust_w = size_w * rng.lognormal(0, .5, len(customers))
    chronic_idx = rng.choice(len(customers), 30, replace=False)
    chronic_sub = np.full(len(customers), None, dtype=object)
    chronic_sub[chronic_idx] = rng.choice(CHRONIC_SUBCATS, 30)
    cust_w[chronic_idx] *= 1.8
    since = pd.to_datetime(customers["customer_since"]).to_numpy()

    sub_w = cats["_w"].to_numpy() / cats["_w"].sum()

    rec_created, rec_cust = [], []
    for di, n in enumerate(daily_n):
        if n == 0:
            continue
        day = dates.iloc[di]
        elig = since <= day.to_datetime64()
        w = np.where(elig, cust_w, 0)
        cidx = rng.choice(len(customers), n, p=w / w.sum())
        prof = hour_we if (day.dayofweek >= 5 or cal["is_uk_bank_holiday"].iloc[di]) else hour_wd
        hrs = rng.choice(24, n, p=prof / prof.sum())
        secs = rng.integers(0, 3600, n)
        rec_created.extend(day + pd.to_timedelta(hrs * 3600 + secs, unit="s"))
        rec_cust.extend(cidx)

    df = pd.DataFrame({"created_at": rec_created, "cidx": rec_cust})
    n = len(df)
    sub_idx = rng.choice(len(cats), n, p=sub_w)
    # chronic override: recurring issue for problem customers
    is_chronic_cust = pd.notna(chronic_sub[df["cidx"].to_numpy()])
    chronic_hit = is_chronic_cust & (rng.random(n) < .40)
    sub_lookup = {s: i for i, s in enumerate(cats["subcategory_id"])}
    sub_idx = np.where(chronic_hit,
                       [sub_lookup.get(chronic_sub[c], 0) for c in df["cidx"]], sub_idx)
    df["sub_idx"] = sub_idx
    df["chronic_hit"] = chronic_hit

    # Major incident spikes (fictional)
    spikes = [("2025-03-11 07:40:00", "SC17", 85, "Third-Party / Vendor"),
              ("2025-09-23 10:15:00", "SC26", 70, "Third-Party / Vendor"),
              ("2024-10-08 09:05:00", "SC31", 45, "Change-Related")]
    spike_rows = []
    for ts, sc, k, rc in spikes:
        base = pd.Timestamp(ts)
        sw = np.where(since <= base.normalize().to_datetime64(), cust_w, 0)
        cidx = rng.choice(len(customers), k, p=sw / sw.sum())
        off = np.sort(rng.exponential(2.5 * 3600, k)).astype(int)
        for c, o in zip(cidx, off):
            spike_rows.append({"created_at": base + pd.Timedelta(seconds=int(o)), "cidx": c,
                               "sub_idx": sub_lookup[sc], "chronic_hit": False,
                               "spike_root": rc})
    df = pd.concat([df, pd.DataFrame(spike_rows)], ignore_index=True)
    df = df.sort_values("created_at", kind="stable").reset_index(drop=True)
    n = len(df)

    c = cats.iloc[df["sub_idx"]].reset_index(drop=True)
    cu = customers.iloc[df["cidx"]].reset_index(drop=True)
    df["customer_id"] = cu["customer_id"]
    df["sla_level"] = cu["sla_level"]
    df["category"] = c["category"]
    df["subcategory"] = c["subcategory"]
    df["subcategory_id"] = c["subcategory_id"]
    df["team_id"] = c["default_team_id"]
    df["complexity"] = c["complexity_tier"]
    df["is_sr"] = c["is_service_request"].to_numpy()
    df["mon_ok"] = c["_mon"].to_numpy()
    tf = ((df["created_at"] - START).dt.total_seconds() /
          (END - START).total_seconds()).clip(0, 1).to_numpy()

    # region: HQ region, 8% from another site
    other = _choice(rng, REGIONS, n)
    df["region"] = np.where(rng.random(n) < .08, other, cu["region"])

    # priority
    pmat = {"Low": [.01, .07, .47, .45], "Medium": [.04, .17, .54, .25],
            "High": [.10, .27, .48, .15], "SR": [0, .03, .42, .55]}
    key = np.where(df["is_sr"], "SR", df["complexity"])
    pr = np.empty(n, dtype=object)
    for k_, p in pmat.items():
        m = key == k_
        pr[m] = rng.choice(PRIORITIES, m.sum(), p=p)
    spike_m = df["spike_root"].notna().to_numpy() if "spike_root" in df else np.zeros(n, bool)
    pr[spike_m] = rng.choice(["P1", "P2", "P3"], spike_m.sum(), p=[.25, .55, .20])
    df["priority"] = pr
    p_idx = pd.Series(pr).map({"P1": 0, "P2": 1, "P3": 2, "P4": 3}).to_numpy()

    # channel
    ch = rng.choice(["Portal", "Email", "Phone", "Chat"], n, p=[.38, .25, .22, .15])
    mon = df["mon_ok"].to_numpy() & (rng.random(n) < .42)
    ch = np.where(mon, "Monitoring Alert", ch)
    p1_phone = (p_idx == 0) & ~mon & (rng.random(n) < .5)
    ch = np.where(p1_phone, "Phone", ch)
    df["channel"] = ch

    # team-month workload index
    df["ym"] = df["created_at"].dt.strftime("%Y-%m")
    hc = teams.set_index("team_id")["planned_headcount"]
    tm = df.groupby(["team_id", "ym"]).size().rename("n").reset_index()
    tm["per_agent"] = tm["n"] / tm["team_id"].map(hc)
    tm["load_index"] = (tm["per_agent"] / tm["per_agent"].median()).clip(.5, 2.2)
    df = df.merge(tm[["team_id", "ym", "load_index"]], on=["team_id", "ym"], how="left")
    load = df["load_index"].to_numpy()

    # agent assignment (experience preference + shift coverage)
    ag = agents.copy()
    exp_w_hi = {"Lead": 2.0, "Senior": 3.0, "Intermediate": 1.5, "Junior": .5}
    exp_w_lo = {"Lead": .3, "Senior": .8, "Intermediate": 1.2, "Junior": 1.5}
    team_agents = {t: g for t, g in ag.groupby("team_id")}
    hours = df["created_at"].dt.hour.to_numpy()
    agent_ids = np.empty(n, dtype=object)
    for i in range(n):
        g = team_agents[df.at[i, "team_id"]]
        ew = (exp_w_hi if p_idx[i] <= 1 else exp_w_lo)
        w = g["experience_level"].map(ew).to_numpy()
        cover = np.array([hours[i] in SHIFT_HOURS[s] for s in g["shift"]])
        w = w * np.where(cover, 4.0, 1.0)
        agent_ids[i] = rng.choice(g["agent_id"].to_numpy(), p=w / w.sum())
    df["agent_id"] = agent_ids
    ai = ag.set_index("agent_id").loc[df["agent_id"]]
    exp = ai["experience_level"].to_numpy()
    emp = ai["employment_type"].to_numpy()

    # knowledge base usage
    kb_p = np.where(df["team_id"] == "T01", .55, .30)
    kb_p += np.select([df["complexity"] == "Low", df["complexity"] == "High"], [.15, -.10], 0)
    kb_p += .08 * tf  # KB adoption rising slowly
    kb = rng.random(n) < kb_p
    df["knowledge_base_used"] = kb

    # escalation
    esc_p = np.array([.45, .30, .12, .05])[p_idx]
    esc_p += np.where(df["complexity"] == "High", .12, 0)
    esc_p += np.where(exp == "Junior", .08, 0)
    esc_p += np.where(df["team_id"] == "T01", .10, 0)
    esc_p += np.where(emp == "Outsourced Partner", .06, 0)
    esc_p -= np.where(kb, .05, 0)
    esc_p += .10 * (load - 1).clip(0, None)
    esc = rng.random(n) < esc_p.clip(.01, .9)
    df["escalation_flag"] = esc

    # root cause (latent; affects work time)
    rc = np.empty(n, dtype=object)
    for cat, wts in ROOT_CAUSES_BY_CATEGORY.items():
        m = (df["category"] == cat).to_numpy()
        if not m.any():
            continue
        keys = list(wts)
        base = np.array([wts[k_] for k_ in keys])
        cr = keys.index("Change-Related") if "Change-Related" in keys else None
        idxs = np.where(m)[0]
        # Change-Related share grows over time (synthetic: weak change control)
        for i in idxs:
            p = base.copy()
            if cr is not None:
                p[cr] *= (1 + 1.6 * tf[i])
            rc[i] = keys[rng.choice(len(keys), p=p / p.sum())]
    ch_m = df["chronic_hit"].to_numpy().astype(bool)
    r = rng.random(n)
    rc = np.where(ch_m & (r < .45), "Known Error",
                  np.where(ch_m & (r < .80), "Configuration Error", rc))
    if "spike_root" in df:
        rc = np.where(spike_m, df["spike_root"].fillna("").to_numpy(), rc)
    rc = np.where(df["is_sr"], "Service Request", rc)
    df["root_cause"] = rc

    # first-contact resolution
    fcr_elig = (~esc & df["channel"].isin(["Phone", "Chat", "Portal", "Email"]).to_numpy()
                & (df["complexity"] != "High").to_numpy())
    fcr_p = .12 + np.where(df["complexity"] == "Low", .30, 0) + np.where(kb, .22, 0)
    fcr_p += np.where(df["team_id"] == "T01", .12, 0)
    fcr_p += np.where(df["channel"].isin(["Phone", "Chat"]), .10, 0)
    fcr_p += np.select([exp == "Junior", exp == "Senior"], [-.08, .05], 0)
    fcr_p -= .08 * (load - 1).clip(0, None)
    fcr = fcr_elig & (rng.random(n) < fcr_p.clip(0, .95))
    df["first_contact_resolution"] = fcr

    # resolution type
    res_type = np.empty(n, dtype=object)
    for root, opts in RESOLUTION_TYPES_BY_ROOT.items():
        m = rc == root
        if m.any():
            res_type[m] = _choice(rng, opts, m.sum())
    df["resolution_type"] = res_type

    # timing ---------------------------------------------------------------
    created = df["created_at"]
    ooh = np.array([is_out_of_hours(t) for t in created])
    bh_team = ~df["team_id"].isin(TWENTY_FOUR_SEVEN).to_numpy()
    wait = np.zeros(n)
    wait_m = ooh & bh_team & (p_idx >= 2)
    for i in np.where(wait_m)[0]:
        wait[i] = (next_business_open(created.iloc[i]) - created.iloc[i]).total_seconds() / 3600

    fr_base = np.array([.15, .45, 2.0, 5.5])[p_idx]
    ch_mult = pd.Series(df["channel"]).map({"Phone": .25, "Chat": .35, "Monitoring Alert": .6,
                                            "Portal": 1.0, "Email": 1.25}).to_numpy()
    frt = fr_base * load ** .8 * ch_mult * rng.lognormal(0, .7, n) + wait
    frt = np.maximum(frt, 1 / 60)

    base_res = np.array([0.9, 3.4, 10.5, 24.0])[p_idx]
    cx = pd.Series(df["complexity"]).map({"Low": .6, "Medium": 1.0, "High": 1.55}).to_numpy()
    em = pd.Series(exp).map({"Junior": 1.25, "Intermediate": 1.0, "Senior": .85,
                             "Lead": .8}).to_numpy()
    et = pd.Series(emp).map({"Permanent": 1.0, "Contractor": 1.05,
                             "Outsourced Partner": 1.18}).to_numpy()
    rcm = pd.Series(rc).map(ROOT_CAUSE_TIME_MULT).to_numpy()
    work = (base_res * cx * em * et * rcm * load ** 1.15
            * np.where(esc, 1.75, 1.0) * np.where(kb, .8, 1.0)
            * rng.lognormal(0, .62, n))
    work = np.where(esc, work + rng.uniform(1, 6, n), work)
    fcr_work = rng.uniform(.08, 1.2, n) * np.where(df["complexity"] == "Low", 1.0, 1.5)
    work = np.where(fcr, fcr_work, work)

    # reopen
    rlam = (.05 + np.where(res_type == "Workaround", .14, 0) + np.where(exp == "Junior", .05, 0)
            + np.where(rc == "Known Error", .08, 0) + np.where(res_type == "No Fault Found", .10, 0))
    reopen = np.where(fcr, 0, rng.poisson(rlam))
    work = work + np.array([rng.lognormal(np.log(14), .8, k).sum() if k else 0 for k in reopen])
    df["reopened_count"] = reopen

    res_hours = frt + work
    df["first_response_at"] = created + pd.to_timedelta(frt * 3600, unit="s")
    df["resolved_at"] = created + pd.to_timedelta(res_hours * 3600, unit="s")

    # SLA target lookup
    sla_map = sla.set_index(["sla_level", "priority"])["resolution_target_hours"]
    df["sla_target_hours"] = [sla_map[(l, p)] for l, p in zip(df["sla_level"], df["priority"])]
    breached = res_hours > df["sla_target_hours"].to_numpy()

    # business impact
    bi_opts = {"P1": {"Critical": .70, "High": .30}, "P2": {"High": .65, "Medium": .35},
               "P3": {"Medium": .70, "Low": .25, "High": .05}, "P4": {"Low": .85, "Medium": .15}}
    bi = np.empty(n, dtype=object)
    for p, o in bi_opts.items():
        m = pr == p
        bi[m] = _choice(rng, o, m.sum())
    df["business_impact"] = bi

    # status at snapshot
    status = np.full(n, "Closed", dtype=object)
    open_m = df["resolved_at"] > SNAPSHOT
    recent = df["resolved_at"] > (SNAPSHOT - pd.Timedelta(days=3))
    status = np.where(recent, "Resolved", status)
    cancel = (rng.random(n) < .012) & ~open_m.to_numpy()
    status = np.where(cancel, "Cancelled", status)
    fr_pending = df["first_response_at"] > SNAPSHOT
    open_status = rng.choice(["In Progress", "Pending Customer", "On Hold"], n, p=[.6, .28, .12])
    # open backlog: a share of recent tickets is still waiting on customer / vendor
    age_days = (SNAPSHOT - created).dt.total_seconds().to_numpy() / 86400
    stuck = (age_days < 60) & (rng.random(n) < .35 * np.exp(-age_days / 12) + .05) & ~cancel
    open_m = open_m.to_numpy() | stuck
    open_m = pd.Series(open_m)
    status = np.where(open_m, np.where(fr_pending, "New", open_status), status)
    df["ticket_status"] = status

    # CSAT (survey on resolved/closed tickets)
    resolved_like = np.isin(status, ["Resolved", "Closed"])
    cust_effect = rng.normal(0, .3, len(customers))[df["cidx"].to_numpy()]
    latent = (4.45 - 1.10 * breached - .45 * reopen - .30 * esc + .25 * fcr
              - .25 * np.log1p(res_hours / 24) + cust_effect + rng.normal(0, .6, n))
    csat = np.clip(np.round(latent), 1, 5)
    respond = rng.random(n) < (.40 + .10 * breached + .05 * (reopen > 0))
    csat = np.where(resolved_like & respond, csat, np.nan)
    df["customer_satisfaction"] = csat

    # clear fields not yet known for open / cancelled tickets
    for col in ["first_contact_resolution", "knowledge_base_used", "escalation_flag"]:
        df[col] = df[col].astype(object)
    df["sla_target_hours"] = df["sla_target_hours"].astype(object)
    df.loc[open_m, ["resolved_at", "root_cause", "resolution_type"]] = None
    df.loc[open_m, "first_contact_resolution"] = None
    df.loc[fr_pending, "first_response_at"] = None
    df.loc[cancel, ["root_cause"]] = None
    df.loc[cancel, "resolution_type"] = "Cancelled"
    df.loc[cancel, "first_contact_resolution"] = False

    out = df[["customer_id", "agent_id", "team_id", "created_at", "first_response_at",
              "resolved_at", "priority", "category", "subcategory", "channel",
              "ticket_status", "sla_target_hours", "escalation_flag", "reopened_count",
              "first_contact_resolution", "customer_satisfaction", "root_cause",
              "resolution_type", "business_impact", "knowledge_base_used", "region"]].copy()
    for col in ["created_at", "first_response_at", "resolved_at"]:
        out[col] = pd.to_datetime(out[col]).dt.floor("s")
    out.insert(0, "ticket_id", [f"TKT-{i + 1:06d}" for i in range(len(out))])
    return out


# ---------------------------------------------------------------------------
# Controlled data-quality issues
# ---------------------------------------------------------------------------
def inject_dq(rng, t: pd.DataFrame, customers: pd.DataFrame, agents: pd.DataFrame):
    log = []
    n = len(t)

    def pick(k, mask=None):
        pool = np.arange(n) if mask is None else np.where(mask)[0]
        return rng.choice(pool, min(k, len(pool)), replace=False)

    def note(i, issue, col, old, new):
        log.append({"ticket_id": t.at[i, "ticket_id"], "issue_type": issue, "column": col,
                    "original_value": None if pd.isna(old) else str(old),
                    "injected_value": None if pd.isna(new) else str(new)})

    closed = t["ticket_status"].isin(["Closed", "Resolved"]).to_numpy()

    # 1. inconsistent category labels (~2.5%)
    variants = {"Network": ["network", "NETWORK", "Network ", "Netwrk"],
                "Access & Identity": ["Access and Identity", "access & identity", "Access/Identity"],
                "Hardware": ["H/W", "hardware", "Hardware "],
                "Email & Collaboration": ["Email and Collaboration", "E-mail & Collaboration"],
                "Software": ["software", "SW"],
                "Infrastructure": ["Infra", "infrastructure"],
                "Cloud Services": ["Cloud", "cloud services"],
                "Business Applications": ["Business Apps", "business applications"],
                "Security": ["security", "Cyber Security"],
                "Database": ["DB", "database"]}
    for i in pick(int(n * .025)):
        old = t.at[i, "category"]
        new = rng.choice(variants[old])
        t.at[i, "category"] = new
        note(i, "inconsistent_category_label", "category", old, new)
    # region casing / whitespace (~0.4%)
    for i in pick(int(n * .004)):
        old = t.at[i, "region"]
        new = rng.choice([old.lower(), old.upper(), f" {old}"])
        t.at[i, "region"] = new
        note(i, "inconsistent_region_label", "region", old, new)

    # 2. missing optional values
    for col, rate, mask in [("root_cause", .04, closed), ("knowledge_base_used", .03, None),
                            ("channel", .006, None), ("subcategory", .01, None),
                            ("sla_target_hours", .003, None)]:
        for i in pick(int(n * rate), mask):
            old = t.at[i, col]
            if pd.isna(old):
                continue
            t.at[i, col] = None
            note(i, "missing_optional_value", col, old, None)
    # unassigned agent on a few resolved tickets
    for i in pick(int(n * .004), closed):
        old = t.at[i, "agent_id"]
        t.at[i, "agent_id"] = None
        note(i, "missing_agent", "agent_id", old, None)

    # 3. resolution-time outliers (~0.35%): tickets left open by mistake
    for i in pick(int(n * .0035), closed):
        old = t.at[i, "resolved_at"]
        dur = old - t.at[i, "created_at"]
        new = t.at[i, "created_at"] + dur * float(rng.uniform(15, 45)) + pd.Timedelta(days=int(rng.integers(10, 60)))
        new = min(new, SNAPSHOT - pd.Timedelta(hours=1))
        if new <= old:
            continue
        t.at[i, "resolved_at"] = new.floor("s")
        note(i, "resolution_time_outlier", "resolved_at", old, t.at[i, "resolved_at"])

    # 4. invalid timestamps (~0.2%)
    idx = pick(int(n * .002), closed)
    for k, i in enumerate(idx):
        mode = k % 3
        if mode == 0:  # resolved before created (swapped fields)
            old = t.at[i, "resolved_at"]
            new = t.at[i, "created_at"] - (old - t.at[i, "created_at"])
            t.at[i, "resolved_at"] = new
            note(i, "invalid_timestamp_resolved_before_created", "resolved_at", old, new)
        elif mode == 1:  # first response before created (clock skew)
            old = t.at[i, "first_response_at"]
            new = t.at[i, "created_at"] - pd.Timedelta(minutes=int(rng.integers(30, 600)))
            t.at[i, "first_response_at"] = new
            note(i, "invalid_timestamp_response_before_created", "first_response_at", old, new)
        else:  # first response after resolution
            old = t.at[i, "first_response_at"]
            new = t.at[i, "resolved_at"] + pd.Timedelta(hours=int(rng.integers(1, 48)))
            t.at[i, "first_response_at"] = new
            note(i, "invalid_timestamp_response_after_resolved", "first_response_at", old, new)

    # 5. unusual satisfaction scores (~0.2%)
    has_csat = t["customer_satisfaction"].notna().to_numpy()
    for i in pick(int(n * .002), has_csat):
        old = t.at[i, "customer_satisfaction"]
        new = float(rng.choice([0, 6, 7, 8, 9, 10, -1]))
        t.at[i, "customer_satisfaction"] = new
        note(i, "invalid_satisfaction_score", "customer_satisfaction", old, new)

    # 6. records requiring investigation
    team_of = agents.set_index("agent_id")["team_id"]
    for i in pick(int(n * .005)):          # agent not in ticket's team
        old = t.at[i, "agent_id"]
        if pd.isna(old):
            continue
        cand = agents.loc[agents["team_id"] != t.at[i, "team_id"], "agent_id"].to_numpy()
        new = rng.choice(cand)
        t.at[i, "agent_id"] = new
        note(i, "agent_team_mismatch", "agent_id", old, new)
    fcr_true = (t["first_contact_resolution"] == True).to_numpy()  # noqa: E712
    for k, i in enumerate(pick(int(n * .003), fcr_true)):  # contradictory flags
        if k % 2 == 0:
            t.at[i, "escalation_flag"] = True
            note(i, "contradictory_fcr_escalated", "escalation_flag", False, True)
        else:
            t.at[i, "reopened_count"] = 1
            note(i, "contradictory_fcr_reopened", "reopened_count", 0, 1)
    p1 = (t["priority"] == "P1").to_numpy()
    for i in pick(12, p1):                  # P1 with Low business impact
        old = t.at[i, "business_impact"]
        t.at[i, "business_impact"] = "Low"
        note(i, "priority_impact_mismatch", "business_impact", old, "Low")
    for i in pick(10):                      # orphan customer ids
        old = t.at[i, "customer_id"]
        new = f"CUST-{int(rng.integers(9000, 9999)):04d}"
        t.at[i, "customer_id"] = new
        note(i, "orphan_customer_id", "customer_id", old, new)
    for i in pick(8, closed):               # resolved status without timestamp
        old = t.at[i, "resolved_at"]
        t.at[i, "resolved_at"] = pd.NaT
        note(i, "closed_without_resolved_at", "resolved_at", old, None)

    # 7. duplicate-looking tickets (~0.6%): same issue logged twice by customer
    dup_src = pick(int(n * .006))
    dups = []
    for i in dup_src:
        r = t.loc[i].copy()
        delta = pd.Timedelta(seconds=int(rng.integers(45, 900)))
        r["created_at"] = r["created_at"] + delta
        for col in ["first_response_at", "resolved_at"]:
            if pd.notna(r[col]):
                r[col] = r[col] + delta
        if rng.random() < .5:
            r["channel"] = rng.choice(["Email", "Portal", "Phone"])
        r["_dup_of"] = r["ticket_id"]
        dups.append(r)
    t = pd.concat([t, pd.DataFrame(dups)], ignore_index=True)
    t = t.sort_values("created_at", kind="stable").reset_index(drop=True)
    # re-key so near-duplicates get their own (adjacent) IDs; keep log consistent
    new_ids = [f"TKT-{i + 1:06d}" for i in range(len(t))]
    remap = dict(zip(t["ticket_id"].where(t["_dup_of"].isna()), new_ids))
    remap.pop(np.nan, None)
    for row in log:
        row["ticket_id"] = remap.get(row["ticket_id"], row["ticket_id"])
    for i in np.where(t["_dup_of"].notna())[0]:
        log.append({"ticket_id": new_ids[i], "issue_type": "near_duplicate_ticket",
                    "column": "*", "original_value": remap[t.at[i, "_dup_of"]],
                    "injected_value": None})
    t["ticket_id"] = new_ids
    t = t.drop(columns="_dup_of")

    # 8. exact duplicate rows from a double-loaded extract (25 rows)
    exact = t.iloc[rng.choice(len(t), 25, replace=False)]
    for tid in exact["ticket_id"]:
        log.append({"ticket_id": tid, "issue_type": "exact_duplicate_row", "column": "*",
                    "original_value": None, "injected_value": None})
    t = pd.concat([t, exact], ignore_index=True)

    # dimension DQ (small)
    for i in rng.choice(len(customers), 4, replace=False):
        customers.at[i, "industry"] = None
    for i in rng.choice(len(agents), 2, replace=False):
        agents.at[i, "shift"] = None
    return t, pd.DataFrame(log)


def finalise_ticket_columns(t: pd.DataFrame) -> pd.DataFrame:
    """Derive hour columns from the (possibly corrupted) timestamps, as a source system would."""
    for col in ["created_at", "first_response_at", "resolved_at"]:
        t[col] = pd.to_datetime(t[col])
    t["first_response_time_hours"] = ((t["first_response_at"] - t["created_at"])
                                      .dt.total_seconds() / 3600).round(2)
    t["resolution_time_hours"] = ((t["resolved_at"] - t["created_at"])
                                  .dt.total_seconds() / 3600).round(2)
    # map subcategory -> keep raw subcategory label column; add after category in order
    order = ["ticket_id", "customer_id", "agent_id", "team_id", "created_at",
             "first_response_at", "resolved_at", "priority", "category", "subcategory",
             "channel", "ticket_status", "sla_target_hours", "first_response_time_hours",
             "resolution_time_hours", "escalation_flag", "reopened_count",
             "first_contact_resolution", "customer_satisfaction", "root_cause",
             "resolution_type", "business_impact", "knowledge_base_used", "region"]
    t = t[order].copy()
    for col in ["created_at", "first_response_at", "resolved_at"]:
        t[col] = t[col].dt.strftime(TS_FMT)
    t["customer_satisfaction"] = t["customer_satisfaction"].astype("Int64")
    t["reopened_count"] = t["reopened_count"].astype("Int64")
    t["sla_target_hours"] = t["sla_target_hours"].astype("Int64")
    for col in ["escalation_flag", "first_contact_resolution", "knowledge_base_used"]:
        t[col] = t[col].map({True: "true", False: "false"})
    return t


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    raw, ref = args.out / "raw", args.out / "reference"
    raw.mkdir(parents=True, exist_ok=True)
    ref.mkdir(parents=True, exist_ok=True)

    cal = build_calendar()
    sla = build_sla_targets()
    cats = build_categories()
    teams = build_teams()
    agents = build_agents(rng, teams)
    customers = build_customers(rng)
    leads = agents[agents["experience_level"] == "Lead"].set_index("team_id")["agent_id"]
    teams["team_lead_agent_id"] = teams["team_id"].map(leads)

    tickets = generate_tickets(rng, customers, agents, teams, cats, sla, cal)
    tickets, dq_log = inject_dq(rng, tickets, customers, agents)
    tickets = finalise_ticket_columns(tickets)

    cats_out = cats.drop(columns=["_w", "_mon"])
    cats_out["is_service_request"] = cats_out["is_service_request"].map({True: "true", False: "false"})
    for c in ["is_weekend", "is_uk_bank_holiday", "is_working_day"]:
        cal[c] = cal[c].map({True: "true", False: "false"})

    files = {"tickets.csv": tickets, "customers.csv": customers, "agents.csv": agents,
             "support_teams.csv": teams, "sla_targets.csv": sla, "calendar.csv": cal,
             "incident_categories.csv": cats_out}
    manifest = {"seed": args.seed, "generator": "scripts/generate_dataset.py",
                "period_start": str(START.date()), "period_end": str(END.date()),
                "snapshot_at": SNAPSHOT.strftime(TS_FMT), "synthetic": True, "files": {}}
    for name, df in files.items():
        p = raw / name
        df.to_csv(p, index=False, lineterminator="\n")
        manifest["files"][name] = {"rows": len(df), "columns": len(df.columns), "sha256": sha256(p)}
    dq_log.to_csv(ref / "dq_injection_log.csv", index=False, lineterminator="\n")
    manifest["dq_injection_log_rows"] = len(dq_log)
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    for name, meta in manifest["files"].items():
        print(f"{name:26s} {meta['rows']:>7,d} rows  {meta['columns']:>2d} cols")
    print(f"dq_injection_log.csv       {len(dq_log):>7,d} rows")


if __name__ == "__main__":
    main()
