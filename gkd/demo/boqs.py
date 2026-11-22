"""One BOQ per project, each taken through the real workflow by the people who own each step."""

import frappe
from frappe.model.workflow import apply_workflow

from gkd.demo import cad, catalog
from gkd.demo.people import acting_as, employee
from gkd.demo.projects import BHATIA, KALAKRITI, PROJECTS, SAFFRON, SINGHANIA, VERMA

# Rows are (room, item code, design qty, site verified qty). BOQ qty starts at the design qty.
BOQS = {
	SINGHANIA: {
		"stage": "Approved", "boq_date": "2026-10-20", "revision_no": 1,
		"site": ("2026-10-28", "Measured with a laser on 28 Oct. The master bedroom wardrobe wall is 11'4\", "
			"not 10'8\" as drawn. The living floor area includes the balcony step-down."),
		"approval": ("Ritu Singhania", "2026-11-03"),
		"rows": [
			("Living & Dining", "FLR-STATUARIO", 620, 642), ("Living & Dining", "FC-GYPSUM", 600, 612),
			("Living & Dining", "FC-COVE", 96, 100), ("Living & Dining", "LGT-DOWNLIGHT", 28, 28),
			("Living & Dining", "LGT-PROFILE", 96, 100), ("Living & Dining", "CRP-TV-UNIT", 64, 64),
			("Living & Dining", "CRP-PANELLING", 180, 192), ("Living & Dining", "PNT-EMULSION", 1450, 1480),
			("Living & Dining", "ELE-POINT", 34, 36), ("Living & Dining", "FUR-SOFA", 1, 1),
			("Living & Dining", "FUR-DINING", 1, 1), ("Living & Dining", "LGT-PENDANT", 3, 3),
			("Living & Dining", "SFT-CURTAIN", 42, 44),
			("Master Bedroom", "FLR-OAK", 280, 286), ("Master Bedroom", "CRP-WARDROBE", 96, 104),
			("Master Bedroom", "FC-GYPSUM", 280, 280), ("Master Bedroom", "PNT-EMULSION", 820, 820),
			("Master Bedroom", "SFT-CURTAIN", 16, 16),
			("Kitchen", "CRP-KITCHEN-BASE", 16, 16.5), ("Kitchen", "CRP-KITCHEN-WALL", 12, 12),
			("Kitchen", "FLR-GRANITE-TOP", 16, 16.5), ("Kitchen", "HW-TANDEM", 10, 10), ("Kitchen", "HW-HINGE", 24, 24),
			("Master Toilet", "CIV-WATERPROOF", 85, 90), ("Master Toilet", "HW-GLASS-PARTITION", 32, 32),
			("Master Toilet", "HW-MIRROR", 18, 18),
		],
	},
	SAFFRON: {
		"stage": "Pending Customer Approval", "boq_date": "2026-11-06", "revision_no": 1,
		"site": ("2026-11-12", "Visited on 12 Nov with the client's operations head. The booth run is 4 rft shorter "
			"because of the fire exit clearance. The back-of-house partition now encloses the dry store."),
		"rows": [
			("Dining Hall", "FLR-VITRIFIED", 2200, 2265), ("Dining Hall", "FC-WOOD-SLAT", 900, 940),
			("Dining Hall", "FC-GYPSUM", 1300, 1300), ("Dining Hall", "LGT-TRACK", 36, 40),
			("Dining Hall", "LGT-PENDANT", 14, 14), ("Dining Hall", "FUR-BOOTH", 64, 60),
			("Dining Hall", "PNT-TEXTURE", 420, 450), ("Dining Hall", "ELE-POINT", 60, 64),
			("Bar", "CRP-BAR-COUNTER", 22, 24), ("Bar", "FUR-BAR-STOOL", 12, 12),
			("Bar", "CRP-PANELLING", 260, 260), ("Bar", "LGT-PROFILE", 80, 86),
			("Entrance & Waiting", "CRP-DOOR", 2, 2), ("Entrance & Waiting", "HW-MIRROR", 40, 40),
			("Entrance & Waiting", "FLR-STATUARIO", 180, 176),
			("Washrooms", "CIV-WATERPROOF", 160, 168), ("Washrooms", "HW-GLASS-PARTITION", 48, 48),
			("Back of House", "CIV-BRICK-WALL", 320, 340), ("Back of House", "CIV-PLASTER", 900, 960),
			("Back of House", "ELE-DB", 2, 2),
		],
	},
	VERMA: {
		"stage": "Site Verified", "boq_date": "2026-11-10", "revision_no": 0,
		"site": ("2026-11-16", "Cabin glass partitions run full height to the slab, not to the false ceiling. "
			"The carpet area is larger because the lift lobby is in our scope."),
		"rows": [
			("Reception", "FLR-STATUARIO", 260, 255), ("Reception", "CRP-PANELLING", 150, 150),
			("Reception", "FC-GYPSUM", 260, 260),
			("Cabins", "HW-GLASS-PARTITION", 360, 396), ("Cabins", "SFT-CARPET", 540, 585),
			("Open Office", "FUR-WORKSTATION", 18, 18), ("Open Office", "SFT-CARPET", 1100, 1150),
			("Open Office", "FC-GYPSUM", 1300, 1320), ("Open Office", "LGT-DOWNLIGHT", 64, 64),
			("Open Office", "ELE-POINT", 72, 76), ("Open Office", "ELE-DATA", 36, 38),
			("Conference Room", "FUR-CONFERENCE", 1, 1), ("Conference Room", "CRP-PANELLING", 220, 220),
			("Conference Room", "SFT-BLIND", 120, 130),
			("Pantry", "CRP-KITCHEN-BASE", 10, 10), ("Pantry", "FLR-GRANITE-TOP", 10, 10),
		],
	},
	KALAKRITI: {
		"stage": "Pending Site Verification", "boq_date": "2026-11-18", "revision_no": 0,
		"rows": [
			("Store Floor", "FLR-OAK", 1400, None), ("Store Floor", "FC-GYPSUM", 1400, None),
			("Store Floor", "LGT-TRACK", 48, None), ("Store Floor", "LGT-DOWNLIGHT", 30, None),
			("Store Floor", "CRP-DISPLAY", 120, None), ("Store Floor", "CRP-CASH-COUNTER", 1, None),
			("Store Floor", "HW-MIRROR", 60, None), ("Store Floor", "PNT-DUCO", 380, None),
			("Store Floor", "ELE-POINT", 40, None), ("Store Floor", "ELE-DATA", 8, None),
			("Trial Rooms", "CIV-BRICK-WALL", 220, None), ("Trial Rooms", "CRP-DOOR", 4, None),
			("Trial Rooms", "SFT-CARPET", 120, None), ("Trial Rooms", "LGT-PROFILE", 40, None),
			("Facade", "CRP-PANELLING", 140, None), ("Facade", "LGT-PROFILE", 30, None),
		],
	},
	BHATIA: {
		# Built from the architect's CAD quantity export, not typed in.
		"stage": "Draft", "boq_date": "2026-11-19", "revision_no": 0, "cad_export": "bhatia_apartment_R0.csv",
		"rows": [],
	},
}

