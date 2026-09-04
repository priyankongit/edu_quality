import json
import random

import frappe
import requests
from frappe.auth import LoginManager

try:
	from nextai.whatsapp_business_api_integration.doctype.whatsapp_message.whatsapp_message import (
		send_templated_message,
	)
except ImportError:

	def send_templated_message(*args, **kwargs):
		frappe.log_error(
			title="Walsh Login: nextai not installed",
			message="send_templated_message was called but the 'nextai' app is not installed on this bench.",
		)


from edu_quality.public.py.utils import remove_indian_country_code

# comment


def format_wa_phone_no(phone_no):
	if not phone_no:
		return False
	if phone_no.startswith("+"):
		phone_no = phone_no[1:]
	if len(phone_no) == 10:
		phone_no = "91" + phone_no

	# check if all characters are numeric
	if not phone_no.isdigit():
		return False
	return phone_no


def create_otp(wa_phone_no, custom_key=None, for_appstore_test=False):
	otp = ""
	for _ in range(4):
		otp += str(random.randint(1, 9))
	cache = frappe.cache()
	key = custom_key or ("wo" + wa_phone_no)
	# frappe.cache.delete_value(key)
	if for_appstore_test:
		otp = "1234"
	cache.set_value(key, otp)
	return otp


def match_otp(wa_phone_no, otp, custom_key=None):
	from edu_quality.common.utils.access import clear_otp_attempts, enforce_otp_attempts

	cache = frappe.cache()
	key = custom_key or ("wo" + wa_phone_no)
	enforce_otp_attempts(key)
	cache_otp = cache.get_value(key)
	if otp == cache_otp:
		clear_otp_attempts(key)
		return True
	return False


def create_or_get_contact(wa_phone_number, contact_name):
	if frappe.db.exists("Contact", {"whatsapp_id": wa_phone_number}):
		contact = frappe.get_last_doc("Contact", filters={"whatsapp_id": wa_phone_number})
	else:
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": contact_name,
				"whatsapp_id": wa_phone_number,
				"chatbot_disabled": 1,
			}
		).insert(ignore_permissions=True)
	return contact


def send_otp_to_whatsapp(wa_phone_no, otp):
	try:
		contact = create_or_get_contact(wa_phone_no, "walsh:" + str(wa_phone_no))
		template_data = [{"type": "text", "text": f"{otp}"}]
		send_templated_message(contact.name, "walsh_new_adm_login", json.dumps(template_data))
	except Exception as e:
		pass


def send_otp_to_sms(full_phone_no, otp):
	api_key = frappe.conf.get("sms_api_key")
	app_name = frappe.conf.get("sms_app_name") or "the app"
	message = (
		f"OTP is {otp} for logging into {app_name}. "
		+ "Valid till 10 min.\nDo not share OTP for security reasons."
	)
	template_id = frappe.conf.get("sms_login_template_id")
	sender = frappe.conf.get("sms_sender")
	encoded_message = requests.utils.quote(message)
	url = f"http://smssolution.net.in/api/v4/?api_key={api_key}&method=sms&message={encoded_message}\
    &to={full_phone_no}&sender={sender}&template_id={template_id}"
	response = requests.post(url)
	response = response.json()
	return response


def save_push_notification_token(push_token, user_id=None):
	user_id = user_id or frappe.session.user
	has_token = frappe.db.exists("Mobile Push Token", {"token": push_token, "user_id": user_id})
	if not has_token:
		frappe.get_doc({"doctype": "Mobile Push Token", "token": push_token, "user_id": user_id}).insert(
			ignore_permissions=True
		)


@frappe.whitelist()
def remove_push_notification_token(push_token=None, remove_all=False):
	user_id = frappe.session.user
	if remove_all:
		frappe.db.delete("Mobile Push Token", {"user_id": user_id})
		return
	if not push_token:
		return
	has_token = frappe.db.exists("Mobile Push Token", {"token": push_token, "user_id": user_id})
	if has_token:
		frappe.db.delete("Mobile Push Token", {"token": push_token, "user_id": user_id})


def is_disabled(guardian_name, logout_if_defaulter=False):
	students = frappe.db.get_all(
		"Student Guardian",
		{"guardian": guardian_name, "parenttype": "Student"},
		"parent",
	)
	student_names = [
		frappe.db.get_value("Student", {"name": student.parent}, "enabled") == 0 for student in students
	]

	if all(student_names):
		if logout_if_defaulter:
			remove_push_notification_token(remove_all=True)
			login_manager = LoginManager()
			login_manager.logout()
		return True

	return False


