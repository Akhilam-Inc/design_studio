"""Fill a draft BOQ's Design Qty from a CAD quantity export (AutoCAD Data Extraction, CSV).

For the presales demo this reads a prepared export. A live link to the drawing tool is a later project.
"""

import csv
import io

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

COLUMNS = ("Room", "Layer", "Block", "Description", "Length", "Width", "Count", "Unit")
FEET_PER_UNIT = {"mm": 1 / 304.8, "cm": 1 / 30.48, "m": 3.28084, "ft": 1, "in": 1 / 12}
MAX_ROWS = 5000


@frappe.whitelist(methods=["POST"])
def import_cad_export(boq: str, file_url: str) -> dict:
	"""Import an export attached to the BOQ. Re-importing a revised drawing updates the CAD rows in place."""
	if not (isinstance(boq, str) and isinstance(file_url, str)):
		frappe.throw(_("Invalid arguments."), frappe.ValidationError)
	doc = frappe.get_doc("GKD Project BOQ", boq)
	doc.check_permission("write")
	if doc.workflow_state not in (None, "", "Draft"):
		frappe.throw(_("CAD quantities can be imported into a Draft BOQ only."), title=_("BOQ Not in Draft"))

	result = CADImport(doc, read_rows(attached_file(doc, file_url))).apply()
	doc.cad_file = file_url
	doc.cad_imported_on = now_datetime()
	doc.save()
	return result


class CADImport:
	def __init__(self, boq, rows):
		self.boq = boq
		self.rows = rows
		self.mappings = load_mappings()
		self.unmapped = {}

	def apply(self) -> dict:
		lines = self.collect_lines()
		counts = self.merge(lines)
		return {
			**counts,
			"objects": len(self.rows),
			"lines": len(lines),
			"unmapped": list(self.unmapped.values()),
		}

	def collect_lines(self) -> dict:
		"""One BOQ line per room and item, summing every CAD object mapped to it."""
		lines = {}
		for number, row in enumerate(self.rows, start=2):
			mapping = self.find_mapping(row)
			if not mapping:
				self.note_unmapped(number, row)
				continue
			key = (row["Room"], mapping.item)
			line = lines.setdefault(key, {"qty": 0, "refs": {}, "mapping": mapping})
			line["qty"] += measure(row, mapping)
			ref = "/".join(part for part in (mapping.cad_layer, mapping.cad_block) if part)
			line["refs"][ref] = line["refs"].get(ref, 0) + 1
		return lines

	def find_mapping(self, row):
		layer, block = row["Layer"].upper(), row["Block"].upper()
		return self.mappings.get((layer, block)) or self.mappings.get((layer, ""))

	def note_unmapped(self, number, row):
		key = (row["Layer"].upper(), row["Block"].upper())
		entry = self.unmapped.setdefault(key, {
			"line": number, "layer": key[0], "block": key[1], "description": row["Description"], "objects": 0,
		})
		entry["objects"] += 1

	def merge(self, lines) -> dict:
		"""Update CAD rows already on the BOQ, add new ones, drop ones the drawing no longer has.

		Rows typed in by hand have no CAD reference and are left alone. A BOQ Qty the designer changed
		by hand is kept. Otherwise it follows the new Design Qty.
		"""
		existing = {(row.room_area, row.item): row for row in self.boq.items if row.cad_ref}
		counts = {"added": 0, "updated": 0, "removed": 0}
		defaults = LineDefaults([line["mapping"] for line in lines.values()])

		for key, line in lines.items():
			qty, ref = round(line["qty"], 2), cad_reference(line["refs"])
			row = existing.pop(key, None)
			if row:
				if flt(row.design_qty) != qty:
					if flt(row.boq_qty) == flt(row.design_qty):
						row.boq_qty = qty
					row.design_qty = qty
					counts["updated"] += 1
				row.cad_ref = ref
			else:
				self.boq.append("items", {"room_area": key[0], "item": key[1], "design_qty": qty, "boq_qty": qty,
					"cad_ref": ref, **defaults.for_mapping(line["mapping"])})
				counts["added"] += 1

		for row in existing.values():
			self.boq.remove(row)
			counts["removed"] += 1
		return counts


