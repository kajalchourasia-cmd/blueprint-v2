"""Build a deterministic 70-record online-first idea library from reviewed templates.

These are synthetic planning priors, not observed market evidence. Runtime evidence
is stored separately in blueprint_evidence_events.csv.
"""

from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "blueprint_idea_master.csv"

IDEAS = {
    "ai_product": [
        "Plant Analyzer App", "AI Interview Practice Coach", "Contract Risk Explainer",
        "Study Notes Synthesizer", "Meal Photo Nutrition Guide", "Home Energy Audit Assistant",
        "Freelance Proposal Reviewer", "Accessible Document Checker", "Pet Symptom Journal",
        "Small Business Cashflow Copilot",
    ],
    "saas": [
        "Creator Sponsorship CRM", "Clinic Waitlist Manager", "Freelancer Scope Tracker",
        "Community Renewal Dashboard", "Restaurant Supplier Portal", "Micro Agency Capacity Planner",
        "Customer Interview Repository", "Rental Inspection Workflow", "Volunteer Shift Manager",
        "Course Cohort Operations Hub",
    ],
    "marketplace": [
        "Local Expert Office Hours", "Independent Tutor Marketplace", "Verified Repair Specialist Network",
        "Unused Studio Time Exchange", "Home Cook Preorder Marketplace", "Specialist Mentor Matching",
        "Accessible Travel Guide Marketplace", "Local Workshop Discovery", "Fractional Operator Network",
        "Community Equipment Rental",
    ],
    "creator": [
        "Research Brief Newsletter", "Career Transition Learning Club", "Founder Interview Library",
        "Local Food Discovery Guide", "Practical AI Course", "Independent Design Critique Membership",
        "Language Practice Community", "Sustainable Living Playbook", "Parent Activity Subscription",
        "Niche Industry Podcast Network",
    ],
    "service": [
        "Remote Operations Studio", "Customer Research Sprint Service", "No Code Prototype Studio",
        "Online Bookkeeping Service", "Technical Writing Subscription", "Remote Hiring Research Service",
        "Ecommerce Conversion Audit", "Digital Accessibility Audit", "Founder Sales Research Service",
        "Online Community Launch Service",
    ],
    "consumer_product": [
        "Personal Knowledge Companion", "Shared Household Planner", "Medication Routine Journal",
        "Mindful Spending App", "Remote Study Focus Room", "Digital Family Archive",
        "Neighborhood Skill Swap App", "Personal Carbon Diary", "Solo Travel Safety Companion",
        "Reading Habit Companion",
    ],
    "online_business": [
        "Specialty Template Store", "Remote Team Workshop Kits", "Digital Wedding Planning Studio",
        "Premium Notion System Shop", "Online Plant Care Membership", "Printable Learning Activity Store",
        "Independent Research Report Shop", "Virtual Event Production Studio", "B2B Data Cleanup Service",
        "Curated Remote Work Toolkit",
    ],
}


def main() -> None:
    with PATH.open(encoding="utf-8", newline="") as handle:
        source = list(csv.DictReader(handle))
        fields = list(source[0])
    digital = next(row for row in source if row["idea_type"] == "ai_product")
    rows = []
    index = 1
    for idea_type, titles in IDEAS.items():
        for title in titles:
            row = deepcopy(digital)
            row.update({
                "idea_id": f"IDEA-{index:03d}",
                "idea_title": title,
                "idea_description": f"Online-first concept for {title.lower()} that must earn behavioral and payment evidence before build investment",
                "idea_type": idea_type,
                "industry": "digital_services" if idea_type in {"service", "online_business"} else idea_type,
                "delivery_model": "online_service" if idea_type == "service" else "web_or_mobile",
                "geography": "Online / global",
                "user_segment": "Digitally active early adopters",
                "secondary_segment": "Small teams and independent professionals",
                "revenue_model": "subscription" if idea_type in {"ai_product", "saas", "creator", "consumer_product"} else "transaction",
                "validation_test": "48-hour landing page plus concierge delivery test",
                "next_action": "Recruit 10 target users with recent problem experience",
                "data_source": "Proofpath synthetic planning prior",
                "confidence_level": "low",
                "positive_signal_count": "0",
                "evidence_strength": "0",
                "launch_readiness": "0",
            })
            rows.append(row)
            index += 1
    with PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
