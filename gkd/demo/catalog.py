"""Item master in interior terms, contractors by trade, and the studio's clients."""

import frappe

SQFT, RFT, NOS = "Square Foot", "Running Foot", "Nos"

# Each item group is carried out by one trade. BOQ rows take their trade and contractor from this.
TRADE_BY_GROUP = {
	"Civil": "Civil", "Flooring & Stone": "Civil", "Carpentry": "Carpentry", "Hardware": "Carpentry",
	"False Ceiling": "False Ceiling", "Electrical": "Electrical", "Lighting": "Lighting",
	"Paint & Polish": "Painting", "Furniture": "Furniture", "Soft Furnishing": "Furniture",
}

# item_code: (item name, item group, UOM, studio rate in INR)
ITEMS = {
	"CIV-BRICK-WALL": ("Brick masonry partition, 115 mm", "Civil", SQFT, 145),
	"CIV-PLASTER": ("Internal wall plaster with POP punning", "Civil", SQFT, 38),
	"CIV-DEMOLITION": ("Demolition and debris removal", "Civil", SQFT, 22),
	"CIV-WATERPROOF": ("Toilet waterproofing, membrane + screed", "Civil", SQFT, 95),
	"FLR-STATUARIO": ("Italian Statuario marble flooring, 18 mm", "Flooring & Stone", SQFT, 650),
	"FLR-OAK": ("Engineered oak wood flooring", "Flooring & Stone", SQFT, 420),
	"FLR-VITRIFIED": ("Vitrified tiles 800 x 1600, laid", "Flooring & Stone", SQFT, 185),
	"FLR-GRANITE-TOP": ("Granite countertop with edge profile", "Flooring & Stone", RFT, 1450),
	"FLR-SKIRTING": ("Marble skirting, 100 mm", "Flooring & Stone", RFT, 160),
	"CRP-WARDROBE": ("Sliding wardrobe, BWP ply with laminate", "Carpentry", SQFT, 1850),
	"CRP-KITCHEN-BASE": ("Modular kitchen base unit", "Carpentry", RFT, 9500),
	"CRP-KITCHEN-WALL": ("Modular kitchen wall unit", "Carpentry", RFT, 6500),
	"CRP-TV-UNIT": ("TV unit in walnut veneer", "Carpentry", SQFT, 2200),
	"CRP-PANELLING": ("Wall panelling in teak veneer", "Carpentry", SQFT, 780),
	"CRP-BAR-COUNTER": ("Bar counter with fluted front", "Carpentry", RFT, 14500),
	"CRP-DISPLAY": ("Retail display shelving with LED groove", "Carpentry", RFT, 5200),
	"CRP-CASH-COUNTER": ("Cash and wrap counter", "Carpentry", NOS, 85000),
	"CRP-DOOR": ("Flush door with veneer and frame", "Carpentry", NOS, 28000),
	"HW-HINGE": ("Soft-close hinge, Hettich", "Hardware", NOS, 650),
	"HW-TANDEM": ("Tandem drawer channel, Blum", "Hardware", NOS, 4200),
	"HW-GLASS-PARTITION": ("Frameless toughened glass partition, 12 mm", "Hardware", SQFT, 950),
	"HW-MIRROR": ("Bevelled mirror with backing", "Hardware", SQFT, 450),
	"FC-GYPSUM": ("Gypsum false ceiling, Saint-Gobain", "False Ceiling", SQFT, 135),
	"FC-COVE": ("Cove ceiling with light trough", "False Ceiling", RFT, 210),
	"FC-WOOD-SLAT": ("Wooden slat ceiling", "False Ceiling", SQFT, 480),
	"ELE-POINT": ("Electrical point wiring, FRLS copper", "Electrical", NOS, 1650),
	"ELE-CONDUIT": ("Concealed PVC conduiting", "Electrical", RFT, 85),
	"ELE-DB": ("Distribution board with MCBs", "Electrical", NOS, 32000),
	"ELE-DATA": ("Data and TV point", "Electrical", NOS, 1200),
	"LGT-DOWNLIGHT": ("LED downlight 12 W, warm white", "Lighting", NOS, 1450),
	"LGT-PROFILE": ("LED strip in aluminium profile", "Lighting", RFT, 650),
	"LGT-PENDANT": ("Decorative brass pendant", "Lighting", NOS, 18500),
	"LGT-TRACK": ("Track light 20 W", "Lighting", NOS, 3800),
	"PNT-EMULSION": ("Royale emulsion, 2 coats on putty", "Paint & Polish", SQFT, 42),
	"PNT-TEXTURE": ("Texture paint, feature wall", "Paint & Polish", SQFT, 145),
	"PNT-PU": ("PU polish on veneer, matt", "Paint & Polish", SQFT, 260),
	"PNT-DUCO": ("Duco paint finish", "Paint & Polish", SQFT, 310),
	"FUR-SOFA": ("Custom 3-seater sofa", "Furniture", NOS, 145000),
	"FUR-DINING": ("6-seater dining table, marble top", "Furniture", NOS, 95000),
	"FUR-BOOTH": ("Restaurant booth seating", "Furniture", RFT, 12500),
	"FUR-BAR-STOOL": ("Bar stool, cane and brass", "Furniture", NOS, 14500),
	"FUR-WORKSTATION": ("Office workstation, 1500 mm", "Furniture", NOS, 42000),
	"FUR-CONFERENCE": ("Conference table, 12-seater", "Furniture", NOS, 165000),
	"SFT-CURTAIN": ("Curtains on motorised track", "Soft Furnishing", RFT, 1850),
	"SFT-BLIND": ("Roman blinds", "Soft Furnishing", SQFT, 320),
	"SFT-CARPET": ("Wall-to-wall carpet", "Soft Furnishing", SQFT, 210),
}

