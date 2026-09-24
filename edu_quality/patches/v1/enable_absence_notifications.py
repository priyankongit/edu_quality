import frappe


def execute():
	"""School App Settings gained a checkbox that defaults on; saved singles don't pick up new defaults.

	Only fill it in when no value has been stored, so a school that switched it off keeps it off.
	"""
	stored = frappe.db.sql(
		"select count(*) from `tabSingles` where doctype=%s and field=%s",
		("School App Settings", "notify_parents_of_absence"),
	)[0][0]
	if not stored:
		frappe.db.set_single_value("School App Settings", "notify_parents_of_absence", 1)
