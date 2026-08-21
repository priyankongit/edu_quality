# Copyright (c) 2024, Hybrowlabs Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.core.doctype.communication.email import make
from frappe.model.document import Document

try:
	from nextai.funnel.custom_trigger import trigger_event
except ImportError:

	def trigger_event(*args, **kwargs):
		frappe.log_error(
			title="CBSE LOC: nextai not installed",
			message="trigger_event was called but the 'nextai' app is not installed on this bench.",
		)


from edu_quality.edu_quality.server_scripts.utils import (
	format_mobile_number,
	set_form_user,
	set_user_permission,
	validate_aadhar,
	validate_mobile_number,
)


class CBSELOC(Document):
	def after_insert(self):
		"""Called after the document is inserted. Triggers autofill of student details."""
		self.autofill_student_details()
		self.set_guardian_permission(self.form_user)
		frappe.db.set_value("CBSE LOC", self.name, "form_hash", frappe.generate_hash(self.name, length=20))
		self.reload()
		self.send_webform_link()

	def before_save(self):
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return
		self.handle_workflow(old_doc)

	def handle_workflow(self, old_doc):
		if "Guardian" in frappe.get_roles():
			if old_doc.status == "Not Filled":
				self.status = "Filled"
				self.workflow_state = "Received"
			elif old_doc.status == "Filled" and self.get_changed_fields:
				self.workflow_state = "Updated"
			elif old_doc.status == "Rejected" and self.workflow_state == "Rejected":
				self.workflow_state = "Updated"
				self.status = "Filled"

	def on_submit(self):
		if self.workflow_state == "Approved":
			self.update_student_details()

	@property
	def get_changed_fields(self):
		changed_fields = []
		for field in self.meta.fields:
			if self.has_value_changed(field.fieldname):
				changed_fields.append(field.fieldname)
		return changed_fields

	def get_program_enrollment(self):
		ac_yr = frappe.db.get_value("Academic Year", {"custom_current_academic_year": 1}, "name")
		return frappe.get_doc(
			"Program Enrollment", {"student": self.student, "academic_year": ac_yr, "docstatus": 1}
		)

	def on_trash(self):
		user_permission = frappe.get_all(
			"User Permission", {"allow": self.doctype, "for_value": self.name}, pluck="name"
		)
		if user_permission:
			for perm in user_permission:
				frappe.delete_doc("User Permission", perm, ignore_permissions=True)

	@frappe.whitelist()
	def reject(self, reason=None):
		if reason:
			self.reject_reason = reason
			self.save(ignore_permissions=True)
			trigger_event(doc=self, event_name="send_cbse_form")

	def validate(self):
		self.validate_aadhar_number()
		self.validate_mobile_numbers()
		self.validate_income()

	def validate_income(self):
		if self.approximate_annual_income == "Select Income Range":
			frappe.throw("Please Select Approximate Annual Income")

	def validate_aadhar_number(self):
		if not validate_aadhar(self.aadhar_number):
			frappe.throw("Invalid Aadhar Number")

	def validate_mobile_numbers(self):
		invalid_numbers = []
		if self.father_mobile_number and not validate_mobile_number(self.father_mobile_number):
			invalid_numbers.append("Father's")
		if self.mother_mobile_number and not validate_mobile_number(self.mother_mobile_number):
			invalid_numbers.append("Mother's")

		if invalid_numbers:
			frappe.throw(
				f"{', '.join(invalid_numbers)} Mobile Number(s) are Invalid! [Use 10-digit mobile number, no spaces, symbols]"
			)

	def set_guardian_permission(self, user):
		"""Set permission for the guardian user to access the CBSE LOC document."""
		set_user_permission(user, "CBSE LOC", self.name)

	def autofill_student_details(self):
		"""
		Fetches student details from the 'Student' document and updates the current document.
		Also fetches and updates guardian details if available.
		"""
		student = frappe.get_doc("Student", self.student)

		full_name = self._construct_full_name(student.first_name, student.middle_name, student.last_name)
		categories = {"general", "sc", "st", "obc"}
		category = (
			student.category if student.category and student.category.lower() in categories else "General"
		)
		program_enrollment = self.get_program_enrollment()
		self.update(
			{
				"first_name": student.first_name,
				"middle_name": student.middle_name,
				"last_name": student.last_name,
				"full_name": full_name,
				"gender": student.gender,
				"date_of_birth": student.date_of_birth,
				"category": category,
				"caste": student.caste,
				"other_caste": student.other_caste,
				"aadhar_number": student.aadhaar_card_number,
				"housebuildingapt": student.address_line_1,
				"survey_nolaneroad": student.address_line_2,
				"colonysocietyarea": student.landmark,
				"city": student.city,
				"pincode": student.pincode,
				"student_status": student.student_status,
				"school": program_enrollment.custom_school,
				"program": program_enrollment.program,
				"division": program_enrollment.student_group,
			}
		)

		for guard in student.guardians:
			if guard.relation.lower() in ["father", "mother"]:
				self._update_guardian_details(guard)

		self.get_subject_details()

		self.save(ignore_permissions=True)

	def get_subject_details(self):
		program_enrollment = self.get_program_enrollment()
		i = 1
		for subject in program_enrollment.courses:
			if i < 7:
				self.update(
					{
						f"subject_{i}": subject.course
						+ "["
						+ frappe.db.get_value("Course", subject.course, "custom_board_short_code")
						+ "]"
					}
				)
			i = i + 1

	def _construct_full_name(self, first_name, middle_name, last_name):
		"""
		Constructs a full name from first, middle, and last names.

		Args:
		    first_name (str): The first name of the person.
		    middle_name (str): The middle name of the person.
		    last_name (str): The last name of the person.

		Returns:
		    str: The full name constructed from the given components.
		"""
		parts = [first_name]
		if middle_name:
			parts.append(middle_name)
		if last_name:
			parts.append(last_name)
		parts = [part for part in parts if part is not None]
		return " ".join(parts)

	@frappe.whitelist()
	def send_webform_link(self):
		trigger_event(doc=self, event_name="send_cbse_form")

	@frappe.whitelist()
	def send_doc_after_filling(self, subject=None, content=None, send_mail=1):
		try:
			make(
				doctype="CBSE LOC",
				name=self.name,
				send_email=send_mail,
				recipients=self.get_recipients(),
				subject=subject,
				content=content,
			)
		except Exception as e:
			frappe.log_error(e)

	def get_recipients(self):
		recipients = []
		if self.father_email:
			recipients.append(self.father_email)
		if self.mother_email and self.mother_email != self.father_email:
			recipients.append(self.mother_email)
		return ", ".join(recipients)

	def _update_guardian_details(self, guardian):
		"""
		Updates the document with guardian details based on the relation (Father/Mother).

		Args:
		    guardian (Guardian): The Guardian document object.
		"""
		relation = guardian.relation.lower()
		doc = frappe.get_doc("Guardian", guardian.guardian)
		if relation == "father":
			self.form_user = doc.user
		else:
			if not self.form_user:
				self.form_user = doc.user
		full_name = self._construct_full_name(doc.first_name, doc.middle_name, doc.last_name)
		details = {
			f"{relation}_first_name": doc.first_name,
			f"{relation}_middle_name": doc.middle_name,
			f"{relation}_last_name": doc.last_name,
			f"{relation}_full_name": full_name,
			f"{relation}_mobile_number": format_mobile_number(doc.mobile_number or ""),
			f"{relation}_email": doc.email_address,
		}

		self.update(details)

	def update_student_details(self):
		"""
		Updates the student details in the 'Student' document based on the CBSE LOC form details.
		"""
		try:
			student = frappe.get_doc("Student", self.student)
			updated_fields = {
				"first_name": self.first_name,
				"middle_name": self.middle_name,
				"last_name": self.last_name,
				"gender": self.gender,
				"date_of_birth": self.date_of_birth,
				"category": self.category if self.category != "General" else "Open",
				"caste": self.caste,
				"other_caste": self.other_caste,
				"aadhaar_card_number": self.aadhar_number,
				"address_line_1": self.housebuildingapt,
				"address_line_2": self.survey_nolaneroad,
				"landmark": self.colonysocietyarea,
				"city": self.city,
				"pincode": self.pincode,
				"student_status": self.student_status,
				"category_cert": self.category_certificate,
				"birth_certificate": self.birth_certificate,
				"aadhaar_card_certificate": self.aadhar_card,
			}
			student.update(updated_fields)
			student.save(ignore_permissions=True)

			# Update guardian details
			for relation in ["Father", "Mother"]:
				student_guardian = frappe.get_doc(
					"Student Guardian", {"parent": self.student, "relation": relation}, "guardian"
				)
				guardian = frappe.get_doc("Guardian", student_guardian.guardian)

				relation = relation.lower()
				updated_guardian_fields = {
					"first_name": self.get(f"{relation}_first_name"),
					"middle_name": self.get(f"{relation}_middle_name"),
					"last_name": self.get(f"{relation}_last_name"),
					"guardian_name": self.get(f"{relation}_full_name"),
					"mobile_number": self.get(f"{relation}_mobile_number"),
					"email_address": self.get(f"{relation}_email"),
					"annual_income": self.approximate_annual_income,
				}

				guardian.update(updated_guardian_fields)
				student_guardian.update(updated_guardian_fields)
				guardian.save(ignore_permissions=True)
				student_guardian.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(title="CBSE LOC Error", message=f"{self.name}\n{frappe.get_traceback()}")


