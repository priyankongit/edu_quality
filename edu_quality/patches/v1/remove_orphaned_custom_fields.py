import frappe

# Custom fields the app used to ship that point at doctypes from apps outside this stack
# (HRMS, Payment Gateways, POS Awesome, a private library app). They were removed from the
# customization JSON, but sites that synced earlier still have them; the Library table one
# makes every Student fail to load.
ORPHANED_FIELDS = (
	"Student-custom_library_books",
	"Company-arrear_component",
	"Company-hra_component",
	"Company-basic_component",
	"Company-posa_primary_offer",
	"Company-posa_customer_offer",
	"Employee-health_insurance_provider",
	"Employee-default_shift",
	"Employee-grade",
	"Employee-job_applicant",
	"Employee-employment_type",
	"Web Form-payment_gateway",
)


def execute():
	for name in ORPHANED_FIELDS:
		options = frappe.db.get_value("Custom Field", name, "options")
		# Keep the field wherever the app that owns its doctype is actually installed.
		if options and not frappe.db.exists("DocType", options):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
