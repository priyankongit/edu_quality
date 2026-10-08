"""Endpoints for the teacher experience of the /school app.

Every endpoint works on the signed-in user's own divisions: those where they are listed as
an instructor on the Student Group, or assigned through CMAP Assignment. School admins can
open every division in the schools they are permitted for.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from edu_quality.common.utils.access import ADMIN_ROLES, get_user_schools
from edu_quality.edu_quality.doctype.student_attendance_sheet.student_attendance_sheet import get_holidays

# Everyone who should be in class. New admissions stay "New student" until they are rolled
# over, so they must be on the register too.
ENROLLED_STATUSES = ("New student", "Current student", "Defaulter")


# ---------------------------------------------------------------- access


def _instructor():
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		return None
	return frappe.db.get_value("Instructor", {"employee": employee, "status": "Active"}, "name")


def _is_admin():
	return bool(set(frappe.get_roles()) & ADMIN_ROLES)


def _my_divisions():
	"""Names of the Student Groups the current user may take attendance for."""
	instructor = _instructor()
	names = set()
	if instructor:
		names.update(
			frappe.get_all(
				"Student Group Instructor",
				filters={"instructor": instructor, "parenttype": "Student Group"},
				pluck="parent",
			)
		)
		names.update(frappe.get_all("CMAP Assignment", filters={"teacher": instructor}, pluck="division"))

	filters = {"disabled": 0}
	if _is_admin():
		schools = get_user_schools()
		if schools is not None:
			filters["custom_school"] = ["in", schools]
	elif not names:
		return []
	else:
		filters["name"] = ["in", list(names)]

	return frappe.get_all("Student Group", filters=filters, pluck="name")


def _assert_division(division):
	if division not in _my_divisions():
		frappe.throw(_("You are not assigned to {0}.").format(division), frappe.PermissionError)
	return frappe.db.get_value(
		"Student Group",
		division,
		["name", "student_group_name", "program", "custom_school as school", "academic_year"],
		as_dict=True,
	)


def _hhmm(value):
	"""Frappe returns Time fields as timedelta; show them as 08:40."""
	if not value:
		return ""
	minutes = int(value.total_seconds()) // 60 if hasattr(value, "total_seconds") else None
	if minutes is None:
		return str(value)[:5]
	return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _parse_date(date):
	date = getdate(date or nowdate())
	if date > getdate(nowdate()):
		frappe.throw(_("Attendance can't be marked for a future date."))
	return date


# ---------------------------------------------------------------- data helpers


def _roster(division, program):
	return frappe.get_all(
		"Program Enrollment",
		filters={
			"student_group": division,
			"program": program,
			"docstatus": 1,
			"custom_status": ["in", ENROLLED_STATUSES],
		},
		fields=["student", "student_name", "roll_no", "student.image as image"],
		order_by="roll_no asc",
	)


def _roll_key(row):
	roll = row.get("roll_no") or ""
	return (0, int(roll), "") if str(roll).isdigit() else (1, 0, str(roll))


def _is_holiday(program, date):
	return date in get_holidays(date, date, program, True)


def _statuses():
	return frappe.get_all(
		"Attendance Status",
		fields=["name", "type", "code", "color"],
		order_by="creation asc",
	)


def _attendance_summary(division, date, strength):
	rows = frappe.get_all(
		"Attendance Entry",
		filters={"division": division, "date": date, "docstatus": ["<", 2]},
		fields=["status", "docstatus"],
	)
	types = {s.name: s.type for s in _statuses()}
	marked = [r for r in rows if r.status]
	return {
		"strength": strength,
		"marked": len(marked),
		"present": sum(1 for r in marked if types.get(r.status) != "Absent"),
		"absent": sum(1 for r in marked if types.get(r.status) == "Absent"),
		"submitted": bool(rows) and all(r.docstatus == 1 for r in rows),
	}


# ---------------------------------------------------------------- endpoints


@frappe.whitelist(methods=["GET"])
def get_my_day(date=None):
	"""Divisions, today's timetable and attendance progress for the home screen."""
	date = getdate(date or nowdate())
	weekday = date.strftime("%A")
	divisions = _my_divisions()

	groups = frappe.get_all(
		"Student Group",
		filters={"name": ["in", divisions or [""]]},
		fields=["name", "student_group_name", "program", "custom_school as school"],
		order_by="program asc, student_group_name asc",
	)
	result = []
	for group in groups:
		strength = len(_roster(group.name, group.program))
		result.append(
			{
				**group,
				"holiday": _is_holiday(group.program, date),
				"attendance": _attendance_summary(group.name, date, strength),
			}
		)

	periods = frappe.get_all(
		"Timetable",
		filters={"division": ["in", divisions or [""]], "day": weekday},
		fields=["name", "division", "subject", "subject.course_name as subject_name", "from_time", "to_time", "type"],
		order_by="from_time asc",
	)
	labels = {g.name: g.student_group_name for g in groups}
	for period in periods:
		period["division_name"] = labels.get(period.division, period.division)
		period["from_time"] = _hhmm(period.from_time)
		period["to_time"] = _hhmm(period.to_time)

	return {"date": str(date), "weekday": weekday, "divisions": result, "periods": periods}


