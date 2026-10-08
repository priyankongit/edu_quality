"""Endpoints for the student experience of the /school app.

A student signs in with the User linked on their Student record and sees only their own data:
today's timetable, attendance, homework, fees, plus the school calendar and newsletters (which
school_calendar / school_newsletter scope to the student's class and school). Nothing here writes.

Students have no DocPerms on these doctypes, so every query below is filtered to the signed-in
student explicitly instead of relying on Frappe's permission engine.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_first_day, get_last_day, getdate, nowdate

from edu_quality.api.teacher import _hhmm, _is_holiday, _statuses
from edu_quality.edu_quality.server_scripts.utils import current_academic_year

ENROLLED_STATUSES = ("New student", "Current student", "Defaulter")


def student_app_enabled():
	try:
		return bool(cint(frappe.get_cached_doc("School App Settings").enable_student_app))
	except frappe.DoesNotExistError:
		return False


def current_student(user=None):
	"""The signed-in student's Student record and current enrollment, or None."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None
	student = frappe.db.get_value(
		"Student",
		{"user": user, "enabled": 1},
		["name", "student_name", "image", "reference_number", "student_status"],
		as_dict=True,
	)
	if not student:
		return None
	filters = {"student": student.name, "docstatus": 1, "custom_status": ["in", ENROLLED_STATUSES]}
	year = current_academic_year()
	enrollment = None
	if year:
		enrollment = frappe.db.get_value(
			"Program Enrollment",
			{**filters, "academic_year": year},
			["name", "program", "student_group", "academic_year", "custom_school", "roll_no"],
			as_dict=True,
		)
	if not enrollment:
		rows = frappe.get_all(
			"Program Enrollment",
			filters=filters,
			fields=["name", "program", "student_group", "academic_year", "custom_school", "roll_no"],
			order_by="enrollment_date desc",
			limit=1,
		)
		enrollment = rows[0] if rows else None
	student["enrollment"] = enrollment
	return student


def _require_student():
	student = current_student()
	if not student:
		frappe.throw(_("This account isn't linked to a student."), frappe.PermissionError)
	if not student.enrollment:
		frappe.throw(_("You aren't enrolled in a class yet. Please contact the school office."))
	if not student_app_enabled():
		frappe.throw(_("The student app is switched off at this school."), frappe.PermissionError)
	return student


def _division_label(division):
	return frappe.db.get_value("Student Group", division, "student_group_name") if division else None


def _attendance(student, start, end):
	"""Submitted attendance between two dates, with each status's type and colour."""
	statuses = {s.name: s for s in _statuses()}
	rows = frappe.get_all(
		"Attendance Entry",
		filters={"student": student, "docstatus": 1, "date": ["between", [start, end]]},
		fields=["date", "status"],
		order_by="date asc",
	)
	return [
		{
			"date": str(r.date),
			"status": r.status,
			"type": (statuses.get(r.status) or {}).get("type") or "Other",
			"code": (statuses.get(r.status) or {}).get("code") or (r.status or "")[:1],
			"color": (statuses.get(r.status) or {}).get("color"),
		}
		for r in rows
	]


def _attendance_totals(entries):
	present = sum(1 for e in entries if e["type"] != "Absent")
	absent = sum(1 for e in entries if e["type"] == "Absent")
	marked = present + absent
	return {
		"present": present,
		"absent": absent,
		"marked": marked,
		"percent": round(present * 100 / marked) if marked else None,
	}


def _year_bounds(academic_year):
	dates = frappe.db.get_value("Academic Year", academic_year, ["year_start_date", "year_end_date"])
	return dates if dates and dates[0] else (getdate(nowdate()).replace(month=1, day=1), getdate(nowdate()))


def _homework_row(doc, student):
	mine = next((r for r in doc.submissions if r.student == student), None)
	return {
		"name": doc.name,
		"title": doc.title,
		"subject": doc.subject,
		"subject_name": frappe.db.get_value("Course", doc.subject, "course_name") if doc.subject else None,
		"assigned_on": str(doc.assigned_on),
		"due_date": str(doc.due_date),
		"open": doc.status == "Open",
		"status": mine.status if mine else "Pending",
		"remarks": mine.remarks if mine else None,
		"teacher": frappe.db.get_value("Instructor", doc.teacher, "instructor_name") if doc.teacher else None,
		"instructions": doc.instructions,
		"attachment": doc.attachment,
	}


