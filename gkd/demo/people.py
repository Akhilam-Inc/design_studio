"""The studio team: employees and their demo logins, one GKD role profile each."""

from contextlib import contextmanager

import frappe

from gkd.setup.masters import COMPANY
from gkd.setup.roles import MODULE_PROFILE

EMAIL_DOMAIN = "gkdstudio.demo"  # Not a real domain, so no mail can reach anyone.
DEMO_PASSWORD = "Studio@Demo#2026"

# key: (first name, last name, designation, GKD role, gender, date of joining)
TEAM = {
	"principal": ("Meera", "Kapoor", "Principal Designer", "GKD Principal Designer", "Female", "2016-06-01"),
	"pm_rohan": ("Rohan", "Mehta", "Project Manager", "GKD Project Manager", "Male", "2019-04-15"),
	"pm_ananya": ("Ananya", "Iyer", "Project Manager", "GKD Project Manager", "Female", "2020-08-01"),
	"des_kavya": ("Kavya", "Sharma", "Senior Interior Designer", "GKD Designer", "Female", "2021-01-11"),
	"des_arjun": ("Arjun", "Malhotra", "Interior Designer", "GKD Designer", "Male", "2022-07-04"),
	"des_neha": ("Neha", "Kulkarni", "Interior Designer", "GKD Designer", "Female", "2023-02-20"),
	"sup_vikram": ("Vikram", "Patil", "Site Supervisor", "GKD Site Supervisor", "Male", "2018-11-05"),
	"sup_suresh": ("Suresh", "Yadav", "Site Supervisor", "GKD Site Supervisor", "Male", "2021-09-13"),
	"acc_priya": ("Priya", "Desai", "Accounts Executive", "GKD Accounts", "Female", "2022-03-01"),
}


def create():
	for _first, _last, designation, *_ in TEAM.values():
		if not frappe.db.exists("Designation", designation):
			frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert(ignore_permissions=True)
	for key in TEAM:
		create_user(key)
		create_employee(key)


def create_user(key):
	first, last, _designation, role, *_ = TEAM[key]
	email = email_of(key)
	if frappe.db.exists("User", email):
		return
	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": first,
		"last_name": last,
		"send_welcome_email": 0,
		"user_type": "System User",
		"module_profile": MODULE_PROFILE,
		"role_profiles": [{"role_profile": role}],
		"new_password": DEMO_PASSWORD,
	})
	user.insert(ignore_permissions=True)
	frappe.defaults.set_user_default("company", COMPANY, email)


def create_employee(key):
	first, last, designation, _role, gender, joined = TEAM[key]
	if frappe.db.exists("Employee", {"user_id": email_of(key)}):
		return
	frappe.get_doc({
		"doctype": "Employee",
		"first_name": first,
		"last_name": last,
		"gender": gender,
		"date_of_birth": "1990-05-14",
		"date_of_joining": joined,
		"company": COMPANY,
		"designation": designation,
		"user_id": email_of(key),
		# Staff pick each other in project teams and BOQs, so no one is limited to their own record.
		"create_user_permission": 0,
	}).insert(ignore_permissions=True)


@contextmanager
def acting_as(key):
	"""Act as a team member, so the workflow, timeline and assignments record the real person.

	Only the demo loader uses this, and it runs from `bench execute`, never from a request.
	"""
	frappe.set_user(email_of(key))  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser -- reviewed: CLI-only demo loader
	try:
		yield
	finally:
		frappe.set_user("Administrator")  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser -- reviewed: CLI-only demo loader


def email_of(key):
	first, last, *_ = TEAM[key]
	return f"{first}.{last}@{EMAIL_DOMAIN}".lower()


def employee(key):
	return frappe.db.get_value("Employee", {"user_id": email_of(key)})
