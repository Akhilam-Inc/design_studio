"""Install and migrate hooks for GKD Studio."""

import frappe

from gkd.setup import custom_fields, masters, roles, workflow

SETTINGS_DEFAULTS = {"variance_threshold_pct": 5, "po_lead_days": 7}
LOGO = "/assets/gkd/images/gkd-logo-128.png"
FAVICON = "/assets/gkd/images/gkd-favicon.png"


def after_install():
	configure()
	masters.create()


def after_migrate():
	configure()


def configure():
	"""Configuration that must match the code on every site. Each step only adds or updates GKD records."""
	roles.create()
	custom_fields.create()
	workflow.create()
	seed_settings()
	apply_branding()


def apply_branding():
	"""Studio logo on the desk navbar, the login page and the browser tab. Set once, so a later change by the studio stays."""
	for doctype, field, value in [
		("Navbar Settings", "app_logo", LOGO),
		("Website Settings", "app_logo", LOGO),
		("Website Settings", "favicon", FAVICON),
	]:
		if not frappe.db.get_single_value(doctype, field):
			frappe.db.set_single_value(doctype, field, value)


def seed_settings():
	"""A Single DocType returns nothing until it is saved, so fill in the defaults once."""
	for field, value in SETTINGS_DEFAULTS.items():
		if frappe.db.get_single_value("GKD Settings", field) in (None, "", 0):
			frappe.db.set_single_value("GKD Settings", field, value)
