import frappe


def execute():
	"""School App Settings gained "Show Fees to Class Teachers", which defaults on; saved singles
	don't pick up new defaults. Only fill it in when nothing is stored yet.
	"""
	stored = frappe.db.sql(
		"select count(*) from `tabSingles` where doctype=%s and field=%s",
		("School App Settings", "show_fees_to_teachers"),
	)[0][0]
	if not stored:
		frappe.db.set_single_value("School App Settings", "show_fees_to_teachers", 1)
