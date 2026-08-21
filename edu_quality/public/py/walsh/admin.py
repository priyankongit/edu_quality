import csv
import json

import frappe
import requests
from frappe.core.doctype.communication.email import make as create_email

from edu_quality.edu_quality.server_scripts.utils import current_academic_year


def render_jinja(text, object):
	if not text:
		return ""
	if not object:
		return text
	return frappe.render_template(text, object)


def get_guardian_emails(student):
	student_guardians = frappe.get_all(
		"Student Guardian",
		filters={"parent": student, "parenttype": "Student"},
		fields=["guardian"],
	)
	guardians = [frappe.get_cached_doc("Guardian", g.get("guardian")) for g in student_guardians]
	guardian_emails = []
	for guardian in guardians:
		if guardian.email_address:
			guardian_emails.append(guardian.email_address)
	return guardian_emails


def send_notification(student_id, subject="", notice_id="", cmap=False, custom=None):
	student_guardians = frappe.get_all(
		"Student Guardian",
		filters={"parent": student_id, "parenttype": "Student"},
		fields=["guardian"],
	)
	guardians = [frappe.get_cached_doc("Guardian", g.get("guardian")) for g in student_guardians]
	for guardian in guardians:
		user = guardian.get("user")
		if user:
			push_tokens = frappe.get_all("Mobile Push Token", filters={"user_id": user}, fields=["token"])
			for push_token in push_tokens:
				url = "https://exp.host/--/api/v2/push/send"
				payload = {}
				if cmap:
					payload = json.dumps(
						{
							"to": push_token.get("token"),
							"title": subject + " - " + student_id,
							"data": {"url_path": "/cmap/"},
							# "body": json.dumps({"url_path": f"/notice/{notice_id}?student={student_id}"})
						}
					)
				elif custom and isinstance(custom, dict):
					custom["to"] = push_token.get("token")
					payload = json.dumps(custom)
				else:
					payload = json.dumps(
						{
							"to": push_token.get("token"),
							"title": subject + " - " + student_id,
							"data": {"url_path": f"/notice/{notice_id}?student={student_id}"},
							# "body": json.dumps({"url_path": f"/notice/{notice_id}?student={student_id}"})
						}
					)
				headers = {"Content-Type": "application/json"}
				requests.request("POST", url, headers=headers, data=payload)


def notification_sender(user, student, subject="", url_path=""):
	push_tokens = frappe.get_all("Mobile Push Token", filters={"user_id": user}, fields=["token"])
	for push_token in push_tokens:
		url = "https://exp.host/--/api/v2/push/send"
		payload = json.dumps(
			{
				"to": push_token.get("token"),
				"title": subject + " - " + student,
				"data": {"url_path": url_path},
			}
		)
		headers = {"Content-Type": "application/json"}
		requests.request("POST", url, headers=headers, data=payload)


def enqueued_specific_notice_emails(__args):
	csv_file = __args.get("csv_file")
	subject = __args.get("subject")
	content = __args.get("notice")
	has_pdf = __args.get("hasPdf")
	if has_pdf:
		content = "pdf"

	csv_file_path = frappe.get_site_path() + csv_file
	csv_text = open(csv_file_path, encoding="utf-8-sig").read()

	csv_data = csv.DictReader(csv_text.splitlines())
	csv_data = list(csv_data)
	csv_data = [{str(key).strip(): value for key, value in row.items()} for row in csv_data]
	school = csv_data[0].get("school")

	bcc_email_group = frappe.get_value("School", school, "bcc_email_group")

	bcc_emails = []
	if bcc_email_group:
		bcc_emails = bcc_emails + [
			eg.email
			for eg in frappe.get_all(
				"Email Group Member",
				filters={"email_group": bcc_email_group},
				fields=["email"],
			)
		]
		# remove duplicates from bcc_emails
		bcc_emails = list(set(bcc_emails))

	success_ref_ids = []
	failure_ref_ids = []
	failure_texts = []
	school_admin_bcc_email = ""
	for row in csv_data:
		try:
			student_id = row.get("ID") or row.get("id") or row.get("name")
			student = frappe.get_cached_doc("Student", student_id)
			if not school_admin_bcc_email:
				school = frappe.get_cached_doc("School", student.school)
				school_admin_bcc_email = school.email_address
			data = {**student.as_dict(), **row}
			notice_subject = render_jinja(subject, data)
			notice_content = render_jinja(content, data)
			student_email = student.student_email_id
			guardian_email = get_guardian_emails(student_id)
			create_email(
				recipients=[student_email] + guardian_email,
				subject=notice_subject,
				content=notice_content,
				bcc=bcc_emails + ([school_admin_bcc_email] if school_admin_bcc_email else []),
				send_email=True,
				read_receipt=True,
			)
			bcc_emails = []
			success_ref_ids.append(student_id)
		except Exception as e:
			failure_ref_ids.append(row.get("ID") or row.get("id") or row.get("name"))
			failure_texts.append(e)

	if len(failure_ref_ids):
		frappe.get_doc(
			{
				"doctype": "School Notice Error",
				"type": "email",
				"failure_list": json.dumps(failure_ref_ids, default=str, indent=2),
				"failure_messages": json.dumps(failure_texts, default=str, indent=2),
			}
		).insert(ignore_permissions=True)


