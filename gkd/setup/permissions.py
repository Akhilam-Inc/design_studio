"""Who sees the GKD Studio app on the apps screen and the desktop grid."""

import frappe

STUDIO_ROLES = {
	"GKD Principal Designer", "GKD Project Manager", "GKD Designer", "GKD Site Supervisor", "GKD Accounts",
	"System Manager",
}


def has_app_permission() -> bool:
	if frappe.session.user == "Administrator":
		return True
	return bool(STUDIO_ROLES.intersection(frappe.get_roles()))
