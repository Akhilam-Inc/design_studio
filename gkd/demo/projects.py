"""Five live studio projects, each at a different stage, with the team's timesheets behind them."""

import frappe
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime

from gkd.demo.people import employee
from gkd.setup.masters import COMPANY

SINGHANIA = "Singhania Residence, Worli"
SAFFRON = "Saffron Table, Bandra West"
KALAKRITI = "Kalakriti Flagship Store, Lower Parel"
VERMA = "Verma Family Office, BKC"
BHATIA = "Bhatia Apartment, Juhu"

# project name: customer, site type, address, PM, designer, supervisor, start, end, last update
PROJECTS = {
	SINGHANIA: ("Aditya & Ritu Singhania", "Residential",
		"Flat 2401, Sea Crest Towers, Dr. Annie Besant Road, Worli, Mumbai 400018",
		"pm_rohan", "des_kavya", "sup_vikram", "2026-08-17", "2027-01-30",
		"Civil work and conduiting done in living and master bedroom. Gypsum ceiling framing started."),
	SAFFRON: ("Saffron Table Hospitality Pvt Ltd", "Hospitality",
		"Ground floor, Waterfield Road, Bandra West, Mumbai 400050",
		"pm_ananya", "des_arjun", "sup_suresh", "2026-10-05", "2027-02-27",
		"Site-verified BOQ sent to the client on 17 Nov. Waiting for sign-off on the bar counter and booths."),
	KALAKRITI: ("Kalakriti Couture LLP", "Retail",
		"Unit G-12, Mill Compound, Senapati Bapat Marg, Lower Parel, Mumbai 400013",
		"pm_rohan", "des_neha", "sup_suresh", "2026-11-02", "2027-01-15",
		"BOQ R0 issued for site measurement. Mall fit-out permit received."),
	VERMA: ("Verma Family Office", "Commercial",
		"8th Floor, One Capital Court, G Block, Bandra Kurla Complex, Mumbai 400051",
		"pm_ananya", "des_kavya", "sup_vikram", "2026-10-19", "2027-03-31",
		"Site measured on 16 Nov. Glass partition and carpet areas are higher than the drawings."),
	BHATIA: ("Kunal Bhatia", "Residential",
		"Flat 6B, Palm Grove CHS, Juhu Tara Road, Mumbai 400049",
		"pm_rohan", "des_arjun", "sup_vikram", "2026-11-09", "2027-02-15",
		"Layout approved by the client. BOQ under preparation."),
}

TIMESHEET_START = "2026-10-26"

# Supervisors report through DPRs, which make their timesheets. Everyone else logs timesheets directly.
SITE_REPORTERS = ("sup_vikram", "sup_suresh")

# Each person repeats a cycle of working days. A day is a list of (project, activity, hours, note).
DAY_PLANS = {
	"principal": [
		[(SINGHANIA, "Client Meeting", 2, "Material sign-off with Mrs. Singhania"), (SAFFRON, "Design Work", 3, "Bar elevation review"),
			(VERMA, "Design Work", 2, "Reception concept review")],
		[(KALAKRITI, "Design Work", 3, "Store layout and display rhythm"), (SAFFRON, "Client Meeting", 2, "Concept walkthrough with the client"),
			(BHATIA, "Design Work", 2, "Living room mood board")],
	],
	"pm_rohan": [
		[(SINGHANIA, "Site Visit", 3, "Weekly site review"), (SINGHANIA, "Vendor Coordination", 2, "Marble lot inspection at the vendor yard"),
			(KALAKRITI, "Client Meeting", 2, "Programme review with the brand team")],
		[(KALAKRITI, "Vendor Coordination", 3, "Mall fit-out permit and NOC"), (BHATIA, "Client Meeting", 2, "Layout presentation"),
			(SINGHANIA, "Vendor Coordination", 3, "Carpentry and ceiling schedule")],
	],
	"pm_ananya": [
		[(SAFFRON, "Client Meeting", 2, "Budget review with the operations head"), (SAFFRON, "Vendor Coordination", 3, "Kitchen exhaust coordination"),
			(VERMA, "Client Meeting", 2, "Requirement workshop")],
		[(VERMA, "Vendor Coordination", 3, "Furniture vendor shortlist"), (SAFFRON, "BOQ Preparation", 3, "BOQ review before client issue"),
			(VERMA, "Site Visit", 2, "Building management approvals")],
	],
	"des_kavya": [
		[(SINGHANIA, "Design Work", 4, "Wardrobe and TV unit shop drawings"), (SINGHANIA, "Site Visit", 2, "Ceiling level check"),
			(VERMA, "Design Work", 2, "Cabin layout options")],
		[(VERMA, "Design Work", 4, "Conference room panelling details"), (VERMA, "BOQ Preparation", 3, "Quantity take-off from CAD")],
	],
	"des_arjun": [
		[(SAFFRON, "Design Work", 5, "Bar counter and booth details"), (SAFFRON, "Client Meeting", 2, "Finishes board review")],
		[(SAFFRON, "BOQ Preparation", 3, "BOQ revision after site visit"), (BHATIA, "Design Work", 3, "Kitchen and wardrobe layout"),
			(BHATIA, "BOQ Preparation", 2, "Quantity take-off for the BOQ draft")],
	],
	"des_neha": [
		[(KALAKRITI, "Design Work", 5, "Display shelving and facade details"), (KALAKRITI, "Client Meeting", 2, "Brand guideline review")],
		[(KALAKRITI, "BOQ Preparation", 4, "Quantity take-off from CAD"), (KALAKRITI, "Site Visit", 3, "Mall unit survey")],
	],
	"sup_vikram": [
		[(SINGHANIA, "Site Supervision", 6, "Civil and conduiting supervision"), (SINGHANIA, "Vendor Coordination", 2, "Material delivery check")],
		[(SINGHANIA, "Site Supervision", 5, "Gypsum ceiling framing"), (VERMA, "Site Visit", 3, "Existing services survey")],
		[(SINGHANIA, "Site Supervision", 5, "Waterproofing test in master toilet"), (BHATIA, "Site Visit", 2, "Existing condition survey"),
			(SINGHANIA, "Vendor Coordination", 1, "Carpenter labour planning")],
	],
	"sup_suresh": [
		[(SAFFRON, "Site Visit", 4, "Services and drainage survey"), (KALAKRITI, "Site Visit", 3, "Unit handover from the mall")],
		[(SAFFRON, "Site Supervision", 5, "Demolition of old fit-out"), (SAFFRON, "Vendor Coordination", 2, "Debris removal permit")],
	],
}


