import frappe


PARAGUAY_DEFAULT_ITEM_TAX_TEMPLATE = "Paraguay Tax"
PARAGUAY_DEFAULT_IVA_RATE = 10.0


def run_setup(*args, **kwargs):
	# ERPNext warehouse bootstrap can fail on fresh sites if Transit type is absent.
	ensure_transit_warehouse_type()
	ensure_paraguay_default_item_tax_template()


def ensure_transit_warehouse_type():
	if frappe.db.exists("Warehouse Type", "Transit"):
		return

	doc = frappe.new_doc("Warehouse Type")
	doc.name = "Transit"
	doc.insert(ignore_permissions=True)


def ensure_paraguay_default_item_tax_template():
	"""Create default Paraguay item tax template per Paraguay company if missing."""
	companies = frappe.get_all("Company", filters={"country": "Paraguay"}, pluck="name")

	for company in companies:
		if frappe.db.exists(
			"Item Tax Template",
			{"company": company, "title": PARAGUAY_DEFAULT_ITEM_TAX_TEMPLATE},
		):
			continue

		tax_account = get_default_paraguay_tax_account(company)
		if not tax_account:
			continue

		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": PARAGUAY_DEFAULT_ITEM_TAX_TEMPLATE,
				"company": company,
				"taxes": [
					{
						"tax_type": tax_account,
						"tax_rate": PARAGUAY_DEFAULT_IVA_RATE,
					}
				],
			}
		).insert(ignore_permissions=True)


def get_default_paraguay_tax_account(company: str):
	"""Resolve the most appropriate tax account for the Paraguay default template."""
	candidates = (
		{"account_number": "2.1.2.1"},  # IVA - Debito Fiscal (Paraguay COA)
		{"account_name": "VAT", "account_type": "Tax"},
		{"account_name": "IVA - Debito Fiscal"},
		{"account_name": "IVA"},
		{"account_type": "Tax"},
	)

	for candidate in candidates:
		account = frappe.db.get_value(
			"Account",
			{"company": company, "is_group": 0, **candidate},
			"name",
		)
		if account:
			return account

	return None
