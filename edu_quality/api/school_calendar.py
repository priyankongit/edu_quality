"""School events and holidays for the /school app.

Both live in the core Event doctype. A holiday is an Event with `custom_holiday` set (attendance
can't be marked on it, see student_attendance_sheet.get_holidays); everything else that is Public
is a school event. Every event belongs to one school (`custom_branch`) and applies to the classes in
its Event Class table; "all classes" fills that table with every class of the school (see
overrides/event.py). Competitions and talks set up through Event Detail add their department and type.

The Event override also rewrites the subject to "<prefix> - <title> - <classes>"; the app shows the
title alone and lists the classes separately.
"""

import html
import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, nowdate, strip_html

from edu_quality.api.teacher import _is_admin, _my_divisions


def _my_programs():
	divisions = _my_divisions()
	if not divisions:
		# A student sees their own class's calendar.
		from edu_quality.api.student_app import current_student

		student = current_student()
		return [student.enrollment.program] if student and student.enrollment else []
	return frappe.get_all(
		"Student Group", filters={"name": ["in", divisions]}, pluck="program", distinct=True
	)


def _programs(names):
	"""{program: {label, school, sequence}} for these Programs."""
	if not names:
		return {}
	return {
		p.name: p
		for p in frappe.get_all(
			"Program",
			filters={"name": ["in", list(names)]},
			fields=["name", "program_name as label", "school", "sequence"],
		)
	}


def _display_title(event, prefixes, labels):
	"""Undo the override's "<prefix> - <title> - <classes>" decoration."""
	title = event.subject or ""
	prefix = prefixes.get(event.custom_branch)
	if prefix and title.startswith(f"{prefix} - "):
		title = title[len(prefix) + 3 :]
	if " - " in title:
		base, tail = title.rsplit(" - ", 1)
		if tail == "All Classes" or (labels and set(tail.split(", ")) <= set(labels)):
			title = base
	return title.strip() or event.subject


def _event_row(event, classes, details, prefixes, programs):
	detail = details.get(event.name) or {}
	starts = get_datetime(event.starts_on)
	ends = get_datetime(event.ends_on) if event.ends_on else starts
	rows = sorted(
		(programs.get(c) or frappe._dict(label=c, sequence=0) for c in classes.get(event.name, [])),
		key=lambda p: cint(p.sequence),
	)
	labels = [p.label or p.name for p in rows]
	return {
		"name": event.name,
		"title": _display_title(event, prefixes, labels),
		"start": str(starts.date()),
		"end": str(ends.date()),
		"from_time": None if event.all_day else starts.strftime("%H:%M"),
		"to_time": None if event.all_day or not event.ends_on else ends.strftime("%H:%M"),
		"holiday": bool(event.custom_holiday),
		"description": html.unescape(strip_html(event.description or "")).strip(),
		"color": event.color,
		"all_classes": bool(event.all_classes),
		"classes": labels,
		"department": detail.get("department"),
		"kind": detail.get("event_type"),
	}


def _rows(events):
	names = [e.name for e in events] or [""]
	classes = {}
	for row in frappe.get_all(
		"Event Class",
		filters={"parent": ["in", names], "parenttype": "Event"},
		fields=["parent", "class"],
		order_by="idx asc",
	):
		classes.setdefault(row.parent, []).append(row["class"])
	details = {
		d.event: d
		for d in frappe.get_all(
			"Event Detail", filters={"event": ["in", names]}, fields=["event", "department", "event_type"]
		)
	}
	prefixes = dict(frappe.get_all("School", fields=["name", "prefix"], as_list=True))
	programs = _programs({c for cs in classes.values() for c in cs})
	return [_event_row(e, classes, details, prefixes, programs) for e in events]