def enqueued_specific_notifications(notice_ids):
	success_ref_ids = []
	failure_ref_ids = []
	failure_texts = []
	for notice_id in notice_ids:
		try:
			notice = frappe.get_cached_doc("School Notice", notice_id).as_dict()
			subject = notice.subject
			student_id = notice.student
			send_notification(student_id, subject, notice_id)
			success_ref_ids.append(student_id)
		except Exception as e:
			failure_ref_ids.append(notice_id)
			failure_texts.append(e)

	if len(failure_ref_ids):
		frappe.get_doc(
			{
				"doctype": "School Notice Error",
				"type": "notification",
				"failure_list": json.dumps(failure_ref_ids, default=str, indent=2),
				"failure_messages": json.dumps(failure_texts, default=str, indent=2),
			}
		).insert(ignore_permissions=True)


def enqueued_specific_notice_docs(__args):
	csv_file = __args.get("csv_file")
	subject = __args.get("subject")
	content = __args.get("notice")
	raw_html = __args.get("raw_html")
	categories = categories = [{"school_notice_category": c} for c in __args.get("categories", [])]
	requires_approval = __args.get("requires_approval")
	has_pdf = __args.get("hasPdf")
	pdf = __args.get("pdf")

	if has_pdf:
		content = "pdf"

	csv_file_path = frappe.get_site_path() + csv_file
	csv_text = open(csv_file_path, encoding="utf-8-sig").read()

	csv_data = csv.DictReader(csv_text.splitlines())
	csv_data = list(csv_data)
	csv_data = [{str(key).strip(): value for key, value in row.items()} for row in csv_data]
	success_ref_ids = []
	failure_ref_ids = []
	failure_texts = []
	notice_ids = []
	for row in csv_data:
		try:
			student_id = row.get("ID") or row.get("id") or row.get("name")
			student = frappe.get_cached_doc("Student", student_id)
			data = {**student.as_dict(), **row}
			notice_subject = render_jinja(subject, data)
			notice_content = render_jinja(content, data)
			notice = frappe.get_doc(
				{
					"doctype": "School Notice",
					"student": student.name,
					"subject": notice_subject,
					"notice": notice_content,
					"is_raw_html": 1 if raw_html else 0,
					"category": categories,
					"requires_approval": requires_approval,
					"is_pdf": bool(has_pdf) or 0,
					"pdf": pdf,
				}
			).insert(ignore_permissions=True)
			notice.reload()
			notice_ids.append(notice.name)
			success_ref_ids.append(student_id)
		except Exception as e:
			failure_ref_ids.append(row.get("ID") or row.get("id") or row.get("name"))
			failure_texts.append(frappe.get_traceback())
	frappe.enqueue(enqueued_specific_notifications, queue="long", notice_ids=notice_ids)
	# enqueued_specific_notifications(notice_ids)

	if len(failure_ref_ids):
		frappe.get_doc(
			{
				"doctype": "School Notice Error",
				"type": "notice",
				"failure_list": json.dumps(failure_ref_ids, default=str, indent=2),
				"failure_messages": json.dumps(failure_texts, default=str, indent=2),
			}
		).insert(ignore_permissions=True)


