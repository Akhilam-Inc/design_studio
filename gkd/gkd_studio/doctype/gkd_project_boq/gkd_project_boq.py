# Copyright (c) 2026, raaj@akhilaminc.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# States a BOQ can reach only after the site visit, and only after the customer's sign-off.
AFTER_SITE_VISIT = ("Site Verified", "Pending Customer Approval", "Approved", "Handed Over")
AFTER_CUSTOMER_APPROVAL = ("Approved", "Handed Over")


class GKDProjectBOQ(Document):
	def validate(self):
		self.set_row_amounts()
		self.set_variance()
		self.set_totals()
		self.validate_approval_gates()

	def before_update_after_submit(self):
		# Actual quantities are entered after approval, as work is executed.
		self.set_variance()
		self.set_variance_value()
		self.validate_handover()

	def validate_handover(self):
		"""Handed Over means contractors hold orders for the scope. The workflow button alone must not claim it."""
		if self.workflow_state != "Handed Over" or not self.has_value_changed("workflow_state"):
			return
		if not frappe.db.exists("Purchase Order", {"gkd_project_boq": self.name, "docstatus": ["<", 2]}):
			frappe.throw(
				_("Use {0} to hand this BOQ over. It creates the contractor orders.").format(
					frappe.bold(_("Create > Contractor Orders"))
				),
				title=_("No Contractor Orders"),
			)

	def set_row_amounts(self):
		for row in self.items:
			# A new row starts from the designed quantity until someone edits the BOQ quantity.
			if not row.boq_qty and row.design_qty:
				row.boq_qty = row.design_qty
			row.amount = flt(row.boq_qty) * flt(row.rate)
			row.approved_qty = approved_qty(row)
			row.approved_amount = flt(row.approved_qty) * flt(row.rate)

	def set_variance(self):
		for row in self.items:
			latest = latest_qty(row)
			row.variance_pct = (latest - flt(row.boq_qty)) / flt(row.boq_qty) * 100 if row.boq_qty else 0
			row.execution_pct = flt(row.executed_qty) / approved_qty(row) * 100 if approved_qty(row) else 0

	def set_totals(self):
		self.total_boq_amount = sum(flt(row.amount) for row in self.items)
		self.total_site_amount = sum(flt(row.approved_amount) for row in self.items)
		self.set_variance_value()

	def set_variance_value(self):
		self.variance_value = sum((latest_qty(row) - flt(row.boq_qty)) * flt(row.rate) for row in self.items)

	def validate_approval_gates(self):
		"""The dual-approval gate. Checked here, not as workflow conditions, so the user is told what is missing."""
		# A draft may be saved empty, so the designer can import its rows from CAD.
		if self.workflow_state not in (None, "", "Draft") and not self.items:
			frappe.throw(_("Add BOQ items before the BOQ leaves Draft."), title=_("BOQ Has No Items"))
		if self.workflow_state in AFTER_SITE_VISIT and not (self.visit_date and self.verified_by):
			self.throw_gate(
				_("Site Verification Missing"), [_("Visit Date"), _("Verified By")], _("Site Verification")
			)
		if self.workflow_state in AFTER_CUSTOMER_APPROVAL and not (
			self.customer_approved and self.approval_date and self.signed_copy
		):
			self.throw_gate(
				_("Customer Approval Missing"),
				[_("Customer Approved"), _("Approval Date"), _("Signed Copy")],
				_("Customer Approval"),
			)

	def throw_gate(self, title, labels, section):
		fields = ", ".join(frappe.bold(label) for label in labels)
		frappe.throw(
			_("Fill {0} in {1} before the BOQ can move to {2}.").format(
				fields, section, frappe.bold(_(self.workflow_state))
			),
			title=title,
		)


def approved_qty(row) -> float:
	"""What the client signs: the measured quantity, or the BOQ quantity for a row nobody measured."""
	return flt(row.site_verified_qty) if row.site_verified_qty else flt(row.boq_qty)


def latest_qty(row) -> float:
	"""The best-known quantity.

	The final actual quantity wins. Work still in progress shows no gap until it passes the approved
	quantity, because a half-done line is not a saving. Otherwise: measured, else the BOQ quantity."""
	if row.actual_qty:
		return flt(row.actual_qty)
	return max(flt(row.executed_qty), approved_qty(row))