# The order each BOQ passes through the workflow, and who acts at each step.
STEPS = ["Pending Site Verification", "Site Verified", "Pending Customer Approval", "Approved"]


def create():
	for project_name, spec in BOQS.items():
		if frappe.db.exists("GKD Project BOQ", {"project_name": project_name}):
			continue
		run_as_team(project_name, spec)


def run_as_team(project_name, spec):
	_customer, _type, _address, pm, designer, supervisor, *_ = PROJECTS[project_name]
	target = STEPS.index(spec["stage"]) if spec["stage"] in STEPS else -1
	boq = draft(project_name, spec, designer)
	if spec.get("cad_export"):
		cad.import_export(boq.name, designer, spec["cad_export"])
		boq.reload()
	if target >= 0:
		boq = act(designer, boq, "Send for Site Verification")
	if target >= 1:
		boq = verify(boq, spec, supervisor)
	if target >= 2:
		boq = act(pm, boq, "Send to Customer")
	if target >= 3:
		boq = approve(boq, spec, pm)
	frappe.db.set_value("Project", boq.project, "estimated_costing", boq.total_site_amount or boq.total_boq_amount)


def draft(project_name, spec, designer):
	with acting_as(designer):
		return frappe.get_doc({
			"doctype": "GKD Project BOQ",
			"project": frappe.db.get_value("Project", {"project_name": project_name}),
			"boq_date": spec["boq_date"],
			"revision_no": spec["revision_no"],
			"prepared_by": employee(designer),
			"items": [boq_row(*row) for row in spec["rows"]],
		}).insert()


def verify(boq, spec, supervisor):
	visit_date, remarks = spec["site"]
	with acting_as(supervisor):
		boq = frappe.get_doc("GKD Project BOQ", boq.name)
		boq.update({"visit_date": visit_date, "verified_by": employee(supervisor), "site_remarks": remarks})
		for item, row in zip(boq.items, spec["rows"], strict=True):
			item.site_verified_qty = row[3]
		boq.save()
		boq.add_comment("Comment", remarks)
	return act(supervisor, boq, "Verify")


def approve(boq, spec, pm):
	approved_by, approval_date = spec["approval"]
	with acting_as(pm):
		boq = frappe.get_doc("GKD Project BOQ", boq.name)
		boq.update({
			"customer_approved": 1, "approved_by_name": approved_by, "approval_date": approval_date,
			"signed_copy": attach_signed_copy(boq),
		})
		boq.save()
	return act(pm, boq, "Approve")


def attach_signed_copy(boq) -> str:
	"""Stands in for the scan of the printed BOQ the client signed. Here it is the unsigned print."""
	pdf = frappe.get_print(boq.doctype, boq.name, print_format="GKD BOQ for Client", as_pdf=True)
	file = frappe.get_doc({
		"doctype": "File",
		"file_name": f"{boq.name}-signed-by-client.pdf",
		"attached_to_doctype": boq.doctype,
		"attached_to_name": boq.name,
		"attached_to_field": "signed_copy",
		"is_private": 1,
		"content": pdf,
	}).insert()
	return file.file_url


def act(person, boq, action):
	with acting_as(person):
		return apply_workflow(frappe.get_doc("GKD Project BOQ", boq.name), action)


def boq_row(room, item_code, design_qty, _site_qty):
	trade = catalog.trade(item_code)
	return {
		"room_area": room, "item": item_code, "design_qty": design_qty, "rate": catalog.rate(item_code),
		"trade": trade, "contractor": catalog.CONTRACTOR_BY_TRADE[trade],
	}