def enqueued_generic_notice_emails(__args):
	subject = __args.get("subject")
	content = __args.get("notice")
	classes = __args.get("classes")
	divisions = __args.get("divisions")
	student_statuses = __args.get("student_statuses")
	academic_year = __args.get("academic_year")
	has_pdf = __args.get("hasPdf")
	school = __args.get("school")
	if has_pdf:
		content = "pdf"

	bcc_email_group = frappe.get_value("School", school, "bcc_email_group")

	bcc_emails = []
	if bcc_email_group:
		bcc_emails = bcc_emails + [
			eg.email
			for eg in frappe.get_all(
				"Email Group Member",
				filters={"email_group": bcc_email_group},
				fields=["email"],
			)
		]
		# remove duplicates from bcc_emails
		bcc_emails = list(set(bcc_emails))

	students_values = {
		"classes": classes,
		"divisions": divisions,
		"student_statuses": student_statuses,
		"academic_year": academic_year,
	}
	students = []
	if len(classes) > 1 or len(divisions) == 0:
		students = frappe.db.sql(
			"""
            select *
            from tabStudent
            where name in (
               select student
               from `tabProgram Enrollment`
               where program in %(classes)s
               and academic_year = %(academic_year)s
            )
            and student_status in %(student_statuses)s
        """,
			values=students_values,
			as_dict=1,
		)
	else:
		students = frappe.db.sql(
			"""
            select *
            from tabStudent
            where name in (
               select student
               from `tabProgram Enrollment`
               where student_group in %(divisions)s
               and academic_year = %(academic_year)s
            )
            and student_status in %(student_statuses)s
        """,
			values=students_values,
			as_dict=1,
		)

	success_student_ids = []
	failure_student_ids = []
	failure_texts = []
	school_admin_bcc_email = ""
	for student in students:
		try:
			notice_subject = render_jinja(subject, student)
			notice_content = render_jinja(content, student)
			student_email = student.student_email_id
			guardian_email = get_guardian_emails(student.name)
			if not school_admin_bcc_email:
				school = frappe.get_cached_doc("School", student.school)
				school_admin_bcc_email = school.email_address
			create_email(
				recipients=[student_email] + guardian_email,
				subject=notice_subject,
				content=notice_content,
				bcc=bcc_emails + ([school_admin_bcc_email] if school_admin_bcc_email else []),
				send_email=True,
				read_receipt=True,
			)
			bcc_emails = []
			success_student_ids.append(student.name)
		except Exception as e:
			failure_student_ids.append(student.get("name"))
			failure_texts.append(e)

	if len(failure_student_ids):
		frappe.get_doc(
			{
				"doctype": "School Notice Error",
				"type": "email",
				"failure_list": json.dumps(failure_student_ids, default=str, indent=2),
				"failure_messages": json.dumps(failure_texts, default=str, indent=2),
			}
		).insert(ignore_permissions=True)


def enqueued_generic_notifications(notice_ids):
	success_student_ids = []
	failure_ids = []
	failure_texts = []
	for notice_id in notice_ids:
		try:
			notice = frappe.get_cached_doc("School Notice", notice_id)
			subject = notice.subject
			students_values = {
				"class": notice.get("class"),
				"division": notice.get("division"),
				"student_status": notice.get("student_status"),
				"academic_year": notice.get("academic_year"),
			}
			if notice.get("division"):
				students = frappe.db.sql(
					"""
                        select *
                        from tabStudent
                        where name in (
                           select student
                           from `tabProgram Enrollment`
                           where student_group = %(division)s
                           and academic_year = %(academic_year)s
                        )
                        and student_status = %(student_status)s
                    """,
					values=students_values,
					as_dict=1,
				)
			else:
				students = frappe.db.sql(
					"""
                        select *
                        from tabStudent
                        where name in (
                           select student
                           from `tabProgram Enrollment`
                           where program = %(class)s
                           and academic_year = %(academic_year)s
                        )
                        and student_status = %(student_status)s
                    """,
					values=students_values,
					as_dict=1,
				)
			for student in students:
				try:
					notice_subject = render_jinja(subject, student)
					send_notification(student.name, notice_subject, notice_id)
					success_student_ids.append(student.name)
				except Exception as e:
					failure_ids.append(student.get("name"))
					failure_texts.append(frappe.get_traceback())
		except Exception as e:
			failure_ids.append(f"notice:{notice_id}")
			failure_texts.append(frappe.get_traceback())

	if len(failure_ids):
		frappe.get_doc(
			{
				"doctype": "School Notice Error",
				"type": "notification",
				"failure_list": json.dumps(failure_ids, default=str, indent=2),
				"failure_messages": json.dumps(failure_texts, default=str, indent=2),
			}
		).insert(ignore_permissions=True)


