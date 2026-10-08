"""School newsletters in the /school app, built on Frappe's Newsletter doctype.

Staff and students can read newsletters that have gone out; a newsletter with a PDF attached is
also shown page by page in the app (pages are rendered to images on the server, so it works on every
phone without a PDF viewer); admins can also write one and send it to email
groups (such as All Parents) from the app. Newsletter.custom_school keeps branches apart: a
newsletter tagged with a school is only shown to that school's staff, an untagged one to all.
"""

import html
import json

import frappe
from frappe import _
from frappe.utils import cint, escape_html, strip_html
from frappe.utils.html_utils import sanitize_html
from werkzeug.wrappers import Response

from edu_quality.api.teacher import _is_admin
from edu_quality.common.utils.access import get_user_schools


def _my_schools():
	"""Schools whose newsletters the user may read, or None for every school."""
	if _is_admin():
		return get_user_schools()
	school = frappe.db.get_value(
		"Instructor",
		{
			"employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name") or "",
			"status": "Active",
		},
		"custom_school",
	)
	if not school:
		from edu_quality.api.student_app import current_student

		student = current_student()
		school = student and student.enrollment and student.enrollment.custom_school
	return [school] if school else []


def _school_condition(schools):
	if schools is None:
		return "", {}
	return "and (ifnull(n.custom_school, '') = '' or n.custom_school in %(schools)s)", {
		"schools": tuple(schools) or ("",)
	}


def _sent_at_column():
	return "n.email_sent_at" if frappe.get_meta("Newsletter").has_field("email_sent_at") else "n.modified"


def _body_html(doc):
	if doc.content_type == "Markdown":
		body = frappe.utils.md_to_html(doc.message_md or "")
	elif doc.content_type == "HTML":
		body = doc.message_html or ""
	else:
		body = doc.message or ""
	return sanitize_html(body)


@frappe.whitelist(methods=["GET"])
def get_newsletters():
	"""Newsletters that have gone out, newest first."""
	condition, values = _school_condition(_my_schools())
	rows = frappe.db.sql(
		f"""
		select n.name, n.subject, n.sender_name, {_sent_at_column()} as sent_at,
			n.content_type, n.message, n.message_md, n.message_html, n.custom_school as school
		from `tabNewsletter` n
		where n.email_sent = 1 {condition}
		order by sent_at desc
		limit 100
		""",
		values,
		as_dict=True,
	)
	return {
		"can_write": _is_admin(),
		"newsletters": [
			{
				"name": r.name,
				"subject": r.subject,
				"sender_name": r.sender_name,
				"sent_at": str(r.sent_at) if r.sent_at else None,
				"school": r.school,
				"preview": html.unescape(strip_html(_body_html(r))).strip()[:200],
			}
			for r in rows
		],
	}


def _get_readable(name):
	schools = _my_schools()
	doc = frappe.get_doc("Newsletter", name)
	if not doc.email_sent:
		frappe.throw(_("This newsletter hasn't gone out yet."), frappe.PermissionError)
	if schools is not None and doc.get("custom_school") and doc.custom_school not in schools:
		frappe.throw(_("This newsletter is for another school."), frappe.PermissionError)
	return doc


@frappe.whitelist(methods=["GET"])
def get_newsletter(name):
	doc = _get_readable(name)
	return {
		"name": doc.name,
		"subject": doc.subject,
		"sender_name": doc.sender_name,
		"sent_at": str(doc.get("email_sent_at") or doc.modified),
		"school": doc.get("custom_school"),
		"recipients": [r.email_group for r in doc.email_group],
		"total_recipients": cint(doc.get("total_recipients")),
		"html": _body_html(doc),
		"pdf": _pdf_info(doc.name),
	}


# ---------------------------------------------------------------- PDF pages

PAGE_CACHE_SECONDS = 24 * 60 * 60
PAGE_SCALE = 2  # 540pt-wide pages come out ~1080px: sharp on phones, still small on the wire


def _pdf_file(newsletter):
	"""The PDF attached to a newsletter, if any."""
	rows = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Newsletter",
			"attached_to_name": newsletter,
			"file_name": ["like", "%.pdf"],
		},
		fields=["name", "file_url", "modified"],
		order_by="creation asc",
		limit=1,
	)
	return rows[0] if rows else None


def _open_pdf(file_row):
	import fitz

	return fitz.open(frappe.get_doc("File", file_row.name).get_full_path())


