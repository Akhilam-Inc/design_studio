"""Singhania is in execution: its BOQ went to contractors, and the first quantities are measured."""

import frappe

from gkd.demo.people import acting_as
from gkd.demo.projects import SINGHANIA
from gkd.gkd_studio.boq_actions import create_contractor_orders

ORDER_DATE = "2026-11-09"
COMPLETE_BY = "2026-12-19"

# Rows already executed at site, as measured by the supervisor: (room, item code): executed qty.
EXECUTED = {
	("Master Toilet", "CIV-WATERPROOF"): 92,
	("Living & Dining", "ELE-POINT"): 37,
	("Living & Dining", "FC-COVE"): 104,
}


def create():
	boq = frappe.db.get_value("GKD Project BOQ", {"project_name": SINGHANIA, "workflow_state": "Approved"})
	if not boq:
		return
	with acting_as("pm_rohan"):
		for name in create_contractor_orders(boq):
			submit_order(name)
		record_executed_quantities(boq)


def submit_order(name):
	order = frappe.get_doc("Purchase Order", name)
	order.transaction_date = ORDER_DATE
	order.schedule_date = COMPLETE_BY
	for row in order.items:
		row.schedule_date = COMPLETE_BY
	order.submit()


def record_executed_quantities(boq_name):
	boq = frappe.get_doc("GKD Project BOQ", boq_name)
	for row in boq.items:
		executed = EXECUTED.get((row.room_area, row.item))
		if executed:
			row.actual_qty = executed
	boq.save()