def get_guardian(guardian_number=None, user_id=None, email=None):
	if user_id:
		if user_id and frappe.db.exists("Guardian", {"user": user_id}):
			guardian = frappe.get_cached_doc("Guardian", {"user": user_id})
			return guardian
	if email:
		if email and frappe.db.exists("Guardian", {"email_address": email}):
			guardian = frappe.get_cached_doc("Guardian", {"email_address": email})
			return guardian
	if guardian_number and frappe.db.exists("Guardian", {"mobile_number": guardian_number}):
		guardian = frappe.get_cached_doc("Guardian", {"mobile_number": guardian_number})
		return guardian
	elif guardian_number and frappe.db.exists(
		"Guardian", {"custom_secondary_mobile_number": guardian_number}
	):
		guardian = frappe.get_cached_doc("Guardian", {"custom_secondary_mobile_number": guardian_number})
		return guardian
	return None


@frappe.whitelist(allow_guest=True)
def send_otp(phone_no=None, email=None):
	try:
		wa_phone_no = None
		guardian_number = None
		if phone_no:
			wa_phone_no = format_wa_phone_no(phone_no)
			if not wa_phone_no:
				return {
					"error": True,
					"error_type": "invalid_phone_number",
					"error_message": "Invalid Phone Number",
				}

			phone_with_country_code = "+" + str(wa_phone_no)
			guardian_number = remove_indian_country_code(phone_with_country_code)
		guardian = get_guardian(guardian_number, email=email)

		students = frappe.get_all("Student", filters={"guardian": guardian.name}, fields=["*"])
		all_disabled = all(student["enabled"] == 0 for student in students)
		if not students or all_disabled:
			return {
				"error": True,
				"error_type": "student_disabled",
				"error_message": "All students for this guardian are disabled.",
			}

		if not guardian:
			return {
				"error": True,
				"error_type": "guardian_not_found",
				"error_message": "Guardian Not Found",
			}
		if is_disabled(guardian.name):
			return {
				"error": True,
				"error_type": "defaulter",
				"error_message": "Your login is disabled",
			}
		if not frappe.db.exists("User", guardian.user):
			return {
				"error": True,
				"error_type": "user_not_found",
				"error_message": "User Not Found",
			}
		if email:
			otp = create_otp(email, "email")
		else:
			otp = create_otp(wa_phone_no)

		if wa_phone_no:
			send_otp_to_whatsapp(wa_phone_no, otp)
			send_otp_to_sms(phone_with_country_code, otp)
		send_otp_to_email(guardian.email_address, otp)

		return {
			"success": True,
			"message": "Otp Sent To +" + str(wa_phone_no or email),
		}
	except Exception as e:
		frappe.log_error(title="Otp Error", message=frappe.get_traceback())
		return {
			"error": True,
			"error_type": "Something Went Wrong",
			"error_message": str(e),
		}


def send_otp_to_email(email, otp):
	try:
		if not email:
			return
		template_name = "Walsh Email OTP"
		email_template = frappe.get_doc("Email Template", template_name)
		content = frappe.render_template(
			email_template.get("response_html") or email_template.get("response"),
			{"otp": otp},
		)
		email_args = {
			"recipients": [email],
			"subject": email_template.get("subject"),
			"message": content,
		}
		frappe.sendmail(**email_args)
	except Exception as e:
		frappe.log_error("Error sending lead generation email", str(e))
		return None


def get_student_form(doc):
	student_forms = []
	applicants = frappe.db.get_all(
		"Student Guardian",
		{"guardian": doc.name, "parenttype": "Student Applicant"},
		"parent",
	)
	link = frappe.utils.get_url() + "/student-application/"
	for applicant in applicants:
		student = frappe.db.get_value("Student", {"student_applicant": applicant.parent}) or applicant.parent
		student_forms.append({"student": student, "link": link + applicant.parent + "/edit"})
	return student_forms


@frappe.whitelist(allow_guest=True)
def verify_otp(otp, phone_no=None, push_token=None, form_link=None, email=None):
	try:
		guardian_number = None
		matched = False

		if not email:
			wa_phone_no = format_wa_phone_no(phone_no)
			phone_with_country_code = "+" + wa_phone_no
			guardian_number = remove_indian_country_code(phone_with_country_code)
			matched = match_otp(wa_phone_no, otp)
		else:
			matched = match_otp(email, otp, "email")

		if matched:
			guardian = get_guardian(guardian_number, email=email)
			user = frappe.get_cached_doc("User", guardian.user)
			login_manager = LoginManager()
			login_manager.login_as(user.name)

			if form_link:
				form_link = get_student_form(guardian)

			if push_token:
				save_push_notification_token(push_token, user.name)

			# key = "walsh_otp" + wa_phone_no
			# frappe.cache.delete_value(key)

			return {
				"success": True,
				"message": "Login Successful",
				"form_link": form_link,
			}

		return {
			"error": True,
			"error_type": "invalid_otp",
			"error_message": "Invalid OTP",
		}
	except Exception as e:
		return {"error": True, "error_type": "server_error", "error_message": str(e)}


