__version__ = "0.0.1"

try:
	from paraguay_compliance.paraguay.chart_of_accounts import apply_runtime_overrides

	apply_runtime_overrides()
except Exception:
	# Keep app import resilient in contexts where ERPNext modules are not ready yet.
	pass