@frappe.whitelist(methods=["GET"])
def get_calendar(from_date=None, to_date=None):
	"""Holidays and public events for the user's classes between two dates (default: the next 90 days)."""
	start = getdate(from_date or nowdate())
	end = getdate(to_date or add_days(start, 90))
	if end < start:
		frappe.throw(_("The end date is before the start date."))
	if (end - start).days > 400:
		frappe.throw(_("Pick a range of a year or less."))

	programs = _my_programs()
	schools = {p.school for p in _programs(programs).values() if p.school}
	events = frappe.db.sql(
		"""
		select e.name, e.subject, e.starts_on, e.ends_on, e.all_day, e.description, e.color,
			e.custom_holiday, e.all_classes, e.custom_branch
		from `tabEvent` e
		where (e.custom_holiday = 1 or e.event_type = 'Public')
			and e.starts_on <= %(end)s
			and coalesce(e.ends_on, e.starts_on) >= %(start)s
			and (
				exists (
					select 1 from `tabEvent Class` c
					where c.parent = e.name and c.parenttype = 'Event' and c.class in %(programs)s
				)
				or (e.all_classes = 1 and e.custom_branch in %(schools)s)
			)
		order by e.starts_on asc
		limit 500
		""",
		{
			"start": f"{start} 00:00:00",
			"end": f"{end} 23:59:59",
			"programs": tuple(programs) or ("",),
			"schools": tuple(schools) or ("",),
		},
		as_dict=True,
	)

	return {
		"from_date": str(start),
		"to_date": str(end),
		"can_create": _is_admin(),
		"events": _rows(events),
	}


@frappe.whitelist(methods=["GET"])
def get_event_form():
	"""Schools and classes an admin can post an event or holiday for."""
	if not _is_admin():
		frappe.throw(_("Only school admins can add events."), frappe.PermissionError)
	programs = sorted(
		_programs(_my_programs()).values(), key=lambda p: (p.school or "", cint(p.sequence), p.label or "")
	)
	return {
		"schools": sorted({p.school for p in programs if p.school}),
		"programs": [{"name": p.name, "label": p.label or p.name, "school": p.school} for p in programs],
	}


@frappe.whitelist(methods=["POST"])
def create_event(title, start, end=None, holiday=0, description=None, classes=None, school=None):
	"""Add a school event or holiday. `classes` is a list of Programs of one school; leave it empty
	(and name the `school`) for every class in the school."""
	if not _is_admin():
		frappe.throw(_("Only school admins can add events."), frappe.PermissionError)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the event a name."))
	start = getdate(start)
	end = getdate(end or start)
	if end < start:
		frappe.throw(_("The event ends before it starts."))

	classes = json.loads(classes) if isinstance(classes, str) else (classes or [])
	allowed = _programs(_my_programs())
	outside = set(classes) - set(allowed)
	if outside:
		frappe.throw(_("You can't add events for {0}.").format(", ".join(sorted(outside))))

	my_schools = {p.school for p in allowed.values() if p.school}
	if classes:
		picked = {allowed[c].school for c in classes}
		if len(picked) > 1:
			frappe.throw(_("Pick classes from one school at a time."))
		school = picked.pop()
	elif not school and len(my_schools) == 1:
		school = next(iter(my_schools))
	if not school or school not in my_schools:
		frappe.throw(_("Pick the school this is for."))
	if not frappe.db.exists("Branch", school):
		# Events are filed under a Branch named after the school (Event.custom_branch).
		frappe.throw(_("Add a Branch named {0} in the ERP before posting events for it.").format(school))

	doc = frappe.get_doc(
		{
			"doctype": "Event",
			"subject": title,
			"custom_branch": school,
			"starts_on": f"{start} 00:00:00",
			"ends_on": f"{end} 23:59:59",
			"all_day": 1,
			"event_type": "Public",
			"event_category": "Event",
			# Public events would otherwise go out in every user's daily event digest.
			"send_reminder": 0,
			"description": frappe.utils.escape_html(description or ""),
			"custom_holiday": cint(holiday),
			# The Event override fills in every class of the school for "all classes".
			"all_classes": 0 if classes else 1,
			"custom_classes": [
				{"class": program, "school": school, "all_divisions": 1} for program in classes
			],
		}
	)
	doc.insert()
	return _rows([doc])[0]
