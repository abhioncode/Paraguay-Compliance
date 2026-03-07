import frappe


def execute():
	if frappe.db.exists("DocType", "Factura Electronica Paraguay"):
		frappe.delete_doc("DocType", "Factura Electronica Paraguay", force=True, ignore_missing=True)
