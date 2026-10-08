"""Fee dues for the /school app.

Dues are worked out the same way as the Fees Defaulter Report: every submitted Payment Request
raised against a student's Fees is one instalment, and it is due until its status is Paid. The
instalment's due date comes from the matching Payment Schedule row.

Class teachers see their own divisions (when School App Settings allows it); school admins see
every division in the schools they are permitted for. Nobody can change fees from the app.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from edu_quality.api.teacher import (
	_assert_division,
	_instructor,
	_is_admin,
	_my_divisions,
	_roll_key,
	_roster,
)
from edu_quality.edu_quality.server_scripts.utils import current_academic_year


def fees_visible_to_teachers():
	try:
		return bool(cint(frappe.get_cached_doc("School App Settings").show_fees_to_teachers))
	except frappe.DoesNotExistError:
		return False


def can_see_fees():
	return _is_admin() or (fees_visible_to_teachers() and bool(_fee_divisions()))


def _fee_divisions():
	"""Divisions whose fees the current user may see: all of them for admins, else those they class-teach."""
	if _is_admin():
		return _my_divisions()
	if not fees_visible_to_teachers():
		return []
	instructor = _instructor()
	if not instructor:
		return []
	return frappe.get_all(
		"Student Group Instructor",
		filters={"instructor": instructor, "parenttype": "Student Group"},
		pluck="parent",
		distinct=True,
	)


def _assert_fee_division(division):
	if division not in _fee_divisions():
		frappe.throw(_("You can't see fees for {0}.").format(division), frappe.PermissionError)
	return _assert_division(division)


def _instalments(students, academic_year):
	"""One row per Payment Request raised against these students' Fees for the year."""
	if not students:
		return []
	return frappe.db.sql(
		"""
		select f.student, pr.name as request, pr.payment_term, pr.grand_total as amount, pr.status,
			ps.due_date
		from `tabPayment Request` pr
		join `tabFees` f on pr.reference_doctype = 'Fees' and f.name = pr.reference_name
		left join `tabPayment Schedule` ps on ps.parent = f.name and ps.payment_term = pr.payment_term
		where pr.docstatus = 1 and f.docstatus = 1
			and f.student in %(students)s
			and f.academic_year = %(academic_year)s
		order by ps.due_date asc, pr.payment_term asc
		""",
		{"students": tuple(students), "academic_year": academic_year},
		as_dict=True,
	)


def _totals(rows, today):
	billed = sum(flt(r.amount) for r in rows)
	paid = sum(flt(r.amount) for r in rows if r.status == "Paid")
	unpaid = [r for r in rows if r.status != "Paid"]
	overdue = [r for r in unpaid if r.due_date and getdate(r.due_date) < today]
	upcoming = [r for r in unpaid if r.due_date and getdate(r.due_date) >= today]
	return {
		"billed": billed,
		"paid": paid,
		"outstanding": billed - paid,
		"overdue": sum(flt(r.amount) for r in overdue),
		"next_due_date": str(min(getdate(r.due_date) for r in upcoming)) if upcoming else None,
	}


def _currency():
	return frappe.db.get_default("currency") or "INR"


@frappe.whitelist(methods=["GET"])
def get_fee_overview():
	"""Per-division fee collection for the divisions the user may see."""
	divisions = _fee_divisions()
	if not divisions:
		if not _is_admin() and not fees_visible_to_teachers():
			frappe.throw(_("Fees aren't shown to teachers at this school."), frappe.PermissionError)
		return {"currency": _currency(), "divisions": []}

	today = getdate(nowdate())
	fallback_year = current_academic_year()
	groups = frappe.get_all(
		"Student Group",
		filters={"name": ["in", divisions], "disabled": 0},
		fields=["name", "student_group_name", "program", "academic_year"],
		order_by="program asc, student_group_name asc",
	)
	result = []
	for group in groups:
		roster = [s.student for s in _roster(group.name, group.program)]
		rows = _instalments(roster, group.academic_year or fallback_year)
		overdue_students = {
			r.student for r in rows if r.status != "Paid" and r.due_date and getdate(r.due_date) < today
		}
		result.append(
			{
				"name": group.name,
				"student_group_name": group.student_group_name,
				"program": group.program,
				"strength": len(roster),
				"defaulters": len(overdue_students),
				**_totals(rows, today),
			}
		)
	return {"currency": _currency(), "divisions": result}


@frappe.whitelist(methods=["GET"])
def get_division_fees(division):
	"""Each student's instalments for one division, with what is paid, due and overdue."""
	group = _assert_fee_division(division)
	today = getdate(nowdate())
	academic_year = group.academic_year or current_academic_year()
	students = sorted(_roster(division, group.program), key=_roll_key)
	rows = _instalments([s.student for s in students], academic_year)

	by_student = {}
	for row in rows:
		by_student.setdefault(row.student, []).append(row)

	result = []
	for student in students:
		mine = by_student.get(student.student, [])
		result.append(
			{
				"student": student.student,
				"student_name": student.student_name,
				"roll_no": student.roll_no,
				**_totals(mine, today),
				"instalments": [
					{
						"term": r.payment_term,
						"amount": flt(r.amount),
						"due_date": str(r.due_date) if r.due_date else None,
						"paid": r.status == "Paid",
						"overdue": r.status != "Paid" and bool(r.due_date) and getdate(r.due_date) < today,
					}
					for r in mine
				],
			}
		)

	return {
		"division": {
			"name": group.name,
			"student_group_name": group.student_group_name,
			"program": group.program,
		},
		"academic_year": academic_year,
		"currency": _currency(),
		**_totals(rows, today),
		"students": result,
	}
