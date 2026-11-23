"""Singhania is in execution: its BOQ went to contractors, and the first quantities are measured."""

import frappe

from gkd.demo.people import acting_as, employee
from gkd.demo.projects import SINGHANIA
from gkd.gkd_studio.boq_actions import create_contractor_orders

ORDER_DATE = "2026-11-09"
COMPLETE_BY = "2026-12-19"

# Work the supervisor reported at site: (day, room, item code, quantity done, item finished).
# Waterproofing, the points and the cove end at 92, 37 and 104, so the variance story is unchanged.
EXECUTION = [
	("2026-11-16", "Master Toilet", "CIV-WATERPROOF", 50, False),
	("2026-11-17", "Master Toilet", "CIV-WATERPROOF", 42, True),
	("2026-11-18", "Living & Dining", "ELE-POINT", 37, True),
	("2026-11-19", "Living & Dining", "FC-COVE", 60, False),
	("2026-11-20", "Living & Dining", "FC-COVE", 44, True),
]
SUPERVISOR = "sup_vikram"
ENTRY_FIELDS = ("project", "activity_type", "hours", "progress_pct", "work_done", "photo", "has_blocker",
	"blocker_category", "comments")


def create():
	boq = frappe.db.get_value(
		"GKD Project BOQ", {"project_name": SINGHANIA, "workflow_state": ["in", ["Approved", "Handed Over"]]}, ["name", "workflow_state"]
	)
	if not boq:
		return
	name, state = boq
	if state == "Approved":
		with acting_as("pm_rohan"):
			for order in create_contractor_orders(name):
				submit_order(order)
	report_executed_quantities(name)


def submit_order(name):
	order = frappe.get_doc("Purchase Order", name)
	order.transaction_date = ORDER_DATE
	order.schedule_date = COMPLETE_BY
	for row in order.items:
		row.schedule_date = COMPLETE_BY
	order.submit()


def report_executed_quantities(boq_name):
	"""Re-file the supervisor's daily reports with the quantity done, so the BOQ is fed the way it is in real use."""
	boq = frappe.get_doc("GKD Project BOQ", boq_name)
	if any(row.executed_qty for row in boq.items):
		return
	# Quantities typed by hand in an earlier load are replaced by the reports.
	for row in boq.items:
		row.actual_qty = 0
	boq.save()
	rows = {(row.room_area, row.item): row.name for row in boq.items}
	for day, room, item, qty, finished in EXECUTION:
		report = frappe.db.get_value(
			"GKD Daily Progress Report", {"employee": employee(SUPERVISOR), "report_date": day, "docstatus": 1}
		)
		if report:
			refile(report, boq.project, {"boq_item": rows[(room, item)], "qty_done": qty, "item_finished": int(finished)})


def refile(report_name, project, measured):
	old = frappe.get_doc("GKD Daily Progress Report", report_name)
	entries = [{field: row.get(field) for field in ENTRY_FIELDS} for row in old.entries]
	target = next((row for row in entries if row["project"] == project), None)
	if not target:
		target = {"project": project, "activity_type": "Site Supervision", "hours": 1, "work_done": "Site check"}
		entries.append(target)
	target.update(measured)
	old.flags.ignore_permissions = True
	old.cancel()
	with acting_as(SUPERVISOR):
		new = frappe.get_doc({
			"doctype": "GKD Daily Progress Report", "employee": old.employee, "report_date": old.report_date,
			"check_in_time": old.check_in_time, "check_out_time": old.check_out_time, "entries": entries,
		})
		new.insert()
		new.submit()