@frappe.whitelist()
def register_push_notice(**kwargs):
	push_token = kwargs.get("push_token")
	if not push_token:
		raise frappe.exceptions.MandatoryError("Push Token is required")
	save_push_notification_token(push_token)


@frappe.whitelist(allow_guest=True)
def logout(push_token=None):
	remove_push_notification_token(push_token, True)
	login_manager = LoginManager()
	login_manager.logout()
	return {
		"success": True,
		"message": "Logout Successful",
	}


# def set_session_variables():
#     # Fetch guardian details for the current session user
#     guardian_name = frappe.db.get_value(
#         "Guardian", {"user": frappe.session.user}, "name"
#     )
#     frappe.local.session["guardian"] = guardian_name

#     # Fetch students associated with the guardian
#     students = get_students()
#     student_names = [s.name for s in students]
#     frappe.local.session.data["students"] = students
#     frappe.local.session.data["student_names"] = student_names

#     # Fetch program enrollments for the students
#     enrollments = frappe.db.sql(
#         """
#         SELECT DISTINCT student_group AS division, program AS class
#         FROM `tabProgram Enrollment`
#         WHERE student IN %(student_names)s
#         """,
#         {"student_names": student_names},
#         as_dict=True,
#     )

#     # Extract divisions and classes from enrollments
#     frappe.local.session.data["divisions"] = [e.division for e in enrollments]
#     frappe.local.session.data["classes"] = [e.get("class") for e in enrollments]
#     frappe.local.session.data["enrollments"] = enrollments
#     # Save changes to the database

#     frappe.local.session_obj.update(force=True)
#     frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def get_logged_user():
	return frappe.session.user


def get_students():
	user = frappe.session.user
	guardian = frappe.get_cached_doc("Guardian", {"user": user})
	students = frappe.get_all("Student", filters={"guardian": guardian.name}, fields=["enabled"])
	student_disabled = all(student.get("enabled") == 0 for student in students)
	# if all of student disabled log out the parent
	if student_disabled:
		logout()

		frappe.throw(("Not permitted"), frappe.PermissionError)
		return []

	students = frappe.get_all("Student", filters={"guardian": guardian.name, "enabled": 1}, fields=["*"])
	return students


@frappe.whitelist(allow_guest=True)
def user_login(usr, pwd, push_token):
	login_manager = LoginManager()

	try:
		login_manager.authenticate(usr, pwd)
		login_manager.post_login()
		user = frappe.session.user
		guardian = get_guardian(user_id=user)
		students = frappe.get_all("Student", filters={"guardian": guardian.name}, fields=["*"])
		all_disabled = all(student["enabled"] == 0 for student in students)

		if not students or all_disabled:
			return {
				"error": True,
				"error_type": "student_disabled",
				"error_message": "All students for this guardian are disabled.",
			}

		if not guardian:
			return {
				"error": True,
				"error_type": "invalid_guardian",
				"error_message": "Invalid Guardian",
			}

		if push_token:
			save_push_notification_token(push_token, user)

		# key = "walsh_otp" + wa_phone_no
		# frappe.cache.delete_value(key)

		return {
			"success": True,
			"message": "Login Successful",
		}

	except Exception as e:
		return {"error": True, "error_type": "server_error", "error_message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_schools_for_guest():
	try:
		schools = frappe.get_all("School", fields=["name"])
		return {"success": True, "data": schools}
	except Exception as e:
		return {"error": True, "error_type": "server_error", "error_message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_programs_for_guest(school):
	try:
		programs = frappe.get_all(
			"Program",
			filters={
				"school": school,
			},
			fields=["program_name"],
		)
		return {"success": True, "data": programs}
	except Exception as e:
		return {"error": True, "error_type": "server_error", "error_message": str(e)}


@frappe.whitelist()
def request_account_deletion():
	user = frappe.session.user
	guardian = get_guardian(user_id=user)
	if not guardian:
		return {
			"error": True,
			"error_type": "invalid_guardian",
			"error_message": "Invalid Guardian",
		}

	existing_request = frappe.get_all(
		"Deletion Request", filters={"user": user, "status": "Pending"}, limit=1
	)

	if existing_request:
		return {
			"error": True,
			"error_type": "request_exists",
			"error_message": "A deletion request is already pending for this account/Test accounts cant be deleted",
		}

	deletion_request = frappe.new_doc("Deletion Request")
	deletion_request.user = user
	deletion_request.status = "Pending"
	deletion_request.insert(ignore_permissions=True)

	frappe.local.login_manager.logout()

	return {
		"success": True,
		"message": "Account deletion request submitted successfully",
	}
