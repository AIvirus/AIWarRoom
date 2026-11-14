"""
Load the demo data used in class: one operating e-commerce company and one idea.

    python manage.py seed_kirana --email you@example.com
    python manage.py seed_kirana --email you@example.com --reset

The businesses go into that user's organization. If the user doesn't exist yet, it is
created with a random password that is printed ONCE in your terminal (local use only).
Every invented number is tagged "illustrative" so nobody mistakes it for real data, and
no AI call is made: seeding costs no Gemini quota.
"""

import secrets

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.access import organization_for
from accounts.models import User
from accounts.services import register_owner
from businesses.models import BusinessComponent, BusinessProfile
from businesses.services.assumptions import save_assumptions
from simulation_engine import catalog
from simulations.models import Scenario
from simulations.services.run_service import run_scenario

DEMO_NOTE = "Demo data for teaching. All figures are illustrative, not a real company."

KIRANA = {
    "name": "Kirana Express",
    "mode": "operating",
    "industry": "Online groceries",
    "website_url": "https://books.toscrape.com/",  # a public scraping sandbox, safe to scan
    "assumptions": {
        # key: (value, source)
        "daily_orders": ("2400", "illustrative"),
        "average_order_value": ("640", "illustrative"),
        "contribution_margin": ("22", "illustrative"),
        "hourly_capacity": ("180", "illustrative"),
        "primary_gateway_share": ("85", "illustrative"),
        "main_warehouse_share": ("80", "illustrative"),
        "logistics_partner_share": ("70", "illustrative"),
        "recapture_rate": ("30", "illustrative"),
        "cancel_rate_per_delay_hour": ("1.5", "illustrative"),
        "max_cancel_rate": ("35", "illustrative"),
    },
    # (key, name, kind, criticality, depends_on keys, fallback)
    "components": [
        ("razorpay", "Razorpay (primary gateway)", "payment", 5, [], "Cashfree account, not live"),
        ("storefront", "kiranaexpress.in", "storefront", 5, ["razorpay"], ""),
        ("bhiwandi", "Bhiwandi DC", "warehouse", 5, [], "Thane dark store, 20 % capacity"),
        ("delhivery", "Delhivery", "logistics", 4, ["bhiwandi"], "Shadowfax for metro pin codes"),
        ("growers", "Nashik growers", "supplier", 3, [], ""),
    ],
    "scenarios": [
        (
            "Razorpay down at evening peak",
            "payment_gateway_outage",
            {"outage_hours": "3", "start_hour": "19"},
        ),
        ("Bhiwandi flood, 6 h from 18:00", "warehouse_shutdown", {"outage_hours": "6"}),
        (
            "Delhivery pickups stop for a day",
            "logistics_failure",
            {"outage_hours": "24", "start_hour": "9", "backup_switch_hours": "4"},
        ),
    ],  # fmt: skip
}

TIFFIN = {
    "name": "Tiffin Box Co.",
    "mode": "idea",
    "industry": "Meal subscriptions",
    "website_url": "",
    "assumptions": {
        "price_per_order": ("180", "user"),
        "variable_cost_per_order": ("112", "illustrative"),
        "fixed_costs_monthly": ("260000", "user"),
        "marketing_spend_monthly": ("120000", "user"),
        "cost_per_visit": ("9", "illustrative"),
        "conversion_rate": ("2.2", "illustrative"),
        "orders_per_customer_monthly": ("9", "illustrative"),
        "monthly_retention": ("78", "illustrative"),
        "initial_investment": ("2500000", "user"),
        "expected_orders_monthly": ("6000", "user"),
    },
    "components": [],
    "scenarios": [("Pune launch, 24 months", "idea_cases", {})],
}


class Command(BaseCommand):
    help = "Create the Kirana Express (operating) and Tiffin Box Co. (idea) demo businesses."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Owner account (created if missing)")
        parser.add_argument("--reset", action="store_true", help="Delete and recreate the demos")

    @transaction.atomic
    def handle(self, *args, email, reset, **options):
        user = User.objects.filter(email=email.lower()).first()
        if user is None:
            password = secrets.token_urlsafe(12)
            user = register_owner(
                email=email, password=password, full_name="Demo operator", org_name="Demo Org"
            )
            self.stdout.write(self.style.WARNING(f"Created {email} with password: {password}"))
            self.stdout.write("  (shown once; change it after logging in if you keep the account)")
        organization = organization_for(user)

        for spec in (KIRANA, TIFFIN):
            existing = BusinessProfile.objects.filter(organization=organization, name=spec["name"])
            if existing.exists():
                if not reset:
                    self.stdout.write(f"{spec['name']}: already there (use --reset to rebuild)")
                    continue
                existing.delete()
            self._create(spec, organization, user)

    def _create(self, spec, organization, user):
        business = BusinessProfile.objects.create(
            organization=organization,
            created_by=user,
            name=spec["name"],
            mode=spec["mode"],
            industry=spec["industry"],
            website_url=spec["website_url"],
            description=DEMO_NOTE,
        )
        save_assumptions(business, spec["assumptions"])

        by_key = {}
        for key, name, kind, criticality, _, fallback in spec["components"]:
            by_key[key] = BusinessComponent.objects.create(
                business=business, key=key, name=name, kind=kind,
                criticality=criticality, fallback_note=fallback,
            )  # fmt: skip
        for key, *_, depends_on, _ in spec["components"]:
            by_key[key].depends_on.set([by_key[d] for d in depends_on])

        self.stdout.write(self.style.SUCCESS(f"{business.name} ({business.mode})"))
        for name, template_key, parameters in spec["scenarios"]:
            scenario = Scenario.objects.create(
                business=business,
                name=name,
                template_key=template_key,
                parameters=catalog.validate_parameters(template_key, parameters),
                created_by=user,
            )
            run = run_scenario(scenario, user)
            self.stdout.write(f"  ran \"{name}\": /runs/{run.pk}/")
