"""Actions on an approved BOQ: draw up the contract, and hand the scope over to contractors."""

import frappe
from erpnext.crm.doctype.contract_template.contract_template import get_contract_template
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, cint, nowdate

from gkd.setup.contract_template import TEMPLATE

APPROVED = "Approved"


@frappe.whitelist(methods=["POST"])
def make_contract(source_name: str):
	"""Return a new, unsaved Contract for the approved BOQ, for the user to review and save."""
	boq = get_approved_boq(source_name, "read")
	existing = frappe.db.get_value("Contract", {"gkd_project_boq": boq.name, "docstatus": ["<", 2]})
	if existing:
		frappe.throw(_("Contract {0} already exists for this BOQ.").format(frappe.bold(existing)),
			title=_("Contract Exists"))

	contract = frappe.new_doc("Contract")
	contract.update({
		"party_type": "Customer",
		"party_name": boq.customer,
		"start_date": nowdate(),
		"document_type": "Project",
		"document_name": boq.project,
		"gkd_project_boq": boq.name,
	})
	if frappe.db.exists("Contract Template", TEMPLATE):
		# The Contract form renders terms only when the template changes, so render them here.
		rendered = get_contract_template(TEMPLATE, contract.as_dict())
		contract.contract_template = TEMPLATE
		contract.contract_terms = rendered["contract_terms"]
		contract.requires_fulfilment = rendered["contract_template"].requires_fulfilment
		for term in rendered["contract_template"].fulfilment_terms:
			contract.append("fulfilment_terms", {"requirement": term.requirement})
	return contract


@frappe.whitelist(methods=["POST"])
def create_contractor_orders(boq: str) -> list[str]:
	"""Make one draft Purchase Order per contractor from the approved BOQ, then mark the BOQ Handed Over."""
	doc = get_approved_boq(boq, "write")
	handover = ContractorHandover(doc)
	handover.validate()
	orders = handover.create_orders()
	apply_workflow(doc, "Hand Over")
	return orders


class ContractorHandover:
	def __init__(self, boq):
		self.boq = boq

	def validate(self):
		existing = frappe.get_all(
			"Purchase Order", filters={"gkd_project_boq": self.boq.name, "docstatus": ["<", 2]}, pluck="name"
		)
		if existing:
			frappe.throw(
				_("Contractor orders already exist for this BOQ: {0}").format(", ".join(existing)),
				title=_("Already Handed Over"),
			)
		missing = [str(row.idx) for row in self.boq.items if not row.contractor]
		if missing:
			frappe.throw(
				_("Set a {0} on BOQ rows {1} before handing over.").format(
					frappe.bold(_("Contractor")), ", ".join(missing)
				),
				title=_("Contractor Missing"),
			)

	def create_orders(self) -> list[str]:
		schedule_date = add_days(nowdate(), cint(frappe.db.get_single_value("GKD Settings", "po_lead_days")) or 7)
		orders = []
		for contractor, rows in self.rows_by_contractor().items():
			orders.append(self.create_order(contractor, rows, schedule_date))
		return orders

	def rows_by_contractor(self) -> dict:
		grouped = {}
		for row in self.boq.items:
			if row.approved_qty:
				grouped.setdefault(row.contractor, []).append(row)
		return grouped

	def create_order(self, contractor, rows, schedule_date) -> str:
		order = frappe.get_doc({
			"doctype": "Purchase Order",
			"supplier": contractor,
			"company": self.boq.company,
			"project": self.boq.project,
			"transaction_date": nowdate(),
			"schedule_date": schedule_date,
			"gkd_project_boq": self.boq.name,
			"items": [self.order_line(row, schedule_date) for row in rows],
		})
		order.insert()
		return order.name

	def order_line(self, row, schedule_date):
		return {
			"item_code": row.item,
			"qty": row.approved_qty,
			"uom": row.uom,
			"rate": row.rate,
			"description": row.description or row.item_name,
			"schedule_date": schedule_date,
			"project": self.boq.project,
			"gkd_room_area": row.room_area,
			"gkd_boq_item_ref": row.name,
		}


def get_approved_boq(name, ptype):
	# A whitelisted string argument can arrive as a filter list. Accept a plain name only.
	if not isinstance(name, str):
		frappe.throw(_("Invalid BOQ reference."), frappe.ValidationError)
	boq = frappe.get_doc("GKD Project BOQ", name)
	boq.check_permission(ptype)
	if boq.workflow_state != APPROVED:
		frappe.throw(
			_("BOQ {0} is {1}. This action needs an {2} BOQ.").format(
				frappe.bold(boq.name), frappe.bold(_(boq.workflow_state)), frappe.bold(_(APPROVED))
			),
			title=_("BOQ Not Approved"),
		)
	return boq