class LineDefaults:
	"""Rate, trade and contractor for new BOQ lines, fetched once for the whole import."""

	def __init__(self, mappings):
		items = list({m.item for m in mappings})
		price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list") or "Standard Selling"
		self.rates = dict(frappe.get_all(
			"Item Price", filters={"item_code": ("in", items or [""]), "price_list": price_list},
			fields=["item_code", "price_list_rate"], as_list=True,
		))
		contractors = frappe.get_all(
			"Supplier", filters={"supplier_group": "Contractor", "disabled": 0}, fields=["name", "gkd_trade"]
		)
		by_trade = {}
		for supplier in contractors:
			by_trade.setdefault(supplier.gkd_trade, []).append(supplier.name)
		# Pre-fill a contractor only when the trade has exactly one. Otherwise the PM chooses.
		self.contractor_by_trade = {trade: names[0] for trade, names in by_trade.items() if len(names) == 1}

	def for_mapping(self, mapping) -> dict:
		return {
			"rate": self.rates.get(mapping.item, 0),
			"trade": mapping.default_trade,
			"contractor": self.contractor_by_trade.get(mapping.default_trade),
		}


def measure(row, mapping) -> float:
	feet = FEET_PER_UNIT[row["Unit"]]
	count = flt(row["Count"]) or 1
	if mapping.quantity_basis == "Area":
		qty = flt(row["Length"]) * feet * flt(row["Width"]) * feet * count
	elif mapping.quantity_basis == "Length":
		qty = flt(row["Length"]) * feet * count
	else:
		qty = count
	return qty * flt(mapping.conversion_factor or 1)


def load_mappings() -> dict:
	rows = frappe.get_all(
		"GKD CAD Mapping",
		filters={"disabled": 0},
		fields=["cad_layer", "cad_block", "item", "quantity_basis", "conversion_factor", "default_trade"],
	)
	return {(row.cad_layer, row.cad_block or ""): row for row in rows}


def attached_file(boq, file_url):
	"""Only a file attached to this BOQ, so the import cannot read other files on the site."""
	name = frappe.db.get_value(
		"File", {"file_url": file_url, "attached_to_doctype": boq.doctype, "attached_to_name": boq.name}
	)
	if not name:
		frappe.throw(_("Attach the CAD export to this BOQ first."), title=_("File Not Attached"))
	return frappe.get_doc("File", name)


def read_rows(file) -> list[dict]:
	content = file.get_content()
	if isinstance(content, bytes):
		content = content.decode("utf-8-sig")
	reader = csv.DictReader(io.StringIO(content))
	headers = {(h or "").strip().title(): h for h in reader.fieldnames or []}
	missing = [column for column in COLUMNS if column not in headers]
	if missing:
		frappe.throw(
			_("The CAD export has no column {0}. Expected columns: {1}.").format(
				", ".join(missing), ", ".join(COLUMNS)
			),
			title=_("Not a CAD Quantity Export"),
		)
	rows = []
	for number, raw in enumerate(reader, start=2):
		if number > MAX_ROWS + 1:
			frappe.throw(_("The CAD export has more than {0} rows.").format(MAX_ROWS), title=_("File Too Large"))
		row = {column: (raw.get(headers[column]) or "").strip() for column in COLUMNS}
		if not any(row.values()):
			continue
		row["Unit"] = row["Unit"].lower()
		if row["Unit"] not in FEET_PER_UNIT:
			frappe.throw(
				_("Row {0}: unit {1} is not one of {2}.").format(
					number, frappe.bold(row["Unit"] or _("(empty)")), ", ".join(FEET_PER_UNIT)
				),
				title=_("Unknown Unit"),
			)
		rows.append(row)
	return rows


def cad_reference(refs: dict) -> str:
	text = ", ".join(f"{ref} x{count}" if count > 1 else ref for ref, count in sorted(refs.items()))
	return text[:140]
