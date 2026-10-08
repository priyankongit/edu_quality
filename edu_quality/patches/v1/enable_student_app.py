import frappe


def execute():
	"""School App Settings gained "Enable Student App", which defaults on; saved singles don't pick
	up new defaults. Only fill it in when nothing is stored yet.
	"""
	stored = frappe.db.sql(
		"select count(*) from `tabSingles` where doctype=%s and field=%s",
		("School App Settings", "enable_student_app"),
	)[0][0]
	if not stored:
		frappe.db.set_single_value("School App Settings", "enable_student_app", 1)