def _pdf_info(newsletter):
	file_row = _pdf_file(newsletter)
	if not file_row:
		return None
	key = f"newsletter_pdf_info:{newsletter}:{file_row.modified}"
	info = frappe.cache().get_value(key)
	if not info:
		pdf = _open_pdf(file_row)
		info = {
			"url": file_row.file_url,
			"pages": [{"width": round(p.rect.width), "height": round(p.rect.height)} for p in pdf],
		}
		frappe.cache().set_value(key, info, expires_in_sec=PAGE_CACHE_SECONDS)
	return info


@frappe.whitelist(methods=["GET"])
def get_newsletter_page(name, page):
	"""One page of a newsletter's PDF as a JPEG (pages count from 1)."""
	_get_readable(name)
	file_row = _pdf_file(name)
	if not file_row:
		frappe.throw(_("This newsletter has no PDF."), frappe.DoesNotExistError)
	page = cint(page)
	key = f"newsletter_pdf_page:{name}:{file_row.modified}:{page}"
	image = frappe.cache().get_value(key)
	if image is None:
		import fitz

		pdf = _open_pdf(file_row)
		if page < 1 or page > pdf.page_count:
			frappe.throw(_("Page {0} doesn't exist.").format(page), frappe.DoesNotExistError)
		pixmap = pdf[page - 1].get_pixmap(matrix=fitz.Matrix(PAGE_SCALE, PAGE_SCALE))
		image = pixmap.tobytes("jpg", jpg_quality=75)
		frappe.cache().set_value(key, image, expires_in_sec=PAGE_CACHE_SECONDS)

	response = Response(image, mimetype="image/jpeg")
	# Private: readers are checked per request, so shared caches mustn't keep a copy.
	response.headers["Cache-Control"] = f"private, max-age={PAGE_CACHE_SECONDS}"
	return response


def _sender_email():
	"""Newsletters go out from the site's default outgoing email account."""
	return frappe.db.get_value(
		"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id"
	) or frappe.db.get_value("Email Account", {"enable_outgoing": 1}, "email_id")


@frappe.whitelist(methods=["GET"])
def get_newsletter_form():
	"""Email groups an admin can send to, with how many people are in each."""
	if not _is_admin():
		frappe.throw(_("Only school admins can send newsletters."), frappe.PermissionError)
	groups = frappe.get_all(
		"Email Group", fields=["name", "title", "total_subscribers"], order_by="title asc"
	)
	schools = get_user_schools()
	return {
		"email_groups": groups,
		"schools": schools
		if schools is not None
		else frappe.get_all("School", pluck="name", order_by="name"),
		"sender_name": frappe.db.get_value("User", frappe.session.user, "full_name"),
		"sender_email": _sender_email(),
	}


@frappe.whitelist(methods=["POST"])
def send_newsletter(subject, message, email_groups, school=None):
	"""Write a newsletter and queue it to the chosen email groups straight away."""
	if not _is_admin():
		frappe.throw(_("Only school admins can send newsletters."), frappe.PermissionError)
	subject = (subject or "").strip()
	message = (message or "").strip()
	email_groups = json.loads(email_groups) if isinstance(email_groups, str) else (email_groups or [])
	if not subject:
		frappe.throw(_("Give the newsletter a subject."))
	if not message:
		frappe.throw(_("Write the newsletter first."))
	if not email_groups:
		frappe.throw(_("Pick who it goes to."))
	missing = [g for g in email_groups if not frappe.db.exists("Email Group", g)]
	if missing:
		frappe.throw(_("Unknown email group: {0}").format(", ".join(missing)))

	sender_email = _sender_email()
	if not sender_email:
		frappe.throw(_("No outgoing email account is set up, so newsletters can't be sent yet."))

	schools = get_user_schools()
	if schools is not None:
		if not school and len(schools) == 1:
			school = schools[0]
		if school not in schools:
			frappe.throw(_("Pick your school."))

	paragraphs = [p.strip() for p in message.replace("\r\n", "\n").split("\n\n") if p.strip()]
	html = "".join("<p>{}</p>".format(escape_html(p).replace("\n", "<br>")) for p in paragraphs)
	doc = frappe.get_doc(
		{
			"doctype": "Newsletter",
			"subject": subject,
			"sender_name": frappe.db.get_value("User", frappe.session.user, "full_name"),
			"sender_email": sender_email,
			"content_type": "Rich Text",
			"message": html,
			"custom_school": school or None,
			"email_group": [{"email_group": g} for g in email_groups],
		}
	)
	doc.insert()
	doc.send_emails()
	return {"name": doc.name, "total_recipients": cint(doc.get("total_recipients"))}
