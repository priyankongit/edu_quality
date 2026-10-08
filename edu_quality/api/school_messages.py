"""Teacher ↔ parent messaging in the /school app, built on Frappe Raven.

Raven is optional. When it isn't installed every endpoint here says so and the app hides the
Messages tab. When it is, the app reads and writes Raven's own Raven Channel / Raven Message
documents, so conversations started here show up in Raven (and Raven's push notifications go out)
and vice versa.

Two kinds of conversation start from the app:
- a class channel per division: a private Raven channel with the division's teachers and every
  guardian who has a Raven account, remembered on Student Group.custom_raven_channel;
- a direct message with one guardian, created through Raven's own API so it is the same DM
  Raven itself would open.

People only join Raven when the office gives their user the "Raven User" role; anyone without it
is skipped and counted, so the teacher can see who still needs access.
"""

import html
import re

import frappe
from frappe import _
from frappe.utils import cint, escape_html, now_datetime

from edu_quality.api.teacher import _assert_division, _my_divisions, _roll_key, _roster

PAGE_SIZE = 50


def raven_installed():
	return "raven" in frappe.get_installed_apps()


def _require_raven():
	if not raven_installed():
		frappe.throw(_("Messaging needs the Raven app, which isn't installed on this site."))
	if not _raven_users([frappe.session.user]):
		frappe.throw(
			_("You don't have a Raven account yet. Ask the school office to give you the Raven User role.")
		)


def _raven_users(users):
	"""The subset of `users` who can use Raven."""
	users = [u for u in users if u]
	if not users:
		return set()
	filters = {"user": ["in", users]}
	if frappe.get_meta("Raven User").has_field("enabled"):
		filters["enabled"] = 1
	return set(frappe.get_all("Raven User", filters=filters, pluck="user"))


def _assert_member(channel):
	if not frappe.db.exists("Raven Channel Member", {"channel_id": channel, "user_id": frappe.session.user}):
		frappe.throw(_("You aren't in this conversation."), frappe.PermissionError)


def _people(users):
	if not users:
		return {}
	return {
		u.name: {"name": u.full_name or u.name, "image": u.user_image}
		for u in frappe.get_all(
			"User", filters={"name": ["in", list(users)]}, fields=["name", "full_name", "user_image"]
		)
	}


def _division_teachers(division):
	instructors = frappe.get_all(
		"Student Group Instructor",
		filters={"parent": division, "parenttype": "Student Group"},
		pluck="instructor",
	)
	if not instructors:
		return []
	employees = frappe.get_all("Instructor", filters={"name": ["in", instructors]}, pluck="employee")
	return frappe.get_all(
		"Employee", filters={"name": ["in", [e for e in employees if e] or [""]]}, pluck="user_id"
	)


def _guardians_of(students):
	"""[{guardian, guardian_name, user, student}] for these students' guardians."""
	if not students:
		return []
	return frappe.db.sql(
		"""
		select sg.parent as student, g.name as guardian, g.guardian_name, g.user
		from `tabStudent Guardian` sg
		join `tabGuardian` g on g.name = sg.guardian
		where sg.parenttype = 'Student' and sg.parent in %(students)s
		""",
		{"students": tuple(students)},
		as_dict=True,
	)


def _channel_slug(label):
	slug = re.sub(r"[^a-z0-9]+", "-", (label or "").lower()).strip("-")
	return f"{slug or 'class'}-parents"[:50]


def _default_workspace():
	"""Raven 2 files every channel under a workspace; earlier versions have no such field."""
	if not frappe.get_meta("Raven Channel").has_field("workspace"):
		return None
	mine = frappe.get_all(
		"Raven Workspace Member", filters={"user": frappe.session.user}, pluck="workspace", limit=1
	)
	if mine:
		return mine[0]
	first = frappe.get_all("Raven Workspace", pluck="name", order_by="creation asc", limit=1)
	return first[0] if first else None


def _add_members(channel, users):
	existing = set(frappe.get_all("Raven Channel Member", filters={"channel_id": channel}, pluck="user_id"))
	added = 0
	for user in users:
		if user in existing:
			continue
		member = frappe.get_doc({"doctype": "Raven Channel Member", "channel_id": channel, "user_id": user})
		# Access to the division was checked by the caller; guardians can't add themselves.
		member.flags.ignore_permissions = True
		member.insert()
		added += 1
	return added


def _insert_channel(values, group):
	"""Name the channel after the division, or after its unique ID when another school has the same name."""
	for label in (group.student_group_name, group.name):
		doc = frappe.get_doc({**values, "channel_name": _channel_slug(label)})
		# The teacher's access to the division was checked by the caller.
		doc.flags.ignore_permissions = True
		try:
			doc.insert()
			return doc.name
		except frappe.DuplicateEntryError:
			frappe.clear_last_message()
	frappe.throw(
		_("A Raven channel for {0} already exists. Ask the office to link it.").format(
			group.student_group_name
		)
	)


