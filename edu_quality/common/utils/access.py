"""Authorization helpers for guardian/staff-facing endpoints.

These centralize the "who may see/act on this student" checks so that
whitelisted endpoints do not have to re-implement (or forget) ownership
validation.
"""

import frappe
from frappe import _

# Roles that may act on any student's records (school staff).
STAFF_ROLES = {"Administrator", "System Manager", "School Admin", "Instructor"}
# Roles allowed to perform sensitive financial/administrative writes.
ADMIN_ROLES = {"Administrator", "System Manager", "School Admin"}


def session_guardian():
	"""Return the Guardian name linked to the current session user, or None."""
	user = frappe.session.user
	if not user or user == "Guest":
		return None
	return frappe.db.get_value("Guardian", {"user": user}, "name")


def _has_role(roles):
	user = frappe.session.user
	if not user or user == "Guest":
		return False
	return bool(set(frappe.get_roles(user)) & roles)


def is_staff():
	return _has_role(STAFF_ROLES)


def guardian_owns_student(student):
	guardian = session_guardian()
	if not guardian or not student:
		return False
	return bool(
		frappe.db.exists(
			"Student Guardian",
			{"guardian": guardian, "parent": student, "parenttype": "Student"},
		)
	)


def assert_student_access(student):
	"""Permit school staff, or a guardian linked to `student`. Raise otherwise."""
	if is_staff() or guardian_owns_student(student):
		return
	frappe.throw(_("You are not permitted to access this record."), frappe.PermissionError)


def assert_staff():
	"""Restrict to school staff (any staff role)."""
	if not is_staff():
		frappe.throw(_("You are not permitted to access this resource."), frappe.PermissionError)


def assert_admin():
	"""Restrict to school-administration roles."""
	if not _has_role(ADMIN_ROLES):
		frappe.throw(_("You are not permitted to perform this action."), frappe.PermissionError)


def get_user_schools():
	"""List of School names the current user is restricted to, or None if unrestricted
	(Administrator, System Manager, or no School assigned to their Employee record — e.g.
	head office). Reads the "School" User Permission rows that
	edu_quality.edu_quality.server_scripts.employee.add_to_user_permission keeps in sync with
	Employee.school, so there is nothing new to maintain.

	Usage in raw-SQL/query-builder endpoints that bypass Frappe's own permission engine:

		schools = get_user_schools()
		if schools is not None:
			# restrict the query to `schools`, or frappe.throw if the requested
			# record's school isn't in it
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return []
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None
	schools = frappe.get_all("User Permission", filters={"user": user, "allow": "School"}, pluck="for_value")
	return schools or None


def enforce_otp_attempts(key, limit=5, window=600):
	"""Throttle OTP verification to defeat brute-forcing of short numeric OTPs.

	Increments a per-key attempt counter; raises once `limit` is exceeded within
	`window` seconds. Call clear_otp_attempts(key) after a successful match.
	"""
	cache_key = f"otp_attempts:{key}"
	rs = frappe.cache()
	attempts = int(rs.get_value(cache_key) or 0)
	if attempts >= limit:
		frappe.throw(
			_("Too many incorrect attempts. Please request a new OTP."),
			frappe.ValidationError,
		)
	rs.set_value(cache_key, attempts + 1, expires_in_sec=window)


def clear_otp_attempts(key):
	frappe.cache().delete_value(f"otp_attempts:{key}")