# supplier name: trade
CONTRACTORS = {
	"Shree Ganesh Carpentry Works": "Carpentry",
	"Mistry Civil Contractors": "Civil",
	"Bright Spark Electricals": "Electrical",
	"Skyline Gypsum Ceilings": "False Ceiling",
	"Colour Craft Painters": "Painting",
	"Lumiere Lighting Solutions": "Lighting",
	"Heritage Furniture Studio": "Furniture",
}
CONTRACTOR_BY_TRADE = {trade: name for name, trade in CONTRACTORS.items()}

# customer name: customer type
CUSTOMERS = {
	"Aditya & Ritu Singhania": "Individual",
	"Saffron Table Hospitality Pvt Ltd": "Company",
	"Kalakriti Couture LLP": "Company",
	"Verma Family Office": "Company",
	"Kunal Bhatia": "Individual",
}


def create():
	create_items()
	create_contractors()
	create_customers()


def create_items():
	for code, (name, group, uom, rate) in ITEMS.items():
		if frappe.db.exists("Item", code):
			continue
		frappe.get_doc({
			"doctype": "Item", "item_code": code, "item_name": name, "item_group": group, "stock_uom": uom,
			"description": name, "is_stock_item": 0, "is_purchase_item": 1, "is_sales_item": 1,
			"standard_rate": rate,
		}).insert(ignore_permissions=True)


def create_contractors():
	for name, trade in CONTRACTORS.items():
		if frappe.db.exists("Supplier", name):
			continue
		frappe.get_doc({
			"doctype": "Supplier", "supplier_name": name, "supplier_type": "Company",
			"supplier_group": "Contractor", "gkd_trade": trade, "country": "India",
		}).insert(ignore_permissions=True)


def create_customers():
	for name, customer_type in CUSTOMERS.items():
		if frappe.db.exists("Customer", name):
			continue
		frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": customer_type}).insert(
			ignore_permissions=True
		)


def rate(item_code):
	return ITEMS[item_code][3]


def trade(item_code):
	return TRADE_BY_GROUP[ITEMS[item_code][1]]
