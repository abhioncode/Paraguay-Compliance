import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Sales Invoice": [
			{
				"fieldname": "section_break_pyg_einvoice",
				"fieldtype": "Section Break",
				"label": "Paraguay E-Invoice",
				"insert_after": "naming_series",
			},
			{
				"fieldname": "pyg_cdc",
				"fieldtype": "Data",
				"label": "CDC",
				"description": "Id unico de 44 digitos del Documento Electronico.",
				"read_only": 1,
				"insert_after": "section_break_pyg_einvoice",
			},
			{
				"fieldname": "pyg_estado",
				"fieldtype": "Data",
				"label": "Estado DE",
				"description": "Estado del Documento Electronico retornado por el proveedor.",
				"read_only": 1,
				"insert_after": "pyg_cdc",
			},
		]
	}

	create_custom_fields(custom_fields, update=True)
	frappe.clear_cache(doctype="Sales Invoice")