@frappe.whitelist(methods=["GET"])
def get_register(division, date=None):
	"""Roster for one division on one day, with any attendance already recorded."""
	group = _assert_division(division)
	date = _parse_date(date)

	students = sorted(_roster(division, group.program), key=_roll_key)
	entries = {
		e.student: e
		for e in frappe.get_all(
			"Attendance Entry",
			filters={"division": division, "date": date, "docstatus": ["<", 2]},
			fields=["name", "student", "status", "docstatus"],
		)
	}
	for student in students:
		entry = entries.get(student.student)
		student["status"] = entry.status if entry else None
		student["locked"] = bool(entry and entry.docstatus == 1)

	return {
		"division": group,
		"date": str(date),
		"holiday": _is_holiday(group.program, date),
		"statuses": _statuses(),
		"students": students,
		"submitted": bool(students) and all(s["locked"] for s in students),
	}


@frappe.whitelist(methods=["POST"])
def save_register(division, date, marks, submit=0):
	"""Save (and optionally submit) attendance for a division.

	`marks` maps student ID to an Attendance Status name. Submitted entries are left as they are.
	"""
	group = _assert_division(division)
	date = _parse_date(date)
	marks = json.loads(marks) if isinstance(marks, str) else (marks or {})
	submit = cint(submit)

	valid_statuses = {s.name: s.type for s in _statuses()}
	roster = {s.student for s in _roster(division, group.program)}

	unknown = set(marks) - roster
	if unknown:
		frappe.throw(_("{0} is not enrolled in {1}.").format(", ".join(sorted(unknown)), division))
	bad = {status for status in marks.values() if status not in valid_statuses}
	if bad:
		frappe.throw(_("Unknown attendance status: {0}").format(", ".join(sorted(bad))))
	if submit:
		locked = set(
			frappe.get_all(
				"Attendance Entry", filters={"division": division, "date": date, "docstatus": 1}, pluck="student"
			)
		)
		if roster - locked - set(marks):
			frappe.throw(_("Mark every student before submitting."))

	absent = []
	for student, status in marks.items():
		name = frappe.db.get_value(
			"Attendance Entry", {"student": student, "date": date, "docstatus": ["<", 2]}, "name"
		)
		doc = frappe.get_doc("Attendance Entry", name) if name else frappe.new_doc("Attendance Entry")
		if doc.docstatus == 1:
			continue
		doc.update(
			{"student": student, "date": date, "status": status, "class": group.program, "division": division}
		)
		# Teachers have no Attendance Entry DocPerm; access was checked per division above.
		doc.flags.ignore_permissions = True
		doc.save()
		if submit:
			doc.submit()
			if valid_statuses[status] == "Absent":
				absent.append(student)

	# Parents hear about an absence once, when the register is submitted (it can't change after).
	if absent:
		frappe.enqueue(
			"edu_quality.api.teacher.notify_guardians_of_absence",
			students=absent,
			date=str(date),
			enqueue_after_commit=True,
		)

	return {
		"attendance": _attendance_summary(division, date, len(roster)),
		"notified": len(absent),
	}


def notify_guardians_of_absence(students, date):
	"""Push an absence alert to each guardian with the parent app installed."""
	settings = frappe.get_cached_doc("School App Settings")
	if not cint(settings.notify_parents_of_absence):
		return
	if not frappe.db.table_exists("Mobile Push Token"):
		return

	from edu_quality.public.py.walsh.admin import notification_sender

	when = getdate(date).strftime("%d %b")
	for student in students:
		guardians = frappe.get_all(
			"Student Guardian", filters={"parent": student, "parenttype": "Student"}, pluck="guardian"
		)
		for guardian in guardians:
			user = frappe.db.get_value("Guardian", guardian, "user")
			if not user:
				continue
			try:
				notification_sender(user, student, subject=f"Marked absent on {when}", url_path="/attendance")
			except Exception:
				frappe.log_error(title="Absence push notification failed", message=frappe.get_traceback())


