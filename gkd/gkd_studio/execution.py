"""Executed quantities: a submitted daily report adds the quantity done to the approved BOQ line."""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils import flt

from gkd.gkd_studio.doctype.gkd_project_boq.gkd_project_boq import approved_qty, latest_qty

# Work can be recorded only against a BOQ the client has signed.
EXECUTABLE_STATES = ("Approved", "Handed Over")
DEFAULT_LIMIT_PCT = 5


@frappe.whitelist(methods=["GET"])
def get_executable_lines(project: str) -> list[dict]:
	"""The BOQ lines of a site that work can be recorded against, with how much is done."""
	frappe.has_permission("Project", "read", project, throw=True)
	boqs = frappe.get_list(
		"GKD Project BOQ",
		filters={"project": project, "workflow_state": ["in", EXECUTABLE_STATES], "docstatus": 1},
		pluck="name",
		order_by="creation asc",
	)
	lines = []
	for name in boqs:
		boq = frappe.get_doc("GKD Project BOQ", name)
		lines += [line_data(boq, row) for row in boq.items]
	return lines


def line_data(boq, row) -> dict:
	approved = approved_qty(row)
	return {
		"boq": boq.name, "boq_state": boq.workflow_state, "boq_item": row.name,
		"room_area": row.room_area, "item_name": row.item_name, "trade": row.trade, "uom": row.uom,
		"approved_qty": approved, "executed_qty": flt(row.executed_qty),
		"remaining_qty": flt(approved - flt(row.executed_qty), 3),
		"execution_pct": flt(row.execution_pct, 1), "is_finished": int(bool(row.actual_qty)),
	}


def validate_entries(report):
	"""Check every measured entry of a report and fill the BOQ, label and unit the server owns."""
	seen = set()
	for entry in report.entries:
		if not (entry.boq_item or flt(entry.qty_done) or entry.item_finished):
			entry.boq = entry.boq_line = entry.qty_uom = None
			continue
		if not entry.boq_item:
			frappe.throw(_("Pick the BOQ item for the quantity."), title=_("BOQ Item Missing"))
		row = frappe.db.get_value(
			"GKD BOQ Item", {"name": entry.boq_item, "parenttype": "GKD Project BOQ"},
			["parent", "room_area", "item_name", "uom"], as_dict=True,
		)
		if not row:
			frappe.throw(_("BOQ item {0} does not exist.").format(frappe.bold(entry.boq_item)), title=_("BOQ Item Not Found"))
		line = f"{row.room_area} · {row.item_name}"
		if flt(entry.qty_done) <= 0:
			frappe.throw(
				_("Enter the quantity done for {0}. It must be more than zero.").format(frappe.bold(line)),
				title=_("Quantity Missing"),
			)
		if entry.boq_item in seen:
			frappe.throw(
				_("BOQ item {0} appears twice in this report. Combine the quantities.").format(frappe.bold(line)),
				title=_("Duplicate BOQ Item"),
			)
		seen.add(entry.boq_item)
		validate_boq(entry, row, line)
		entry.boq, entry.boq_line, entry.qty_uom = row.parent, line, row.uom


def validate_boq(entry, row, line: str):
	project, state = frappe.db.get_value("GKD Project BOQ", row.parent, ["project", "workflow_state"])
	if project != entry.project:
		frappe.throw(
			_("{0} belongs to {1}, which is for another site.").format(frappe.bold(line), row.parent),
			title=_("Wrong Site"),
		)
	if state not in EXECUTABLE_STATES:
		frappe.throw(
			_("{0} is in BOQ {1}, which is {2}. Work can be recorded only against an Approved or Handed Over BOQ.").format(
				frappe.bold(line), row.parent, _(state)
			),
			title=_("BOQ Not Approved"),
		)


def post_quantities(report, sign: int):
	"""Add (sign 1, on submit) or take back (sign -1, on cancel) the report's quantities."""
	by_boq = {}
	for entry in report.entries:
		if entry.boq_item and flt(entry.qty_done):
			by_boq.setdefault(entry.boq, []).append(entry)
	for name, entries in by_boq.items():
		post_to_boq(frappe.get_doc("GKD Project BOQ", name), entries, sign, report)


def post_to_boq(boq, entries, sign: int, report):
	limit = flt(frappe.db.get_single_value("GKD Settings", "variance_threshold_pct")) or DEFAULT_LIMIT_PCT
	rows = {row.name: row for row in boq.items}
	over_before = {name: is_over(row, limit) for name, row in rows.items()}
	for entry in entries:
		apply_entry(rows[entry.boq_item], entry, sign)
	boq.flags.ignore_permissions = True
	boq.save()
	if sign > 0:
		for entry in entries:
			row = rows[entry.boq_item]
			if is_over(row, limit) and not over_before[row.name]:
				alert_managers(boq, row, report)
			warn_if_over_approved(row)


def apply_entry(row, entry, sign: int):
	row.executed_qty = max(0, flt(row.executed_qty) + sign * flt(entry.qty_done))
	if sign > 0 and (entry.item_finished or row.actual_qty):
		row.actual_qty = row.executed_qty
	elif sign < 0:
		# Cancelling the report that finished the line reopens it.
		row.actual_qty = 0 if entry.item_finished else (row.executed_qty if row.actual_qty else 0)


def is_over(row, limit: float) -> bool:
	if not flt(row.boq_qty):
		return False
	return abs(latest_qty(row) - flt(row.boq_qty)) / flt(row.boq_qty) * 100 > limit


def warn_if_over_approved(row):
	if flt(row.executed_qty) > approved_qty(row):
		frappe.msgprint(
			_("{0}: {1} {2} done, more than the approved {3}.").format(
				frappe.bold(f"{row.room_area} · {row.item_name}"), flt(row.executed_qty, 2), row.uom, approved_qty(row)
			),
			indicator="orange", alert=True,
		)


def alert_managers(boq, row, report):
	# Imported here because the report module imports this one.
	from gkd.gkd_studio.doctype.gkd_daily_progress_report.gkd_daily_progress_report import project_manager_users

	recipients = project_manager_users(boq.project)
	if not recipients:
		return
	pct = (latest_qty(row) - flt(row.boq_qty)) / flt(row.boq_qty) * 100
	enqueue_create_notification(recipients, {
		"type": "Alert",
		"document_type": boq.doctype,
		"document_name": boq.name,
		"from_user": frappe.session.user,
		"subject": _("BOQ quantity off at {0}: {1} is {2}% against the BOQ").format(
			frappe.db.get_value("Project", boq.project, "project_name"), row.item_name, flt(pct, 1)
		),
		"email_content": _("Reported in {0}. {1}: {2} {3} against {4} in the BOQ.").format(
			report.name, row.room_area, flt(latest_qty(row), 2), row.uom, flt(row.boq_qty, 2)
		),
	})