# ---------------------------------------------------------------- endpoints


@frappe.whitelist(methods=["GET"])
def get_conversations():
	"""The user's Raven conversations, newest first, with an unread count each, plus the class
	channels they could open for their divisions."""
	if not raven_installed():
		return {"enabled": False, "has_account": False, "conversations": [], "divisions": []}
	user = frappe.session.user
	has_account = bool(_raven_users([user]))
	my_divisions = _my_divisions() or [""]

	memberships = {
		m.channel_id: m
		for m in frappe.get_all(
			"Raven Channel Member", filters={"user_id": user}, fields=["channel_id", "last_visit"]
		)
	}
	channels = []
	if memberships:
		meta = frappe.get_meta("Raven Channel")
		fields = ["name", "channel_name", "type", "is_direct_message", "modified"]
		fields += [
			f for f in ("is_archived", "is_self_message", "last_message_timestamp") if meta.has_field(f)
		]
		channels = frappe.get_all("Raven Channel", filters={"name": ["in", list(memberships)]}, fields=fields)
		channels = [c for c in channels if not c.get("is_archived") and not c.get("is_self_message")]

	last = {}
	if channels:
		for row in frappe.db.sql(
			"""
			select m.channel_id, m.text, m.message_type, m.owner, m.creation
			from `tabRaven Message` m
			join (
				select channel_id, max(creation) as creation from `tabRaven Message`
				where channel_id in %(channels)s group by channel_id
			) latest on latest.channel_id = m.channel_id and latest.creation = m.creation
			""",
			{"channels": tuple(c.name for c in channels)},
			as_dict=True,
		):
			last[row.channel_id] = row

	# Other party of each DM: Raven names DM channels after both users.
	dm_users = {}
	for c in channels:
		if c.is_direct_message:
			others = frappe.get_all(
				"Raven Channel Member",
				filters={"channel_id": c.name, "user_id": ["!=", user]},
				pluck="user_id",
				limit=1,
			)
			dm_users[c.name] = others[0] if others else None
	people = _people({u for u in dm_users.values() if u} | {m.owner for m in last.values()})

	class_channels = {
		g.custom_raven_channel: g
		for g in frappe.get_all(
			"Student Group",
			filters={"name": ["in", my_divisions], "custom_raven_channel": ["is", "set"]},
			fields=["name", "student_group_name", "custom_raven_channel"],
		)
	}

	conversations = []
	for c in channels:
		message = last.get(c.name)
		visit = memberships[c.name].last_visit
		unread = 0
		if message and (not visit or message.creation > visit):
			unread = frappe.db.count(
				"Raven Message",
				{"channel_id": c.name, "owner": ["!=", user], "creation": [">", visit or "1900-01-01"]},
			)
		other = dm_users.get(c.name)
		division = class_channels.get(c.name)
		conversations.append(
			{
				"name": c.name,
				"title": (
					(people.get(other) or {}).get("name", other or "Direct message")
					if c.is_direct_message
					else (division.student_group_name + " parents" if division else c.channel_name)
				),
				"kind": "direct" if c.is_direct_message else ("class" if division else "channel"),
				"division": division.name if division else None,
				"image": (people.get(other) or {}).get("image") if c.is_direct_message else None,
				"last_message": _preview(message),
				"last_sender": (people.get(message.owner) or {}).get("name") if message else None,
				"last_at": str(message.creation)
				if message
				else str(c.get("last_message_timestamp") or c.modified),
				"unread": cint(unread),
			}
		)
	conversations.sort(key=lambda c: c["last_at"], reverse=True)

	opened = set(class_channels)
	divisions = [
		{"name": g.name, "student_group_name": g.student_group_name, "channel": g.custom_raven_channel}
		for g in frappe.get_all(
			"Student Group",
			filters={"name": ["in", my_divisions]},
			fields=["name", "student_group_name", "custom_raven_channel"],
			order_by="program asc, student_group_name asc",
		)
	]
	for d in divisions:
		# A channel someone deleted in Raven, or one the user left, has to be opened again.
		if d["channel"] not in opened or d["channel"] not in memberships:
			d["channel"] = None

	return {
		"enabled": True,
		"has_account": has_account,
		"conversations": conversations,
		"divisions": divisions,
	}


def _preview(message):
	if not message:
		return None
	if message.message_type == "Text":
		return html.unescape(frappe.utils.strip_html(message.text or "")).strip()[:140]
	return {"Image": "Photo", "File": "File", "Poll": "Poll"}.get(message.message_type, message.message_type)


