# Copyright (c) 2026, raaj@akhilaminc.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from gkd.gkd_studio.doctype.gkd_project_boq.gkd_project_boq import approved_qty, latest_qty


def execute(filters: dict | None = None):
	report = BOQVarianceReport(frappe._dict(filters or {}))
	rows = report.get_rows()
	return report.get_columns(), rows, None, report.get_chart(rows), report.get_summary(rows)


class BOQVarianceReport:
	"""Design, BOQ, site and actual quantities for every BOQ row, and the value each gap puts at stake."""

	def __init__(self, filters):
		self.filters = filters
		self.threshold = flt(frappe.db.get_single_value("GKD Settings", "variance_threshold_pct")) or 5

	def get_rows(self):
		rows = []
		for line in self.get_lines():
			row = self.make_row(line)
			if cint(self.filters.only_above_threshold) and abs(row.variance_pct) <= self.threshold:
				continue
			rows.append(row)
		return rows

	def get_lines(self):
		# get_list applies the user's permissions on GKD Project BOQ.
		return frappe.get_list(
			"GKD Project BOQ",
			filters=self.get_filters(),
			fields=[
				"name as boq", "project", "project_name", "workflow_state",
				"items.room_area as room_area", "items.item as item", "items.item_name as item_name",
				"items.trade as trade", "items.uom as uom", "items.design_qty as design_qty",
				"items.boq_qty as boq_qty", "items.site_verified_qty as site_verified_qty",
				"items.actual_qty as actual_qty", "items.executed_qty as executed_qty", "items.rate as rate",
			],
			order_by="name asc, items.idx asc",
		)

	def get_filters(self):
		filters = [["docstatus", "<", 2]]
		for field in ("project", "workflow_state"):
			if self.filters.get(field):
				filters.append([field, "=", self.filters.get(field)])
		if self.filters.trade:
			filters.append(["GKD BOQ Item", "trade", "=", self.filters.trade])
		return filters

	def make_row(self, line):
		latest = latest_qty(line)
		boq_qty = flt(line.boq_qty)
		line.approved_qty = approved_qty(line)
		line.design_gap_pct = pct(boq_qty - flt(line.design_qty), line.design_qty)
		line.variance_pct = pct(latest - boq_qty, boq_qty)
		line.variance_value = (latest - boq_qty) * flt(line.rate)
		line.status = self.status(line.variance_pct)
		return line

	def status(self, variance_pct):
		if abs(variance_pct) > self.threshold:
			return _("Over Threshold")
		return _("Within Threshold") if variance_pct else ""

	def get_columns(self):
		return [
			col(_("BOQ"), "boq", "Link", 130, options="GKD Project BOQ"),
			col(_("Project"), "project_name", "Data", 200),
			col(_("Stage"), "workflow_state", "Data", 150),
			col(_("Room / Area"), "room_area", "Data", 130),
			col(_("Item"), "item_name", "Data", 220),
			col(_("Trade"), "trade", "Link", 110, options="GKD Trade"),
			col(_("UOM"), "uom", "Data", 90),
			col(_("Design Qty"), "design_qty", "Float", 95),
			col(_("BOQ Qty"), "boq_qty", "Float", 90),
			col(_("Site Qty"), "site_verified_qty", "Float", 90),
			col(_("Executed Qty"), "executed_qty", "Float", 90),
			col(_("Actual Qty"), "actual_qty", "Float", 90),
			col(_("Rate"), "rate", "Currency", 100),
			col(_("BOQ vs Design %"), "design_gap_pct", "Percent", 110),
			col(_("Variance %"), "variance_pct", "Percent", 95),
			col(_("Variance Value"), "variance_value", "Currency", 120),
			col(_("Status"), "status", "Data", 120),
		]

	def get_chart(self, rows):
		by_project = {}
		for row in rows:
			by_project[row.project_name] = by_project.get(row.project_name, 0) + flt(row.variance_value)
		return {
			"data": {
				"labels": list(by_project),
				"datasets": [{"name": _("Variance Value"), "values": list(by_project.values())}],
			},
			"type": "bar",
			"fieldtype": "Currency",
		}

	def get_summary(self, rows):
		total = sum(flt(row.variance_value) for row in rows)
		flagged = sum(1 for row in rows if abs(row.variance_pct) > self.threshold)
		return [
			{"label": _("Variance Value"), "value": total, "datatype": "Currency",
				"indicator": "Red" if total > 0 else "Green"},
			{"label": _("Rows Over {0}%").format(self.threshold), "value": flagged, "datatype": "Int",
				"indicator": "Orange" if flagged else "Green"},
			{"label": _("BOQs"), "value": len({row.boq for row in rows}), "datatype": "Int"},
		]


def pct(difference, base):
	return flt(difference) / flt(base) * 100 if flt(base) else 0


def col(label, fieldname, fieldtype, width, options=None):
	return {"label": label, "fieldname": fieldname, "fieldtype": fieldtype, "width": width, "options": options}