# ---------------------------------------------------------------- homework

HOMEWORK_STATUSES = ("Pending", "Submitted", "Reviewed")


def _division_subjects(division, program):
	"""Subjects taught in a division: its timetable first, then the class's program courses."""
	names = frappe.get_all("Timetable", filters={"division": division}, pluck="subject", distinct=True)
	names += frappe.get_all(
		"Program Course", filters={"parent": program, "parenttype": "Program"}, pluck="course"
	)
	seen, subjects = set(), []
	for name in names:
		if name and name not in seen:
			seen.add(name)
			subjects.append({"name": name, "label": frappe.db.get_value("Course", name, "course_name") or name})
	return subjects


def _homework_summary(doc):
	rows = doc.get("submissions") or []
	return {
		"name": doc.name,
		"title": doc.title,
		"division": doc.division,
		"division_name": frappe.db.get_value("Student Group", doc.division, "student_group_name"),
		"subject": doc.subject,
		"subject_name": frappe.db.get_value("Course", doc.subject, "course_name") if doc.subject else None,
		"assigned_on": str(doc.assigned_on),
		"due_date": str(doc.due_date),
		"status": doc.status,
		"total": len(rows),
		"submitted": sum(1 for r in rows if r.status in ("Submitted", "Reviewed")),
		"reviewed": sum(1 for r in rows if r.status == "Reviewed"),
	}


def _get_homework(name):
	doc = frappe.get_doc("Homework", name)
	_assert_division(doc.division)
	return doc


@frappe.whitelist(methods=["GET"])
def get_homework_list():
	divisions = _my_divisions()
	names = frappe.get_all(
		"Homework",
		filters={"division": ["in", divisions or [""]]},
		pluck="name",
		order_by="due_date desc, creation desc",
		limit=100,
	)
	return [_homework_summary(frappe.get_doc("Homework", name)) for name in names]


@frappe.whitelist(methods=["GET"])
def get_homework_form(division, date=None):
	"""Subjects for the division plus any homework planned in CMAP for that day."""
	group = _assert_division(division)
	date = getdate(date or nowdate())
	suggestions = frappe.db.sql(
		"""
		select c.name as cmap, c.subject, c.home_work
		from `tabCMAP` c
		join `tabCMAP Assignment` a on a.parent = c.name and a.parenttype = 'CMAP'
		where a.division = %(division)s and a.real_date = %(date)s
			and ifnull(c.home_work, '') != ''
		order by c.subject
		""",
		{"division": division, "date": date},
		as_dict=True,
	)
	for row in suggestions:
		row["subject_name"] = frappe.db.get_value("Course", row.subject, "course_name") if row.subject else None
	return {"subjects": _division_subjects(division, group.program), "suggestions": suggestions}