@frappe.whitelist(methods=["POST"])
def open_class_channel(division):
	"""Create (or bring up to date) the private parents' channel for a division."""
	_require_raven()
	group = _assert_division(division)
	students = [s.student for s in _roster(division, group.program)]
	guardians = _guardians_of(students)
	wanted = {frappe.session.user, *_division_teachers(division), *(g.user for g in guardians)}
	on_raven = _raven_users(wanted)

	channel = frappe.db.get_value("Student Group", division, "custom_raven_channel")
	if not channel or not frappe.db.exists("Raven Channel", channel):
		values = {
			"doctype": "Raven Channel",
			"channel_description": _("Class updates for parents of {0}").format(group.student_group_name),
			"type": "Private",
		}
		workspace = _default_workspace()
		if workspace:
			values["workspace"] = workspace
		channel = _insert_channel(values, group)
		frappe.db.set_value("Student Group", division, "custom_raven_channel", channel, update_modified=False)

	added = _add_members(channel, sorted(on_raven))
	guardian_users = {g.user for g in guardians if g.user}
	return {
		"channel": channel,
		"added": added,
		"guardians_on_raven": len(guardian_users & on_raven),
		"guardians_missing": len({g.guardian for g in guardians if not g.user or g.user not in on_raven}),
	}


@frappe.whitelist(methods=["GET"])
def get_parent_contacts(division):
	"""Guardians in a division the teacher can message directly."""
	_require_raven()
	group = _assert_division(division)
	students = {s.student: s for s in _roster(division, group.program)}
	guardians = _guardians_of(list(students))
	on_raven = _raven_users([g.user for g in guardians])
	rows = [
		{
			"student": g.student,
			"student_name": students[g.student].student_name,
			"roll_no": students[g.student].roll_no,
			"guardian": g.guardian,
			"guardian_name": g.guardian_name,
			"on_raven": g.user in on_raven,
		}
		for g in guardians
	]
	return sorted(rows, key=lambda r: (_roll_key(r), r["guardian_name"] or ""))


@frappe.whitelist(methods=["POST"])
def open_direct_message(guardian, division):
	"""Open (or create) Raven's DM with one guardian of a student in the teacher's division."""
	_require_raven()
	group = _assert_division(division)
	students = [s.student for s in _roster(division, group.program)]
	match = [g for g in _guardians_of(students) if g.guardian == guardian]
	if not match:
		frappe.throw(_("That parent isn't linked to a student in {0}.").format(group.student_group_name))
	user = match[0].user
	if not user or not _raven_users([user]):
		frappe.throw(_("{0} isn't on Raven yet.").format(match[0].guardian_name))

	for path in (
		"raven.api.raven_channel.create_direct_message_channel",
		"raven.raven_channel_management.doctype.raven_channel.raven_channel.create_direct_message_channel",
	):
		try:
			create = frappe.get_attr(path)
		except (AttributeError, ImportError):
			continue
		return {"channel": create(user)}
	frappe.throw(_("This version of Raven can't open direct messages from the school app."))


@frappe.whitelist(methods=["GET"])
def get_messages(channel, before=None):
	"""A page of messages in a conversation, oldest first. Opening it marks it read."""
	_require_raven()
	_assert_member(channel)
	filters = {"channel_id": channel}
	if before:
		filters["creation"] = ["<", before]
	rows = frappe.get_all(
		"Raven Message",
		filters=filters,
		fields=["name", "owner", "text", "message_type", "file", "creation"],
		order_by="creation desc",
		limit=PAGE_SIZE + 1,
	)
	has_more = len(rows) > PAGE_SIZE
	rows = list(reversed(rows[:PAGE_SIZE]))
	people = _people({r.owner for r in rows})

	if not before:
		frappe.db.set_value(
			"Raven Channel Member",
			{"channel_id": channel, "user_id": frappe.session.user},
			"last_visit",
			now_datetime(),
			update_modified=False,
		)

	return {
		"has_more": has_more,
		"messages": [
			{
				"name": r.name,
				"sender": r.owner,
				"sender_name": (people.get(r.owner) or {}).get("name", r.owner),
				"sender_image": (people.get(r.owner) or {}).get("image"),
				"mine": r.owner == frappe.session.user,
				"type": r.message_type,
				"text": r.text if r.message_type == "Text" else None,
				"file": r.file,
				"at": str(r.creation),
			}
			for r in rows
		],
	}


@frappe.whitelist(methods=["POST"])
def send_message(channel, text):
	_require_raven()
	_assert_member(channel)
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Write a message first."))
	if len(text) > 4000:
		frappe.throw(_("That message is too long. Keep it under 4,000 characters."))

	# Raven stores messages as HTML from its editor.
	html = "".join(f"<p>{escape_html(line)}</p>" if line else "<p></p>" for line in text.split("\n"))
	doc = frappe.get_doc(
		{"doctype": "Raven Message", "channel_id": channel, "text": html, "message_type": "Text"}
	)
	# Membership was checked above; Raven's own hooks still send the realtime update and push alerts.
	doc.flags.ignore_permissions = True
	doc.insert()
	frappe.db.set_value(
		"Raven Channel Member",
		{"channel_id": channel, "user_id": frappe.session.user},
		"last_visit",
		now_datetime(),
		update_modified=False,
	)
	return {"name": doc.name, "at": str(doc.creation)}
