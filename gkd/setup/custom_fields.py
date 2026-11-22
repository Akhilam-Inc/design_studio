"""Custom fields that GKD Studio adds to standard ERPNext DocTypes."""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "GKD Studio"
SITE_TYPES = "\nResidential\nCommercial\nHospitality\nRetail"


def create():
	fields = {**project_fields(), **contract_fields(), **supplier_fields(), **purchase_order_fields()}
	for doctype_fields in fields.values():
		for field in doctype_fields:
			field["module"] = MODULE
	create_custom_fields(fields, update=True)


def project_fields():
	return {
		"Project": [
			field("gkd_site_section", "Section Break", "Site & Team", insert_after="cost_center"),
			field("gkd_site_type", "Select", "Site Type", insert_after="gkd_site_section", options=SITE_TYPES,
				in_standard_filter=1),
			field("gkd_site_city", "Data", "Site City", insert_after="gkd_site_type", in_standard_filter=1),
			field("gkd_site_address", "Small Text", "Site Address", insert_after="gkd_site_city"),
			field("gkd_site_column", "Column Break", insert_after="gkd_site_address"),
			field("gkd_project_designer", "Link", "Project Designer", insert_after="gkd_site_column",
				options="Employee"),
			field("gkd_site_supervisor", "Link", "Site Supervisor", insert_after="gkd_project_designer",
				options="Employee"),
			field("gkd_last_update_on", "Datetime", "Last Update On", insert_after="gkd_site_supervisor",
				read_only=1, no_copy=1),
			field("gkd_last_update", "Small Text", "Last Update", insert_after="gkd_last_update_on",
				read_only=1, no_copy=1),
			field("gkd_team_section", "Section Break", "Project Team", insert_after="gkd_last_update"),
			# Left empty when the client has no fixed resource on a site.
			field("gkd_team", "Table", "Project Team", insert_after="gkd_team_section", options="GKD Project Team"),
		]
	}


def contract_fields():
	return {
		"Contract": [
			field("gkd_project_boq", "Link", "Project BOQ", insert_after="document_name",
				options="GKD Project BOQ", allow_on_submit=1),
		]
	}


def supplier_fields():
	return {
		"Supplier": [
			field("gkd_trade", "Link", "Contractor Trade", insert_after="supplier_group", options="GKD Trade",
				in_standard_filter=1, depends_on='eval:doc.supplier_group=="Contractor"'),
		]
	}


def purchase_order_fields():
	"""A contractor order points back to its BOQ, and each line to the BOQ row it carries out."""
	return {
		"Purchase Order": [
			field("gkd_project_boq", "Link", "Project BOQ", insert_after="supplier", options="GKD Project BOQ",
				read_only=1, no_copy=1, in_standard_filter=1, search_index=1),
		],
		"Purchase Order Item": [
			field("gkd_room_area", "Data", "Room / Area", insert_after="item_name", read_only=1, no_copy=1),
			field("gkd_boq_item_ref", "Data", "BOQ Row", insert_after="gkd_room_area", read_only=1, no_copy=1,
				hidden=1),
		],
	}


def field(fieldname, fieldtype, label=None, **kwargs):
	return {"fieldname": fieldname, "fieldtype": fieldtype, "label": label, **kwargs}