@frappe.whitelist(allow_guest=True)
def get_form_details(hash):
	"""
	Retrieves the CBSE LOC document details based on the provided hash.

	Args:
	    hash (str): The unique hash associated with the CBSE LOC document.

	Returns:
	    dict: A dictionary containing the form user details.

	Raises:
	    frappe.PermissionError: If the CBSE LOC document with the provided hash is not found.
	"""
	if not frappe.db.exists("CBSE LOC", {"form_hash": hash}):
		frappe.throw("Form Not Found!")
	docname = frappe.db.get_value("CBSE LOC", {"form_hash": hash}, "name")
	return set_form_user("CBSE LOC", docname)


@frappe.whitelist()
def generate_confirmations(program, status):
	"""
	Generates CBSE LOC documents for students enrolled in the given program.

	Args:
	    program (str): The name of the program for which CBSE LOCs need to be generated.

	Returns:
	    dict: A dictionary containing the status (success or failure) and an error message (if applicable).
	"""
	try:
		frappe.enqueue(student_confirmation_generation, program=program, status=status, queue="long")
		return {"status": 1}
	except Exception as e:
		return {"status": 0, "error": str(e)}


def student_confirmation_generation(program, status="Current student"):
	"""
	Helper function to generate CBSE LOC documents for students enrolled in the given program.

	Args:
	    program (str): The name of the program for which CBSE LOCs need to be generated.
	"""
	ac_yr = frappe.db.get_value("Academic Year", {"custom_current_academic_year": 1}, "name")
	students = frappe.get_all(
		"Program Enrollment",
		filters={"program": program, "docstatus": 1, "academic_year": ac_yr, "custom_status": status},
		fields=["student"],
	)
	for student in students:
		try:
			if not frappe.db.exists("CBSE LOC", {"student": student.student}):
				doc = frappe.new_doc("CBSE LOC")
				doc.student = student.student
				doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(
				title="CBSE LOC Student Error", message=f"{student.student}\n{frappe.get_traceback()}"
			)
