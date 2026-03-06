import frappe


def execute():
	if not frappe.db.exists("DocType", "Paraguay Compliance Settings"):
		return

	old_doctype = "Factura Electronica Paraguay"
	new_doctype = "Paraguay Compliance Settings"

	old_doctype_value = frappe.db.sql(
		"""
		select value from `tabSingles`
		where doctype=%s and field=%s
		limit 1
		""",
		(old_doctype, "naming_series_doctype"),
		as_list=True,
	)
	old_options_value = frappe.db.sql(
		"""
		select value from `tabSingles`
		where doctype=%s and field=%s
		limit 1
		""",
		(old_doctype, "naming_series_options"),
		as_list=True,
	)
	old_doctype_value = old_doctype_value[0][0] if old_doctype_value else None
	old_options_value = old_options_value[0][0] if old_options_value else None

	if not old_doctype_value and not old_options_value:
		return

	current_new_doctype = frappe.db.get_single_value(new_doctype, "naming_series_doctype")
	current_new_options = frappe.db.get_single_value(new_doctype, "naming_series_options")

	if not current_new_doctype and old_doctype_value:
		frappe.db.set_single_value(new_doctype, "naming_series_doctype", old_doctype_value)

	if not current_new_options and old_options_value:
		frappe.db.set_single_value(new_doctype, "naming_series_options", old_options_value)