def _homework_rows(student, division, limit=100):
	names = frappe.get_all(
		"Homework",
		filters={"division": division},
		pluck="name",
		order_by="due_date desc, creation desc",
		limit=limit,
	)
	return [_homework_row(frappe.get_doc("Homework", name), student) for name in names]


def _fees(student, academic_year):
	from edu_quality.api.school_fees import _currency, _instalments, _totals

	today = getdate(nowdate())
	rows = _instalments([student], academic_year)
	return {
		"academic_year": academic_year,
		"currency": _currency(),
		**_totals(rows, today),
		"instalments": [
			{
				"term": r.payment_term,
				"amount": r.amount,
				"due_date": str(r.due_date) if r.due_date else None,
				"paid": r.status == "Paid",
				"overdue": r.status != "Paid" and bool(r.due_date) and getdate(r.due_date) < today,
			}
			for r in rows
		],
	}


# ---------------------------------------------------------------- endpoints


@frappe.whitelist(methods=["GET"])
def get_home():
	"""Everything the student's home screen shows."""
	student = _require_student()
	enrollment = student.enrollment
	today = getdate(nowdate())
	start, _end = _year_bounds(enrollment.academic_year)

	todays = _attendance(student.name, today, today)
	weekday = today.strftime("%A")
	periods = frappe.get_all(
		"Timetable",
		filters={"division": enrollment.student_group, "day": weekday},
		fields=["name", "subject", "subject.course_name as subject_name", "from_time", "to_time"],
		order_by="from_time asc",
	)
	for p in periods:
		p["from_time"] = _hhmm(p.from_time)
		p["to_time"] = _hhmm(p.to_time)

	homework = [h for h in _homework_rows(student.name, enrollment.student_group, limit=30) if h["open"]]
	due = [h for h in homework if h["due_date"] >= str(today) and h["status"] == "Pending"]
	fees = _fees(student.name, enrollment.academic_year)

	return {
		"student": {
			"name": student.name,
			"student_name": student.student_name,
			"image": student.image,
			"reference_number": student.reference_number,
			"roll_no": enrollment.roll_no,
			"division": enrollment.student_group,
			"division_name": _division_label(enrollment.student_group),
			"school": enrollment.custom_school,
			"academic_year": enrollment.academic_year,
		},
		"date": str(today),
		"weekday": weekday,
		"holiday": _is_holiday(enrollment.program, today),
		"today": todays[0] if todays else None,
		"attendance": _attendance_totals(_attendance(student.name, start, today)),
		"periods": periods,
		"homework_due": sorted(due, key=lambda h: h["due_date"])[:5],
		"fees": {k: fees[k] for k in ("currency", "outstanding", "overdue", "next_due_date", "billed")},
	}


@frappe.whitelist(methods=["GET"])
def get_attendance(month=None):
	"""One month of the student's attendance (`month` is YYYY-MM; default this month) plus year totals."""
	student = _require_student()
	enrollment = student.enrollment
	first = get_first_day(getdate(f"{month}-01") if month else getdate(nowdate()))
	last = get_last_day(first)
	start, _end = _year_bounds(enrollment.academic_year)
	today = getdate(nowdate())

	holidays = []
	day = first
	while day <= min(last, add_days(today, 60)):
		if _is_holiday(enrollment.program, day):
			holidays.append(str(day))
		day = add_days(day, 1)

	return {
		"month": str(first)[:7],
		"days": _attendance(student.name, first, last),
		"holidays": holidays,
		"statuses": _statuses(),
		"month_totals": _attendance_totals(_attendance(student.name, first, last)),
		"year_totals": _attendance_totals(_attendance(student.name, start, today)),
	}


@frappe.whitelist(methods=["GET"])
def get_homework():
	student = _require_student()
	return _homework_rows(student.name, student.enrollment.student_group)


@frappe.whitelist(methods=["GET"])
def get_homework_detail(name):
	student = _require_student()
	division = frappe.db.get_value("Homework", name, "division")
	if not division or division != student.enrollment.student_group:
		frappe.throw(_("This homework isn't for your class."), frappe.PermissionError)
	return _homework_row(frappe.get_doc("Homework", name), student.name)


@frappe.whitelist(methods=["GET"])
def get_fees():
	student = _require_student()
	return _fees(student.name, student.enrollment.academic_year)