def create():
	for name in PROJECTS:
		create_project(name)
	for key, plan in DAY_PLANS.items():
		if key not in SITE_REPORTERS:
			create_timesheets(key, plan)


def create_project(name):
	if frappe.db.exists("Project", {"project_name": name}):
		return
	customer, site_type, address, pm, designer, supervisor, start, end, update = PROJECTS[name]
	frappe.get_doc({
		"doctype": "Project",
		"project_name": name,
		"company": COMPANY,
		"customer": customer,
		"status": "Open",
		"project_type": "External",
		"expected_start_date": start,
		"expected_end_date": end,
		"gkd_site_type": site_type,
		"gkd_site_city": "Mumbai",
		"gkd_site_address": address,
		"gkd_project_designer": employee(designer),
		"gkd_site_supervisor": employee(supervisor),
		"gkd_last_update": update,
		"gkd_last_update_on": now_datetime(),
		"gkd_team": [
			{"employee": employee(pm), "role_in_project": "Project Manager", "allocation_pct": 40},
			{"employee": employee(designer), "role_in_project": "Designer", "allocation_pct": 60},
			{"employee": employee(supervisor), "role_in_project": "Site Supervisor", "allocation_pct": 50},
		],
	}).insert(ignore_permissions=True)


def create_timesheets(key, plan):
	emp = employee(key)
	day, last_day, index = getdate(TIMESHEET_START), getdate(), 0
	while day <= last_day:
		if day.weekday() != 6 and not frappe.db.exists("Timesheet", {"employee": emp, "start_date": day}):
			blocks = blocks_for(plan[index % len(plan)], day, last_day)
			create_timesheet(emp, day, blocks)
		if day.weekday() != 6:
			index += 1
		day = add_days(day, 1)


def blocks_for(blocks, day, today):
	"""Saturday is a half day. Today has only the morning logged so far."""
	limit = 4 if day.weekday() == 5 or day == today else 24
	kept, total = [], 0
	for project, activity, hours, note in blocks:
		hours = min(hours, limit - total)
		if hours <= 0:
			break
		kept.append((project, activity, hours, note))
		total += hours
	return kept


def create_timesheet(emp, day, blocks):
	start = get_datetime(f"{day} 09:30:00")
	logs = []
	for project_name, activity, hours, note in blocks:
		end = add_to_date(start, hours=hours)
		logs.append({
			"activity_type": activity, "project": project_id(project_name), "hours": hours,
			"from_time": start, "to_time": end, "description": note,
		})
		start = end
	ts = frappe.get_doc({"doctype": "Timesheet", "company": COMPANY, "employee": emp, "time_logs": logs})
	ts.insert(ignore_permissions=True)
	ts.submit()


def project_id(name):
	return frappe.db.get_value("Project", {"project_name": name})
