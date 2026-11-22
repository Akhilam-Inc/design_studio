"""GKD roles, role profiles, module profile and extra permissions on standard DocTypes."""

import frappe
from frappe.permissions import add_permission, update_permission_property

# Each GKD role is paired with the standard roles it needs to do its job in ERPNext.
ROLE_PROFILES = {
	# Projects Manager has no Timesheet rights in ERPNext, so managers need Projects User too.
	"GKD Principal Designer": ["Projects Manager", "Projects User", "Purchase User", "Employee"],
	"GKD Project Manager": ["Projects Manager", "Projects User", "Purchase User", "Employee"],
	"GKD Designer": ["Projects User", "Employee"],
	"GKD Site Supervisor": ["Projects User", "Employee"],
	"GKD Accounts": ["Accounts User", "Purchase User"],
}

CONTRACT_ROLES = ["GKD Principal Designer", "GKD Project Manager"]
CONTRACT_RIGHTS = ["write", "create", "submit", "cancel", "amend", "print", "email"]

# Modules an interior design studio does not use. Hidden for GKD users.
BLOCKED_MODULES = [
	"Manufacturing", "Quality Management", "Maintenance", "Subcontracting", "Support", "Assets",
	"Telephony", "EDI", "Bulk Transaction", "Recruitment", "Payroll", "Tax and Benefits", "Performance",
]
MODULE_PROFILE = "GKD Studio"
HOME_PAGE = "/desk/design-studio"


def create():
	for role in ROLE_PROFILES:
		ensure_role(role)
	for role, extra_roles in ROLE_PROFILES.items():
		ensure_role_profile(role, [role, *extra_roles])
	ensure_module_profile()
	grant_contract_rights()


def ensure_role(role):
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
	# GKD users land on the Design Studio workspace, not the ERPNext home.
	if frappe.db.get_value("Role", role, "home_page") != HOME_PAGE:
		frappe.db.set_value("Role", role, "home_page", HOME_PAGE)


def ensure_role_profile(name, roles):
	profile = frappe.get_doc("Role Profile", name) if frappe.db.exists("Role Profile", name) else None
	if not profile:
		profile = frappe.new_doc("Role Profile")
		profile.role_profile = name
	existing = {row.role for row in profile.roles}
	for role in roles:
		if role not in existing and frappe.db.exists("Role", role):
			profile.append("roles", {"role": role})
	profile.save(ignore_permissions=True)


def ensure_module_profile():
	profile = frappe.get_doc("Module Profile", MODULE_PROFILE) if frappe.db.exists("Module Profile", MODULE_PROFILE) else None
	if not profile:
		profile = frappe.new_doc("Module Profile")
		profile.module_profile_name = MODULE_PROFILE
	blocked = {row.module for row in profile.block_modules}
	for module in BLOCKED_MODULES:
		if module not in blocked and frappe.db.exists("Module Def", module):
			profile.append("block_modules", {"module": module})
	profile.save(ignore_permissions=True)


def grant_contract_rights():
	for role in CONTRACT_ROLES:
		add_permission("Contract", role)
		for right in CONTRACT_RIGHTS:
			update_permission_property("Contract", role, 0, right, 1)
		# Picking a template on a Contract reads it, so these roles need read on Contract Template too.
		add_permission("Contract Template", role)
