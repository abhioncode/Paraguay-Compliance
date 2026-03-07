import frappe
from frappe import _


ACCOUNTS = [
	# (account_name, parent_account_name, account_type, root_type, tax_rate)
	("IVA Débito 10%", "Tax Assets", "Tax", "Liability", 10),
	("IVA Débito 5%", "Tax Assets", "Tax", "Liability", 5),
	("IVA Exento Ventas", "Tax Assets", "Tax", "Liability", 0),
	("IVA Crédito 10%", "Tax Assets", "Tax", "Asset", 10),
	("IVA Crédito 5%", "Tax Assets", "Tax", "Asset", 5),
	("Retención IVA por Pagar", "Duties and Taxes", "Tax", "Liability", 0),
	("Retención IRE por Pagar", "Duties and Taxes", "Tax", "Liability", 0),
	("Retención INR por Pagar", "Duties and Taxes", "Tax", "Liability", 0),
	("Retención IVA a Favor", "Tax Assets", "Tax", "Asset", 0),
	("Retención IRE a Favor", "Tax Assets", "Tax", "Asset", 0),
]


@frappe.whitelist()
def configurar_iva_estandar(company):
	if not company:
		frappe.throw(_("Company is required."))

	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} does not exist.").format(company))

	summary = {"created": [], "existing": [], "skipped": []}
	company_abbr = frappe.db.get_value("Company", company, "abbr")
	if not company_abbr:
		frappe.throw(_("Company abbreviation is missing for {0}.").format(company))

	accounts_by_base_name = {}
	for account_name, parent_account_name, account_type, root_type, _tax_rate in ACCOUNTS:
		account_doc = _get_existing_account_doc(account_name, company)
		if account_doc:
			summary["existing"].append(f"Cuenta: {account_doc.name}")
			accounts_by_base_name[account_name] = account_doc.name
			continue

		parent_account = _resolve_parent_account(
			company=company,
			root_type=root_type,
			parent_account_name=parent_account_name,
		)
		if not parent_account:
			summary["skipped"].append(f"Cuenta omitida (sin parent): {account_name}")
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"company": company,
				"parent_account": parent_account,
				"is_group": 0,
				"account_type": account_type,
				"root_type": root_type,
			}
		).insert(ignore_permissions=True)

		summary["created"].append(f"Cuenta: {doc.name}")
		accounts_by_base_name[account_name] = doc.name

	_create_sales_templates(company, accounts_by_base_name, summary)
	_create_purchase_templates(company, accounts_by_base_name, summary)
	_populate_iva_mapping(company, accounts_by_base_name, summary)

	frappe.db.commit()
	return summary


def _get_existing_account_doc(account_name: str, company: str):
	"""Return account doc if exists without emitting not-found exceptions/messages."""
	account_name_full = frappe.db.get_value(
		"Account", {"account_name": account_name, "company": company}, "name"
	)
	if not account_name_full:
		return None
	return frappe.get_doc("Account", account_name_full)


def _resolve_parent_account(company: str, root_type: str, parent_account_name: str):
	# 1) Try exact parent account name inside company/root_type tree.
	parent = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_name": parent_account_name,
			"root_type": root_type,
			"is_group": 1,
		},
		"name",
	)
	if parent:
		return parent

	# 2) Fallback: root account for this root_type.
	root = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"root_type": root_type,
			"is_group": 1,
			"parent_account": ("is", "not set"),
		},
		"name",
	)
	if root:
		return root

	# 3) Final fallback: first group account by root_type.
	fallback = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"root_type": root_type,
			"is_group": 1,
		},
		"name",
	)
	return fallback


