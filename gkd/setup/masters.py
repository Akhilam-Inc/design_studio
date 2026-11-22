"""Demo master data for Gauri Khan Design Studio. Safe to run again: it only adds what is missing.

Run by hand with: bench --site SITE execute gkd.setup.masters.create
"""

import frappe

COMPANY = "Gauri Khan Design Studio"
COMPANY_ABBR = "GKDS"
LETTER_HEAD = "Gauri Khan Design Studio"
ITEM_GROUP_ROOT = "GKD Interior Works"
ITEM_GROUPS = [
	"Civil", "Carpentry", "Electrical", "Lighting", "False Ceiling", "Flooring & Stone",
	"Paint & Polish", "Furniture", "Soft Furnishing", "Hardware",
]
TRADES = ["Carpentry", "Civil", "Electrical", "False Ceiling", "Painting", "Furniture", "Lighting"]
ACTIVITY_TYPES = [
	"Site Visit", "Design Work", "Client Meeting", "Vendor Coordination", "Site Supervision", "BOQ Preparation",
]
CONTRACTOR_GROUP = "Contractor"
UOMS = ["Running Foot"]


def create():
	ensure_company()
	ensure_letter_head()
	ensure_item_groups()
	ensure_named("Supplier Group", "supplier_group_name", [CONTRACTOR_GROUP], parent_supplier_group="All Supplier Groups")
	ensure_named("GKD Trade", "trade_name", TRADES)
	ensure_named("Activity Type", "activity_type", ACTIVITY_TYPES)
	ensure_named("UOM", "uom_name", UOMS)
	from gkd.setup import contract_template

	contract_template.create()


def ensure_company():
	if frappe.db.exists("Company", COMPANY):
		return
	frappe.get_doc({
		"doctype": "Company",
		"company_name": COMPANY,
		"abbr": COMPANY_ABBR,
		"country": "India",
		"default_currency": "INR",
		"chart_of_accounts": "Standard",
		"create_chart_of_accounts_based_on": "Standard Template",
	}).insert(ignore_permissions=True)


def ensure_letter_head():
	"""The studio logo and a gold hairline. Not the site default, so other companies keep theirs."""
	doc = frappe.get_doc("Letter Head", LETTER_HEAD) if frappe.db.exists("Letter Head", LETTER_HEAD) else None
	if not doc:
		doc = frappe.new_doc("Letter Head")
		doc.letter_head_name = LETTER_HEAD
	doc.update({
		"source": "HTML", "content": LETTER_HEAD_HTML, "footer_source": "HTML", "footer": LETTER_FOOT_HTML,
		"is_default": 0,
	})
	doc.save(ignore_permissions=True)
	if frappe.db.exists("Company", COMPANY):
		frappe.db.set_value("Company", COMPANY, "default_letter_head", LETTER_HEAD)


def ensure_item_groups():
	ensure_named("Item Group", "item_group_name", [ITEM_GROUP_ROOT], parent_item_group="All Item Groups", is_group=1)
	ensure_named("Item Group", "item_group_name", ITEM_GROUPS, parent_item_group=ITEM_GROUP_ROOT)


def ensure_named(doctype, name_field, names, **values):
	for name in names:
		if not frappe.db.exists(doctype, name):
			frappe.get_doc({"doctype": doctype, name_field: name, **values}).insert(ignore_permissions=True)


# Colors are the Warm Luxe design system: gold #BF873C for lines, ink #182127, bark #655649 for small text.
LETTER_HEAD_HTML = """
<table style="width: 100%; border-bottom: 1px solid #BF873C; padding-bottom: 6px;">
	<tr>
		<td style="width: 70px;"><img src="/assets/gkd/images/gkd-logo.png" style="height: 62px;"></td>
		<td style="vertical-align: middle; font-family: Georgia, serif; color: #182127;">
			<div style="font-size: 18px; letter-spacing: 3px;">GAURI KHAN DESIGN STUDIO</div>
			<div style="font-size: 9px; letter-spacing: 2px; color: #655649;">INTERIOR ARCHITECTURE &middot; DESIGN</div>
		</td>
	</tr>
</table>
"""

LETTER_FOOT_HTML = """
<div style="font-size: 9px; color: #655649; text-align: center; border-top: 1px solid #D6D5D2; padding-top: 4px;">
	Gauri Khan Design Studio &middot; Mumbai
</div>
"""
