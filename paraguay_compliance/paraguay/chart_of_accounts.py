import json
import os

import frappe
from erpnext.accounts.doctype.account.chart_of_accounts import chart_of_accounts as erpnext_coa

PARAGUAY_CHART_NAME = "Plan de Cuentas Paraguayo"
_ORIGINAL_GET_CHART = erpnext_coa.get_chart
_ORIGINAL_GET_CHARTS_FOR_COUNTRY = erpnext_coa.get_charts_for_country


def _get_chart_path():
	return os.path.join(
		os.path.dirname(__file__), "chart_of_accounts", "py_paraguay_chart_of_accounts.json"
	)


def _get_paraguay_chart_tree():
	with open(_get_chart_path()) as f:
		content = json.load(f)
	return content.get("tree")


@frappe.whitelist()
def get_chart(chart_template, existing_company=None):
	if chart_template == PARAGUAY_CHART_NAME:
		return _get_paraguay_chart_tree()
	return _ORIGINAL_GET_CHART(chart_template, existing_company)


@frappe.whitelist()
def get_charts_for_country(country, with_standard=False):
	charts = _ORIGINAL_GET_CHARTS_FOR_COUNTRY(country, with_standard=with_standard)

	# Ensure the Paraguay chart appears for country "Paraguay" or code "py".
	country_code = frappe.get_cached_value("Country", country, "code")
	if country == "Paraguay" or (country_code and country_code.lower() == "py"):
		if PARAGUAY_CHART_NAME not in charts:
			charts.insert(0, PARAGUAY_CHART_NAME)

	return charts


def apply_runtime_overrides():
	"""Patch ERPNext chart helpers so setup/company creation can resolve PY chart."""
	if getattr(erpnext_coa, "_paraguay_coa_patched", False):
		return

	erpnext_coa.get_chart = get_chart
	erpnext_coa.get_charts_for_country = get_charts_for_country
	erpnext_coa._paraguay_coa_patched = True