def _create_sales_templates(company: str, accounts_by_base_name: dict, summary: dict):
	templates = [
		("IVA Ventas 10%", "IVA Débito 10%", 10, "On Net Total"),
		("IVA Ventas 5%", "IVA Débito 5%", 5, "On Net Total"),
		("IVA Ventas Exento", "IVA Exento Ventas", 0, "On Net Total"),
	]

	for template_title, account_base_name, rate, charge_type in templates:
		existing_template = frappe.db.exists(
			"Sales Taxes and Charges Template",
			{"company": company, "title": template_title},
		)
		if existing_template:
			summary["existing"].append(f"Plantilla de ventas: {template_title}")
			continue

		account_head = accounts_by_base_name.get(account_base_name) or frappe.db.get_value(
			"Account", {"company": company, "account_name": account_base_name}, "name"
		)
		if not account_head:
			summary["skipped"].append(f"Plantilla de ventas omitida (sin cuenta): {template_title}")
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": template_title,
				"company": company,
				"taxes": [
					{
						"charge_type": charge_type,
						"account_head": account_head,
						"rate": rate,
						"description": template_title,
						"included_in_print_rate": 1,
					}
				],
			}
		).insert(ignore_permissions=True)
		summary["created"].append(f"Plantilla de ventas: {doc.name}")


def _create_purchase_templates(company: str, accounts_by_base_name: dict, summary: dict):
	templates = [
		("IVA Compras 10%", "IVA Crédito 10%", 10, "On Net Total"),
		("IVA Compras 5%", "IVA Crédito 5%", 5, "On Net Total"),
		("IVA Compras Exento", "IVA Exento Ventas", 0, "On Net Total"),
	]

	for template_title, account_base_name, rate, charge_type in templates:
		existing_template = frappe.db.exists(
			"Purchase Taxes and Charges Template",
			{"company": company, "title": template_title},
		)
		if existing_template:
			summary["existing"].append(f"Plantilla de compras: {template_title}")
			continue

		account_head = accounts_by_base_name.get(account_base_name) or frappe.db.get_value(
			"Account", {"company": company, "account_name": account_base_name}, "name"
		)
		if not account_head:
			summary["skipped"].append(f"Plantilla de compras omitida (sin cuenta): {template_title}")
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": template_title,
				"company": company,
				"taxes": [
					{
						"charge_type": charge_type,
						"account_head": account_head,
						"rate": rate,
						"description": template_title,
						"category": "Total",
						"add_deduct_tax": "Add",
						"included_in_print_rate": 1,
					}
				],
			}
		).insert(ignore_permissions=True)
		summary["created"].append(f"Plantilla de compras: {doc.name}")


def _populate_iva_mapping(company: str, accounts_by_base_name: dict, summary: dict):
	settings = frappe.get_single("Paraguay Compliance Settings")
	should_save = False
	if not settings.company:
		settings.company = company
		should_save = True
	elif settings.company != company:
		summary["skipped"].append(
			f"Se omite asignar company en settings: ya está configurado para '{settings.company}'."
		)

	standard_mappings = [
		("IVA Débito 10%", "10% Gravado", "Ventas"),
		("IVA Débito 5%", "5% Gravado", "Ventas"),
		("IVA Exento Ventas", "0% Exento", "Ventas"),
		("IVA Crédito 10%", "10% Gravado", "Compras"),
		("IVA Crédito 5%", "5% Gravado", "Compras"),
	]

	existing_accounts = {row.account for row in settings.get("vat_mapping") or [] if row.account}
	changed = False

	for account_base_name, government_rate, direction in standard_mappings:
		account_head = accounts_by_base_name.get(account_base_name) or frappe.db.get_value(
			"Account", {"company": company, "account_name": account_base_name}, "name"
		)
		if not account_head:
			summary["skipped"].append(f"Mapeo IVA omitido (sin cuenta): {account_base_name}")
			continue

		if account_head in existing_accounts:
			summary["existing"].append(f"Mapeo IVA: {account_head}")
			continue

		settings.append(
			"vat_mapping",
			{
				"account": account_head,
				"government_rate": government_rate,
				"direction": direction,
			},
		)
		existing_accounts.add(account_head)
		changed = True
		summary["created"].append(f"Mapeo IVA: {account_head} -> {government_rate} ({direction})")

	if changed or should_save:
		settings.flags.ignore_mandatory = True
		settings.save(ignore_permissions=True)
