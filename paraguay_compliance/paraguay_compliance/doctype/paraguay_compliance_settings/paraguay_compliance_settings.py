import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class ParaguayComplianceSettings(Document):
	def validate(self):
		self._set_ruc_and_dv_from_company_tax_id()
		self._sync_mapping_rows_with_api_provider()
		self._validate_unique_accounts()
		self._validate_account_types()

		if not self.naming_series_doctype:
			self.naming_series_doctype = "Sales Invoice"

		if self.has_value_changed("naming_series_options") or self.has_value_changed("naming_series_doctype"):
			if self.naming_series_options:
				_update_core_naming_series(self.naming_series_doctype, self.naming_series_options)

		if self.billing_regime and not (self.vat_mapping or []):
			frappe.msgprint(
				_("El mapeo de IVA está vacío. Use el botón 'Configurar IVA Estándar' para configurarlo automáticamente."),
				indicator="orange",
				alert=True,
			)

	def get_vat_mapping(self, account_head, direction):
		for row in self.get("vat_mapping") or []:
			if row.account != account_head:
				continue

			if not direction or row.direction in (direction, "Ambos"):
				return row

		return None

	def get_iva_mapping(self, account_head, direction):
		# Backward-compatible alias for older callers.
		return self.get_vat_mapping(account_head, direction)

	def get_active_timbrado(self, tipo_comprobante):
		today = getdate(nowdate())

		for row in self.get("timbrado_entries") or []:
			if not row.is_active:
				continue
			if row.voucher_type != tipo_comprobante:
				continue

			if not row.valid_until or getdate(row.valid_until) >= today:
				return row

		frappe.throw(
			_("No hay timbrado activo para '{0}'. Configure un timbrado en Paraguay Compliance Settings.").format(
				tipo_comprobante
			)
		)

	def _validate_unique_accounts(self):
		seen = set()
		for row in self.get("vat_mapping") or []:
			if not row.account:
				continue

			if row.account in seen:
				frappe.throw(_("No se permiten cuentas duplicadas en el mapeo de IVA: {0}").format(row.account))
			seen.add(row.account)

	def _validate_account_types(self):
		for row in self.get("vat_mapping") or []:
			if not row.account:
				continue

			account_type = frappe.db.get_value("Account", row.account, "account_type")
			if account_type != "Tax":
				frappe.throw(
					_("La cuenta '{0}' debe tener Account Type = Tax para ser usada en el mapeo de IVA.").format(
						row.account
					)
				)

	def _set_ruc_and_dv_from_company_tax_id(self):
		if not self.company:
			return

		tax_id = frappe.db.get_value("Company", self.company, "tax_id") or ""
		if not str(tax_id).strip():
			return

		ruc_base = _extract_ruc_base(tax_id)
		if not ruc_base:
			return

		self.ruc = ruc_base
		self.dv = str(calculate_dv_paraguay(ruc_base))

	def _sync_mapping_rows_with_api_provider(self):
		if self.api_provider not in {"Ninguno", "Custom"}:
			return

		if self.get("mapping_rows"):
			self.set("mapping_rows", [])


@frappe.whitelist()
def get_core_naming_series_options(doctype: str = "Sales Invoice"):
	dns = frappe.get_single("Document Naming Settings")
	return dns.get_options(doctype) or ""


@frappe.whitelist()
def sync_core_naming_series_options(doctype: str, naming_series_options: str):
	if not doctype:
		frappe.throw("DocType is required.")
	if not naming_series_options:
		frappe.throw("Naming series options are required.")

	_update_core_naming_series(doctype, naming_series_options)
	return {"ok": True}


def _update_core_naming_series(doctype: str, naming_series_options: str):
	dns = frappe.get_single("Document Naming Settings")
	dns.transaction_type = doctype
	dns.naming_series_options = naming_series_options
	dns.validate_set_series()
	dns.check_duplicate()
	dns.set_series_options_in_meta(doctype, naming_series_options)


def _extract_ruc_base(tax_id: str) -> str:
	value = str(tax_id or "").strip()
	if not value:
		return ""

	if "-" in value:
		value = value.split("-", 1)[0]

	# Keep only alphanumeric characters for DV calculation consistency.
	return "".join(ch for ch in value if ch.isalnum())


def calculate_dv_paraguay(ruc: str) -> int:
	total = 0
	weight = 2

	for char in reversed(str(ruc)):
		val = int(char) if char.isdigit() else ord(char)
		total += val * weight
		weight += 1

	remainder = total % 11
	return 11 - remainder if remainder > 1 else 0
