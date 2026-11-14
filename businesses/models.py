"""
The business being simulated.

BusinessProfile      - one business idea or operating company, owned by an organization.
FinancialAssumption  - one number the simulation uses, with its unit and where it came from.
BusinessComponent    - a part of the operation (payment gateway, warehouse, courier...) and
                       which other components it depends on.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import BaseModel
from common.querysets import OrgScopedQuerySet
from simulation_engine import catalog


class BusinessQuerySet(OrgScopedQuerySet):
    def active(self):
        return self.filter(archived_at__isnull=True)


class BusinessProfile(BaseModel):
    class Mode(models.TextChoices):
        IDEA = catalog.IDEA, "Idea (not launched)"
        OPERATING = catalog.OPERATING, "Operating company"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="businesses"
    )
    mode = models.CharField(max_length=10, choices=Mode.choices)
    name = models.CharField(max_length=120)
    industry = models.CharField(max_length=80, default="E-commerce")
    description = models.TextField(blank=True)
    website_url = models.URLField(blank=True)
    # One currency per business; the MVP supports INR only so amounts are never mixed.
    currency = models.CharField(max_length=3, default="INR", choices=[("INR", "Indian rupee")])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Archive instead of delete: past runs and decisions must stay readable.
    archived_at = models.DateTimeField(null=True, blank=True)

    ORG_PATH = "organization"
    objects = BusinessQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FinancialAssumption(BaseModel):
    class Source(models.TextChoices):
        USER = "user", "User input"
        ILLUSTRATIVE = "illustrative", "Illustrative"
        DERIVED = "derived", "Derived"
        FROM_SITE = "from_site", "From company site"

    business = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="assumptions"
    )
    key = models.CharField(max_length=60)
    # 16 digits with 4 decimals covers rupee amounts in crores and rates like 2.5 %.
    value = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(max_length=40, editable=False)
    source = models.CharField(max_length=15, choices=Source.choices, default=Source.USER)
    note = models.CharField(max_length=240, blank=True)

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["business", "key"], name="unique_assumption_key")
        ]

    def clean(self):
        try:
            self.value = catalog.parse_input(self.key, self.value)
        except catalog.CatalogError as error:
            raise ValidationError(error.errors) from None

    def save(self, *args, **kwargs):
        # The unit always comes from the catalogue, never from the client.
        spec = catalog.INPUTS.get(self.key)
        self.unit = spec.unit if spec else ""
        super().save(*args, **kwargs)

    @property
    def label(self):
        spec = catalog.INPUTS.get(self.key)
        return spec.label if spec else self.key

    def __str__(self):
        return f"{self.key} = {self.value} {self.unit}"


class BusinessComponent(BaseModel):
    class Kind(models.TextChoices):
        STOREFRONT = "storefront", "Storefront"
        PAYMENT = "payment", "Payment gateway"
        WAREHOUSE = "warehouse", "Warehouse"
        LOGISTICS = "logistics", "Logistics partner"
        SUPPLIER = "supplier", "Supplier"
        CUSTOMERS = "customers", "Customers"
        REVENUE = "revenue", "Revenue"

    business = models.ForeignKey(
        BusinessProfile, on_delete=models.CASCADE, related_name="components"
    )
    key = models.SlugField(max_length=40)
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    criticality = models.PositiveSmallIntegerField(
        default=3, help_text="1 = nice to have, 5 = business stops without it"
    )
    fallback_note = models.CharField(max_length=240, blank=True)
    # "Checkout depends on the payment gateway" is stored as
    # checkout.depends_on = [payment_gateway]. Not symmetrical: the gateway doesn't
    # depend on checkout.
    depends_on = models.ManyToManyField(
        "self", symmetrical=False, related_name="dependents", blank=True
    )

    ORG_PATH = "business__organization"
    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["business", "key"], name="unique_component_key"),
            models.CheckConstraint(
                condition=models.Q(criticality__gte=1, criticality__lte=5),
                name="criticality_1_to_5",
            ),
        ]

    def __str__(self):
        return self.name