def enqueued_generic_notice_docs(__args):
	subject = __args.get("subject")
	content = __args.get("notice")
	is_public = __args.get("is_public")
	school = __args.get("school")
	classes = __args.get("classes")
	divisions = __args.get("divisions")
	has_pdf = __args.get("hasPdf")
	pdf = __args.get("pdf")
	if has_pdf:
		content = "pdf"
	student_statuses = __args.get("student_statuses")
	academic_year = __args.get("academic_year")
	raw_html = __args.get("raw_html")
	notice_ids = []

	if is_public:
		notice = frappe.get_doc(
			{
				"doctype": "School Notice",
				"is_generic_notice": 1,
				"school": school,
				"subject": subject,
				"notice": content,
				"academic_year": academic_year,
				"is_raw_html": 1 if raw_html else 0,
				"is_pdf": has_pdf,
				"pdf": pdf,
				"is_public": 1,
			}
		).insert(ignore_permissions=True)
		notice.reload()
		notice_ids.append(notice.name)
	else:
		for student_status in student_statuses:
			if len(classes) > 1 or len(divisions) == 0:
				for class_ in classes:
					notice = frappe.get_doc(
						{
							"doctype": "School Notice",
							"class": class_,
							"is_generic_notice": 1,
							"school": school,
							"subject": subject,
							"student_status": student_status,
							"notice": content,
							"academic_year": academic_year,
							"is_raw_html": 1 if raw_html else 0,
							"is_pdf": has_pdf,
							"pdf": pdf,
						}
					).insert(ignore_permissions=True)
					notice.reload()
					notice_ids.append(notice.name)
			else:
				class_ = classes[0]
				for division in divisions:
					notice = frappe.get_doc(
						{
							"doctype": "School Notice",
							"is_generic_notice": 1,
							"class": class_,
							"school": school,
							"division": division,
							"subject": subject,
							"student_status": student_status,
							"notice": content,
							"academic_year": academic_year,
						}
					).insert(ignore_permissions=True)
					notice.reload()
					notice_ids.append(notice.name)
	if not is_public:
		frappe.enqueue(enqueued_generic_notifications, queue="long", notice_ids=notice_ids)
	# enqueued_generic_notifications(notice_ids)


def send_generic_notification(variables, **kwargs):
	"""
	Send a generic notification to students based on the supplied filters
	Sending notification using dotted path in funnel
	variables: data from previous node
	kwargs: payload from exec dotted path node
	"""
	try:
		doc = variables.get("doc")
		if doc.doctype == "Payment Request":
			student = frappe.get_doc("Student", doc.party)
		elif doc.doctype == "Program Enrollment":
			student = frappe.get_doc("Student", doc.student)

		subject = kwargs.get("subject")
		content = kwargs.get("notice")
		raw_html = kwargs.get("raw_html")
		academic_year = current_academic_year()

		notice = frappe.get_doc(
			{
				"doctype": "School Notice",
				"class": student.program,
				"is_generic_notice": 1,
				"school": student.school,
				"subject": subject,
				"student_status": student.student_status,
				"notice": content,
				"academic_year": academic_year,
				"is_raw_html": 1 if raw_html else 0,
			}
		).insert(ignore_permissions=True)
		send_notification(student.name, notice.subject, notice.name)
	except Exception:
		frappe.log_error("Push Notification", frappe.get_traceback())


def validate_school(csv_data):
	school = csv_data[0].get("school")
	for row in csv_data:
		if row.get("school") != school:
			raise frappe.exceptions.ValidationError("There are multiple schools in the CSV")