@frappe.whitelist(methods=["POST"])
def create_homework(division, title, due_date, subject=None, instructions=None, cmap=None):
	group = _assert_division(division)
	if not (title or "").strip():
		frappe.throw(_("Give the homework a title."))
	if getdate(due_date) < getdate(nowdate()):
		frappe.throw(_("The due date has already passed."))

	doc = frappe.get_doc(
		{
			"doctype": "Homework",
			"title": title.strip(),
			"division": division,
			"subject": subject or None,
			"instructions": instructions or "",
			"assigned_on": nowdate(),
			"due_date": due_date,
			"cmap": cmap or None,
			"teacher": _instructor(),
			"submissions": [
				{"student": s.student, "student_name": s.student_name, "status": "Pending"}
				for s in sorted(_roster(division, group.program), key=_roll_key)
			],
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return _homework_summary(doc)


@frappe.whitelist(methods=["GET"])
def get_homework(name):
	doc = _get_homework(name)
	rolls = {s.student: s.roll_no for s in _roster(doc.division, doc.program)}
	return {
		**_homework_summary(doc),
		"instructions": doc.instructions,
		"attachment": doc.attachment,
		"submissions": [
			{
				"student": r.student,
				"student_name": r.student_name,
				"roll_no": rolls.get(r.student),
				"status": r.status,
				"remarks": r.remarks,
			}
			for r in doc.submissions
		],
	}


@frappe.whitelist(methods=["POST"])
def update_homework(name, updates=None, status=None):
	"""`updates` maps student ID to {"status": ..., "remarks": ...}."""
	doc = _get_homework(name)
	updates = json.loads(updates) if isinstance(updates, str) else (updates or {})
	rows = {r.student: r for r in doc.submissions}

	for student, change in updates.items():
		row = rows.get(student)
		if not row:
			frappe.throw(_("{0} isn't on this homework's list.").format(student))
		new_status = change.get("status", row.status)
		if new_status not in HOMEWORK_STATUSES:
			frappe.throw(_("Unknown homework status: {0}").format(new_status))
		if new_status == "Reviewed" and row.status != "Reviewed":
			row.reviewed_on = frappe.utils.now_datetime()
		row.status = new_status
		if "remarks" in change:
			row.remarks = change.get("remarks") or ""

	if status in ("Open", "Closed"):
		doc.status = status

	doc.flags.ignore_permissions = True
	doc.save()
	return _homework_summary(doc)


# ---------------------------------------------------------------- marks
#
# Teachers enter marks for plain criteria-scored exams. Descriptive papers, KG exams, remarks and
# composite groups keep using the desk Marks Entry Tool. Marks are saved as draft Assessment
# Results; the exam office processes and submits them, after which they are read-only here.


def _markable_plans(divisions, plan=None):
	if not divisions:
		return []
	return frappe.db.sql(
		"""
		select p.name, p.assessment_name, p.assessment_group, g.assessment_group_name,
			p.student_group as division, p.program, p.course as subject, c.course_name as subject_name,
			p.schedule_date, p.maximum_assessment_score as maximum_score, p.grading_scale,
			p.custom_scoring_type as scoring_type, p.custom_type as exam_type, p.examiner
		from `tabAssessment Plan` p
		join `tabAssessment Group` g on g.name = p.assessment_group
		left join `tabCourse` c on c.name = p.course
		where p.docstatus = 1 and p.student_group in %(divisions)s
			and p.custom_scoring_type in ('Marks', 'Grades')
			and ifnull(p.custom_is_descriptive, 0) = 0
			and g.is_group = 0
			and ifnull(g.custom_is_kg_exam, 0) = 0
			and ifnull(g.custom_is_composite, 0) = 0
			and (%(plan)s is null or p.name = %(plan)s)
		order by p.schedule_date desc, g.assessment_group_name, c.course_name
		limit 300
		""",
		{"divisions": tuple(divisions), "plan": plan},
		as_dict=True,
	)


def _exam_summaries(plans):
	counts = {}
	if plans:
		for row in frappe.db.sql(
			"""
			select assessment_plan, count(*) as entered, sum(docstatus = 1) as submitted
			from `tabAssessment Result`
			where assessment_plan in %(plans)s and docstatus < 2
			group by assessment_plan
			""",
			{"plans": tuple(p.name for p in plans)},
			as_dict=True,
		):
			counts[row.assessment_plan] = row

	instructor = _instructor()
	divisions, result = {}, []
	for plan in plans:
		if plan.division not in divisions:
			divisions[plan.division] = {
				"name": frappe.db.get_value("Student Group", plan.division, "student_group_name"),
				"strength": len(_roster(plan.division, plan.program)),
			}
		count = counts.get(plan.name) or {}
		result.append(
			{
				**plan,
				"schedule_date": str(plan.schedule_date) if plan.schedule_date else None,
				"division_name": divisions[plan.division]["name"],
				"strength": divisions[plan.division]["strength"],
				"entered": cint(count.get("entered")),
				"submitted": cint(count.get("submitted")),
				"mine": bool(instructor and plan.examiner == instructor),
			}
		)
	return result


def _get_markable_plan(name):
	plan = frappe.db.get_value("Assessment Plan", name, ["name", "student_group"], as_dict=True)
	if not plan:
		frappe.throw(_("Exam {0} not found.").format(name), frappe.DoesNotExistError)
	_assert_division(plan.student_group)
	rows = _markable_plans([plan.student_group], plan=name)
	if not rows:
		frappe.throw(_("Marks for this exam are entered on the desk, not in the app."))
	return rows[0]


def _plan_criteria(plan):
	return frappe.get_all(
		"Assessment Plan Criteria",
		filters={"parent": plan, "parenttype": "Assessment Plan"},
		fields=["assessment_criteria", "maximum_score", "custom_scale"],
		order_by="idx asc",
	)


def _grades(grading_scale):
	return frappe.get_all(
		"Grading Scale Interval",
		filters={"parent": grading_scale, "parenttype": "Grading Scale"},
		fields=["grade_code as code", "grade_description as description"],
		order_by="threshold desc",
	)


@frappe.whitelist(methods=["GET"])
def get_exam_list():
	"""Exams in the teacher's divisions that take marks in the app, with how far entry has got."""
	return _exam_summaries(_markable_plans(_my_divisions()))


@frappe.whitelist(methods=["GET"])
def get_marks_sheet(plan):
	"""Roster for one exam with each student's marks (or grades) per criterion.

	A value is a number of marks, a grade code, "-" for absent, or missing if not entered yet.
	"""
	row = _get_markable_plan(plan)
	results = frappe.get_all(
		"Assessment Result",
		filters={"assessment_plan": plan, "docstatus": ["<", 2]},
		fields=["name", "student", "docstatus"],
	)
	by_result = {r.name: r for r in results}
	values = {}
	for d in frappe.get_all(
		"Assessment Result Detail",
		filters={"parent": ["in", list(by_result) or [""]], "parenttype": "Assessment Result"},
		fields=["parent", "assessment_criteria", "score", "grade", "custom_is_absent"],
	):
		if d.custom_is_absent:
			value = "-"
		elif row.scoring_type == "Grades":
			value = d.grade or ""
		else:
			value = d.score
		values.setdefault(by_result[d.parent].student, {})[d.assessment_criteria] = value

	locked = {r.student for r in results if r.docstatus == 1}
	students = sorted(_roster(row.division, row.program), key=_roll_key)
	return {
		**_exam_summaries([row])[0],
		"criteria": [
			{"name": c.assessment_criteria, "maximum_score": c.maximum_score} for c in _plan_criteria(plan)
		],
		"grades": _grades(row.grading_scale) if row.scoring_type == "Grades" else [],
		"students": [
			{
				"student": s.student,
				"student_name": s.student_name,
				"roll_no": s.roll_no,
				"locked": s.student in locked,
				"values": values.get(s.student, {}),
			}
			for s in students
		],
	}


@frappe.whitelist(methods=["POST"])
def save_marks(plan, marks):
	"""Save marks as draft Assessment Results.

	`marks` maps student ID to {criteria: value}; a value is marks, a grade code, "-" for absent,
	or "" to clear it. Results the exam office has already submitted are left as they are.
	"""
	from edu_quality.edu_quality.report.marks_entry_tool.marks_entry_tool import (
		add_assessment_criteria,
		get_assessment_result_doc,
	)

	row = _get_markable_plan(plan)
	marks = json.loads(marks) if isinstance(marks, str) else (marks or {})
	criteria = {c.assessment_criteria: c for c in _plan_criteria(plan)}
	grades = {g.code.upper(): g.code for g in _grades(row.grading_scale)} if row.scoring_type == "Grades" else {}
	roster = {s.student: s.student_name for s in _roster(row.division, row.program)}

	# Check everything before writing anything.
	clean = {}
	for student, entries in marks.items():
		if student not in roster:
			frappe.throw(_("{0} is not enrolled in {1}.").format(student, row.division))
		clean[student] = {}
		for name, value in (entries or {}).items():
			if name not in criteria:
				frappe.throw(_("{0} is not part of this exam.").format(name))
			value = "" if value is None else str(value).strip()
			if value in ("", "-"):
				pass
			elif row.scoring_type == "Grades":
				if value.upper() not in grades:
					frappe.throw(_("{0}: {1} is not a grade on this exam's scale.").format(roster[student], value))
				value = grades[value.upper()]
			else:
				try:
					score = float(value)
				except ValueError:
					frappe.throw(_("{0}: {1} is not a number.").format(roster[student], value))
				maximum = criteria[name].maximum_score or 0
				if score < 0 or score > maximum:
					frappe.throw(
						_("{0}: {1} marks is outside 0–{2:g} for {3}.").format(roster[student], value, maximum, name)
					)
			clean[student][name] = value

	saved = skipped = 0
	for student, entries in clean.items():
		if not entries:
			continue
		doc = get_assessment_result_doc(student, plan)
		if doc is None:  # already submitted by the exam office
			skipped += 1
			continue

		details = list(doc.details)
		for name, value in entries.items():
			if value == "":
				details = [d for d in details if d.get("assessment_criteria") != name]
				continue
			add_assessment_criteria(
				details,
				{
					"assessment_criteria": {
						"name": name,
						"value": value,
						"scoring_type": row.scoring_type,
						"custom_scale": criteria[name].custom_scale,
						"custom_online_assessment": 0,
					}
				},
				None,
			)

		# Teachers have no Assessment Result DocPerm; access was checked per division above.
		if not details:
			if not doc.is_new():
				frappe.delete_doc("Assessment Result", doc.name, ignore_permissions=True)
				saved += 1
			continue
		doc.update({"student": student, "assessment_plan": plan, "custom_is_descriptive": 0, "details": details})
		doc.flags.ignore_permissions = True
		doc.save()
		saved += 1

	return {**_exam_summaries([row])[0], "saved": saved, "skipped": skipped}
