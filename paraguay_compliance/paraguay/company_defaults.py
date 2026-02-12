import frappe


def set_stock_defaults_for_paraguay_company(doc, method=None):
	"""Set default inventory accounts for Paraguay chart if missing.

	Triggered on Company on_update so accounts exist.
	"""
	if doc.chart_of_accounts != "Plan de Cuentas Paraguayo":
		return

	if not doc.enable_perpetual_inventory:
		return

	updates = {}

	if not doc.default_inventory_account:
		inv_acc = frappe.db.get_value(
			"Account",
			{"company": doc.name, "account_number": "1.1.3.1"},
			"name",
		)
		if inv_acc:
			updates["default_inventory_account"] = inv_acc

	if not doc.stock_adjustment_account:
		adj_acc = frappe.db.get_value(
			"Account",
			{"company": doc.name, "account_number": "5.1.4.0"},
			"name",
		)
		if adj_acc:
			updates["stock_adjustment_account"] = adj_acc

	if updates:
		frappe.db.set_value("Company", doc.name, updates)