def validate_args(**kwargs):
	has_csv = kwargs.get("has_csv")
	csv_file = kwargs.get("csv_file")
	subject = kwargs.get("subject")
	content = kwargs.get("notice")
	school = kwargs.get("school")
	classes = kwargs.get("classes")
	divisions = kwargs.get("divisions")
	student_statuses = kwargs.get("student_statuses")
	is_test = kwargs.get("is_test")
	academic_year = kwargs.get("academic_year")
	student_data = kwargs.get("student_data")
	has_pdf = kwargs.get("hasPdf")
	pdf = kwargs.get("pdf")
	is_public = kwargs.get("is_public")
	# verify supplied data
	if has_csv:
		if is_test:
			student_id = student_data.get("ID") or student_data.get("id") or student_data.get("name")
			student = frappe.get_cached_doc("Student", student_id)
			if not student_data.get("school"):
				raise frappe.exceptions.MandatoryError("School (school) is required in CSV")
			if student.get("school") != student_data.get("school"):
				raise frappe.exceptions.ValidationError(
					f"School Mismatch: {student_id} [{student.get('school')}, {student_data.get('school')}]"
				)
		else:
			csv_file_path = frappe.get_site_path() + csv_file
			csv_file_path = frappe.get_site_path() + csv_file
			csv_text = open(csv_file_path, encoding="utf-8-sig").read()

			if not csv_text:
				raise frappe.exceptions.ValidationError("CSV File Error: Empty File")

			csv_data = csv.DictReader(csv_text.splitlines())
			csv_data = list(csv_data)

			# verify csv data to check if there are multiple schools
			validate_school(csv_data)

			un_matches = []
			student_ids = [row.get("ID") or row.get("id") or row.get("name") for row in csv_data]
			student_schools = frappe.get_all(
				"Student",
				fields=["name", "school"],
				filters={"name": ["in", student_ids]},
			)

			for row in csv_data:
				for student in student_schools:
					student_id = row.get("ID") or row.get("id") or row.get("name")
					if student_id == student.name:
						if student.get("school") != row.get("school"):
							un_matches.append([student_id, row.get("school")])
						break

			if len(un_matches):
				error_string = "<br/>".join([f"{row[0]} [{row[1]}]" for row in un_matches])
				raise frappe.exceptions.ValidationError(f"School Mismatch: <br/> {error_string}")
	else:
		if not is_public:
			if not school:
				raise frappe.exceptions.MandatoryError("School is required")

			if not classes:
				raise frappe.exceptions.MandatoryError("Classes are required")
			if not isinstance(classes, list):
				raise frappe.exceptions.ValidationError("Classes must be a list")
			if not len(classes):
				raise frappe.exceptions.MandatoryError("At least one Class is required")

			if len(classes) == 1 and divisions:
				if not isinstance(divisions, list):
					raise frappe.exceptions.ValidationError("Divisions must be a list")

			if not student_statuses:
				raise frappe.exceptions.MandatoryError("Student Statuses are required")
			if not isinstance(student_statuses, list):
				raise frappe.exceptions.ValidationError("Student Statuses must be a list")
			if not len(student_statuses):
				raise frappe.exceptions.MandatoryError("At least one Student Status is required")
			if not academic_year:
				raise frappe.exceptions.MandatoryError("Academic Year is required")

	if not subject:
		raise frappe.exceptions.MandatoryError("Subject is required")

	if not has_pdf and not content:
		raise frappe.exceptions.MandatoryError("Content is required")
	if has_pdf and not pdf:
		raise frappe.exceptions.MandatoryError("PDF is required")


@frappe.whitelist()
def create_notice(**kwargs):
	has_csv = kwargs.get("has_csv")
	send_emails = kwargs.get("send_emails")
	is_public = kwargs.get("is_public")
	# verify supplied data
	validate_args(**kwargs)

	if has_csv and not is_public:
		frappe.enqueue(enqueued_specific_notice_docs, __args=kwargs)
		# enqueued_specific_notice_docs(kwargs)
		if send_emails:
			frappe.enqueue(enqueued_specific_notice_emails, queue="long", __args=kwargs)
	else:
		frappe.enqueue(enqueued_generic_notice_docs, __args=kwargs)
		# enqueued_generic_notice_docs(kwargs)
		if send_emails and not is_public:
			frappe.enqueue(enqueued_generic_notice_emails, queue="long", __args=kwargs)


@frappe.whitelist()
def send_test_mail(**kwargs):
	has_csv = kwargs.get("has_csv")
	student_data = kwargs.get("student_data")
	subject = kwargs.get("subject")
	content = kwargs.get("notice")
	test_emails = kwargs.get("emails")
	classes = kwargs.get("classes")
	divisions = kwargs.get("divisions")
	student_statuses = kwargs.get("student_statuses")
	academic_year = kwargs.get("academic_year")
	is_public = kwargs.get("is_public")

	if not test_emails:
		raise frappe.exceptions.MandatoryError("Test Emails are required")

	validate_args(**kwargs, is_test=True)

	notice_subject = subject
	notice_content = content

	if has_csv:
		student_id = student_data.get("ID") or student_data.get("id") or student_data.get("name")
		student = frappe.get_cached_doc("Student", student_id)
		data = {**student.as_dict(), **student_data}
		notice_subject = render_jinja(subject, data)
		notice_content = render_jinja(content, data)
	elif not is_public:
		students = []
		students_values = {
			"classes": classes,
			"divisions": divisions,
			"student_statuses": student_statuses,
			"academic_year": academic_year,
		}
		if len(classes) > 1 or len(divisions) == 0:
			students = frappe.db.sql(
				"""
                select *
                from tabStudent
                where name in (
                   select student
                   from `tabProgram Enrollment`
                   where program in %(classes)s
                   and academic_year = %(academic_year)s
                )
                and student_status in %(student_statuses)s
                limit 1
            """,
				values=students_values,
				as_dict=1,
			)
		else:
			students = frappe.db.sql(
				"""
                select *
                from tabStudent
                where name in (
                   select student
                   from `tabProgram Enrollment`
                   where student_group in %(divisions)s
                   and academic_year = %(academic_year)s
                )
                and student_status in %(student_statuses)s
                limit 1
            """,
				values=students_values,
				as_dict=1,
			)

		if len(students):
			notice_subject = render_jinja(subject, students[0])
			notice_content = render_jinja(content, students[0])

	test_emails = [e.strip() for e in str(test_emails).split(",")]
	return create_email(
		recipients=test_emails,
		subject=notice_subject,
		content=notice_content,
		send_email=True,
		read_receipt=True,
		now=True,
	)


# /api/method/edu_quality.public.py.walsh.admin.get_student_count
@frappe.whitelist()
def get_student_count(**kwargs):
	from edu_quality.common.utils.access import get_user_schools

	classes = kwargs.get("classes")
	divisions = kwargs.get("divisions")
	student_statuses = kwargs.get("student_statuses")
	academic_year = kwargs.get("academic_year")
	classes = json.loads(classes)
	divisions = json.loads(divisions)
	student_statuses = json.loads(student_statuses)

	schools = get_user_schools()
	if schools is not None:
		if classes:
			classes = frappe.get_all("Program", filters={"name": ["in", classes], "school": ["in", schools]}, pluck="name")
		if divisions:
			divisions = frappe.get_all(
				"Student Group", filters={"name": ["in", divisions], "custom_school": ["in", schools]}, pluck="name"
			)

	if not len(classes) and not len(divisions):
		return 0

	students_values = {
		"classes": classes,
		"divisions": divisions,
		"student_statuses": student_statuses,
		"academic_year": academic_year,
	}
	if len(classes) > 1 or len(divisions) == 0:
		students = frappe.db.sql(
			"""
                    select count(*) as count
                    from tabStudent
                    where name in (
                       select student
                       from `tabProgram Enrollment`
                       where program in %(classes)s
                       and academic_year = %(academic_year)s
                    )
                    and student_status in %(student_statuses)s
                """,
			values=students_values,
			as_dict=1,
		)
	else:
		students = frappe.db.sql(
			"""
                    select count(*) as count
                    from tabStudent
                    where name in (
                       select student
                       from `tabProgram Enrollment`
                       where student_group in %(divisions)s
                       and academic_year = %(academic_year)s
                    )
                    and student_status in %(student_statuses)s
                """,
			values=students_values,
			as_dict=1,
		)
	return students[0].get("count")


# renders a email template with provided data, with subject of template as notice subject.
@frappe.whitelist()
def create_notice_from_email_template(data, email_template, send_notif=False):
	try:
		data = json.loads(data) if isinstance(data, str) else data
		email_temp_doc = frappe.get_doc("Email Template", email_template)
		subject = email_temp_doc.subject
		content = ""
		if email_temp_doc.use_html == 1:
			content = email_temp_doc.response_html
		else:
			content = email_temp_doc.response
		content = render_jinja(content, data)
		subject = render_jinja(subject, data)
		student = data.get("student")
		notice = frappe.get_doc(
			{
				"doctype": "School Notice",
				"class": data.get("program"),
				"is_generic_notice": data.get("is_generic_notice") or 0,
				"school": data.get("school"),
				"subject": subject,
				"student": student,
				"division": data.get("division"),
				"student_status": data.get("student_status"),
				"notice": content,
				"academic_year": data.get("academic_year"),
				"is_raw_html": 1,
			}
		).insert(ignore_permissions=True)

		frappe.enqueue(
			send_notification,
			queue="long",
			student_id=student,
			custom={
				"title": subject,
				"data": {"url_path": f"/notice/{notice.name}?student={student}"},
			},
		)

	except Exception as e:
		frappe.log_error(title="NoticeEmail Error", message=frappe.get_traceback())
		raise e
