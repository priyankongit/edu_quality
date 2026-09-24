import datetime

import frappe
from education.education.doctype.student.student import Student
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_request.payment_request import get_gateway_details
from frappe.desk.query_report import run
from frappe.utils import getdate


class CustomStudent(Student):
	def autoname(self):
		if self.imported and self.reference_number:
			prefix = frappe.get_value("School", self.school, "prefix") or ""
			doc_name = prefix + self.reference_number
			self.name = doc_name
		elif self.reference_number:
			prefix = frappe.get_value("School", self.school, "prefix") or ""
			doc_name = prefix + self.reference_number
			self.name = doc_name
		elif self.student_applicant:
			applicant = frappe.get_doc("Student Applicant", self.student_applicant)
			prefix = frappe.get_value("School", applicant.school, "prefix")
			series = self.get_reference(applicant.academic_year)
			prefix += series
			ref_id = self.get_last_id(prefix)
			if ref_id == "max":
				prefix = prefix[:2]
				if series[1] != "Z":
					series = series[0] + chr(ord(series[1]) + 1)
				elif series[0] != "Z":
					series = chr(ord(series[0]) + 1) + "A"
				else:
					series = "A" + "A"
				frappe.db.set_value("Program", applicant.program, "reference_series", series)
				prefix = prefix + series + "01"
			else:
				prefix = prefix + ref_id
			self.name = prefix
			from edu_quality.edu_quality.server_scripts.utils import get_email_domain

			self.student_email_id = f"{self.name}@{get_email_domain()}"
			self.reference_number = self.name[2:]

	def get_reference(self, academic_year):
		previous_roll_no = not frappe.db.get_value(
			"Academic Year",
			{"custom_current_academic_year": 1},
			"rolled_over",
		)
		if frappe.db.get_value("Academic Year", academic_year, "custom_next_academic_year"):
			previous_roll_no = 1
		if previous_roll_no:
			current_program = frappe.get_doc("Program", self.program)
			previous_sequence = current_program.sequence - 1

			# Try to get the series based on the current program's school and previous sequence
			series = frappe.db.get_value(
				"Program",
				{"school": current_program.school, "sequence": previous_sequence},
				"reference_series",
			)

			# If series is not found, try to get it based on the previous class
			if not series:
				series = frappe.db.get_value("Program", current_program.previous_class, "reference_series")

			# If still not found, generate the series based on the current program's reference series
			if not series:
				series = current_program.reference_series
				series = chr(ord(series[0]) + 1) + series[1]
		else:
			series = frappe.db.get_value("Program", self.program, "reference_series")
		return series

	def get_last_id(self, prefix):
		val = frappe.db.get_all("Student", [["name", "Like", prefix + "%"]], "name", order_by="name")
		if val:
			series = int(val[-1].name[-2:])
			if series == 99:
				return "max"
			series += 1
			return str(series) if series > 9 else "0" + str(series)
		else:
			return "01"

	@frappe.whitelist()
	def get_academic_years(self):
		yr = []
		yr.append(frappe.db.get_value("Academic Year", {"custom_current_academic_year": 1}, "name"))
		yr.append(frappe.db.get_value("Academic Year", {"custom_next_academic_year": 1}, "name"))
		return yr

	@frappe.whitelist()
	def change_class(self, school, program, division):
		pass

	@frappe.whitelist()
	def create_student_exit(self):
		exit = frappe.new_doc("Student Exit")
		exit.student = self.name
		exit.academic_year = frappe.db.get_value("Academic Year", {"custom_current_academic_year": 1})
		exit.insert(ignore_permissions=True)
		return exit.name

	def validate_user(self):
		if not frappe.db.get_single_value(
			"Education Settings", "user_creation_skip"
		) and not frappe.db.exists("User", self.student_email_id):
			student_user = frappe.get_doc(
				{
					"doctype": "User",
					"first_name": self.first_name,
					"last_name": self.last_name,
					"email": self.student_email_id,
					"gender": self.gender,
					"send_welcome_email": 0,
					"user_type": "Website User",
				}
			)
			# Staff creating a student usually can't create Users; skip the check for this one
			# record rather than switching the whole session to Administrator.
			student_user.flags.ignore_permissions = True
			student_user.add_roles("Student")
			student_user.save(ignore_permissions=True)

			self.user = student_user.name

	@frappe.whitelist()
	def validate_bank_account(self):
		return frappe.db.exists("Bank Account", {"party": self.name})

	def cancel_related_documents(self, academic_year):
		# Cancel the program enrollment
		pe_filter = {"student": self.name, "academic_year": academic_year, "docstatus": 1}
		if frappe.db.exists("Program Enrollment", pe_filter):
			frappe.db.set_value("Program Enrollment", pe_filter, "docstatus", 2)

		# Cancel the student
		frappe.db.set_value("Student", self.name, {"enabled": 0, "student_status": "Cancelled"})

	@frappe.whitelist()
	def cancel_student(self, academic_year, fee_collection):
		try:
			self.cancel_related_documents(academic_year)
			if fee_collection == "Deposit Refund":
				if self.check_pending_fee():
					return frappe.throw(
						"Fee Collection is pending.for this student!\nGO to the fee document, generate pending links and collect the fees!"
					)
				return self.check_deposit()
			elif fee_collection == "Ignore Pending Fee":
				self.check_deposit()
				return self.reverse_pending_fees(academic_year)
			elif fee_collection == "Deduct from Deposit":
				return self.deduct_from_deposit()
			elif fee_collection == "Collect Partial Fee":
				return frappe.throw("Partial Fees Not Yet Implemented!")
			elif fee_collection == "Collect Full Fee":
				if self.check_pending_fee():
					return frappe.throw(
						"Fee Collection is pending.for this student!\nGO to the fee document, generate pending links and collect the fees!"
					)
				else:
					return frappe.msgprint("Fee Already collected! You can proceed with deposit refund!")

		except Exception as e:
			frappe.log_error(title="Cancel Error", message=frappe.get_traceback())
			frappe.throw(e)

	def check_pending_fee(self):
		if frappe.db.exists("Fees", {"student": self.name, "docstatus": "1", "outstanding_amount": [">", 0]}):
			return frappe.db.get_value(
				"Fees",
				{"student": self.name, "docstatus": "1", "outstanding_amount": [">", 0]},
				"outstanding_amount",
			)
		else:
			return 0

	def deduct_from_deposit(self):
		pending_fees = frappe.db.get_all(
			"Fees",
			filters=[
				["Fees", "docstatus", "=", "1"],
				["Fees", "student", "=", self.name],
				["Fees", "outstanding_amount", ">", 0],
			],
		)
		if len(pending_fees) > 1:
			return frappe.throw("More than one pending Fee Present!")
		pending_fees = pending_fees[0]
		pending_fee_doc = frappe.get_doc("Fees", pending_fees.name)
		deposit_fee, deposit_amount, deposit_account = self.check_deposit(deduct=1)
		if pending_fee_doc.outstanding_amount < deposit_amount:
			refund_amount = deposit_amount - pending_fee_doc.outstanding_amount
			self.refund_deposit(deposit_fee, refund_amount, deposit_account)
			deposit_fee_doc = frappe.get_doc("Fees", deposit_fee)
			deposit_fee_doc.deposit_adjustment_entry(pending_fee_doc.outstanding_amount)
		return pending_fee_doc.deduct_from_deposit(deposit_amount, deposit_account)

	def reverse_pending_fees(self, academic_year):
		fees_list = frappe.db.get_all(
			"Fees",
			filters=[
				["Fees", "docstatus", "=", "1"],
				["Fees", "student", "=", self.name],
				["Fees", "outstanding_amount", ">", 0],
				["Fees", "academic_year", "=", academic_year],
			],
		)
		for fee in fees_list:
			fee_doc = frappe.get_doc("Fees", fee.name)
			if fee_doc.outstanding_amount == fee_doc.grand_total:
				pr_list = frappe.db.get_all("Payment Request", {"reference_name": fee.name, "docstatus": 1})
				for pr in pr_list:
					pr_doc = frappe.get_doc("Payment Request", pr.name)
					pr_doc.cancel()
				fee_doc.cancel()
				return 1
			else:
				return fee_doc.reverse_pending_fees()

	def check_deposit(self, deduct=0):
		fees_list = frappe.db.get_all("Fees", filters={"docstatus": 1, "student": self.name})
		for fee in fees_list:
			if frappe.db.exists(
				"Fee Component", [["parent", "=", fee.name], ["fees_category", "like", "%DEPOSIT%"]]
			):
				deposit, account = frappe.db.get_value(
					"Fee Component",
					[["parent", "=", fee.name], ["fees_category", "like", "%DEPOSIT%"]],
					["amount", "label"],
				)
				deposit_paid = 0
				if frappe.db.exists(
					"Payment Request",
					[
						["Payment Request", "reference_name", "=", fee.name],
						["Payment Request", "payment_term", "is", "not set"],
						["Payment Request", "status", "=", "Paid"],
					],
				):
					deposit_paid = 1
				description, outstanding = frappe.db.get_value(
					"Payment Schedule",
					{"parent": fee.name, "payment_term": "Term 1"},
					["description", "outstanding"],
				)
				if "deposit" in description.lower() and outstanding == 0:
					deposit_paid = 1
				if deposit_paid:
					if deduct:
						return fee.name, deposit, account
					return self.refund_deposit(fee.name, deposit, account)

		return self.check_previous_deposits(deduct)

	def get_deposit_company(self):
		company = frappe.get_doc("Company", {"default_deposit_account": ["is", "set"]})
		return company

	def check_previous_deposits(self, deduct=0):
		company = self.get_deposit_company()
		filters = {
			"company": company.name,
			"from_date": "2024-01-01",
			"to_date": frappe.utils.nowdate(),
			"account": [company.default_deposit_account],
			"party_type": "Student",
			"party": [self.name],
			"party_name": self.name,
			"group_by": "Group by Voucher (Consolidated)",
			"cost_center": [],
			"school": [],
			"program": [],
			"project": [],
			"include_dimensions": 1,
			"include_default_book_entries": 1,
		}
		report = run(report_name="General Ledger", filters=filters, user="Administrator")
		balance = report["result"][0]["credit"]
		if balance > 0:
			if deduct:
				return None, balance, company.default_deposit_account
			else:
				return self.refund_deposit(None, balance, company.default_deposit_account)
		else:
			return frappe.throw("No Deposit Found!")

	def refund_deposit(self, fee, amount, account):
		company = self.get_deposit_company()
		student = self.name
		ref_doc = None
		if fee:
			ref_doc = frappe.get_doc("Fees", fee)
		pe = frappe.new_doc("Payment Entry")
		pe.update(
			{
				"naming_series": "ACC-PAY-.YYYY.-",
				"payment_type": "Pay",
				"payment_order_status": "Initiated",
				"posting_date": frappe.utils.nowdate(),
				"company": company.name,
				"paid_from_account_currency": "INR",
				"paid_to_account_currency": "INR",
				"status": "Draft",
				"letter_head": "Default letter head",
				"party_type": "Student",
				"party": self.name,
				"paid_from_account_type": "Bank",
				"paid_from": company.default_bank_account,
				"paid_to_account_type": "Payable",
				"paid_to": company.default_deposit_account,
				"paid_amount": amount,
				"base_paid_amount": amount,
				"received_amount": amount,
				"base_received_amount": amount,
				"unallocated_amount": amount,
				"difference_amount": 0,
				"total_allocated_amount": 0,
				"base_total_allocated_amount": 0,
				"reference_doctype": "Fees" if fee else "",
				"reference_name": fee if fee else "",
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"mode_of_payment": "Bank Draft",
			}
		)
		if ref_doc:
			for dimension in get_accounting_dimensions():
				pe.update({dimension: ref_doc.get(dimension)})

		pe.update(
			{
				"reference_no": fee if fee else "",
				"reference_date": frappe.utils.nowdate(),
			}
		)
		try:
			pe.insert(ignore_permissions=True)
			pe.submit()
			return 1
		except Exception as e:
			pass

	@frappe.whitelist()
	def mark_entry(self, status, reason=None, date=None, time=None):
		student = self.name
		if not date:
			date = getdate()
		if not time:
			time = datetime.datetime.now().strftime("%H:%M:%S")

		try:
			if frappe.db.exists("Attendance Entry", {"student": student, "date": date}):
				entry = frappe.get_doc("Attendance Entry", {"student": student, "date": date})
				entry.append(
					"absent_and_delays",
					{
						"reason": reason,
						"status": status,
						"timestamp": date + " " + time,
						"user": frappe.session.user,
					},
				)
				entry.flags.ignore_mandatory = True
				entry.save(ignore_permissions=True)
			else:
				entry = frappe.new_doc("Attendance Entry")
				entry.student = student
				entry.date = date
				entry.append(
					"absent_and_delays",
					{
						"reason": reason,
						"status": status,
						"timestamp": date + " " + time,
						"user": frappe.session.user,
					},
				)
				entry.insert(ignore_permissions=True)
			return True
		except Exception as e:
			frappe.log_error(title="Entry Error", message=frappe.get_traceback())
			return False

	@frappe.whitelist()
	def get_parents_details(self):
		parents = []
		for guardian in self.guardians:
			parent = frappe.get_doc("Guardian", guardian.guardian).as_dict()
			parent.update({"relation": guardian.relation})
			parents.append(parent)
		return parents

	@frappe.whitelist()
	def get_fees_details(self):
		class_id = frappe.get_value(
			"Program Enrollment",
			{"student": self.name, "docstatus": 1},
			"program",
			order_by="creation desc",
		)
		if class_id and frappe.get_value("Fees", {"student": self.name, "program": class_id, "docstatus": 1}):
			return frappe.get_doc("Fees", {"student": self.name, "program": class_id}).payment_schedule
		elif class_id and frappe.get_value(
			"Fee Advance", {"student": self.name, "program": class_id, "docstatus": 1}
		):
			doc = frappe.get_doc("Fee Advance", {"student": self.name, "program": class_id})
			invoice_portion = frappe.get_value(
				"Payment Schedule",
				{"parent": doc.payment_plan, "payment_term": doc.payment_term},
				"invoice_portion",
			)
			return [
				{
					"payment_term": doc.payment_term,
					"payment_amount": doc.amount,
					"due_date": doc.due_date,
					"invoice_portion": invoice_portion,
					"doctype": doc.doctype,
					"parent": doc.name,
					"paid_date": doc.paid_date,
					"description": "Installment 1",
					"outstanding": doc.outstanding_amount,
				}
			]
		return False

	@frappe.whitelist()
	def get_deposit_details(self):
		academic_year = frappe.db.get_value("Academic Year", {"custom_current_academic_year": 1})
		fee_filters = {
			"student": self.name,
			"academic_year": academic_year,
			"docstatus": 1,
		}

		if not frappe.db.exists("Fees", fee_filters):
			return False

		fee = frappe.get_doc("Fees", fee_filters)

		def get_deposit_payment_entry(payment_term):
			pe_filters = {
				"reference_name": fee.name,
				"docstatus": 1,
				"payment_term": payment_term,
			}
			return frappe.get_value("Payment Entry", pe_filters, ["name", "posting_date"], as_dict=True)

		def get_deposit_payment_request(payment_term):
			pr_filters = {
				"reference_name": fee.name,
				"docstatus": 1,
				"status": ["!=", "Paid"],
				"payment_term": payment_term,
			}
			return frappe.get_value("Payment Request", pr_filters, as_dict=True)

		for schedule in fee.payment_schedule:
			if "deposit" in schedule.description.lower():
				deposit_payment_entry = get_deposit_payment_entry(schedule.payment_term)
				if deposit_payment_entry:
					deposit_payment_entry["paid_amount"] = fee.get_deposit_amount()
					return [deposit_payment_entry]

				deposit_payment_request = get_deposit_payment_request(schedule.payment_term)
				if deposit_payment_request:
					deposit_payment_request["paid_amount"] = fee.get_deposit_amount()
					return [deposit_payment_request]

		# Check for unspecified payment term as a fallback
		deposit_payment_entry = get_deposit_payment_entry(None)
		if deposit_payment_entry:
			deposit_payment_entry["paid_amount"] = fee.get_deposit_amount()
			return [deposit_payment_entry]

		deposit_payment_request = get_deposit_payment_request(None)
		if deposit_payment_request:
			deposit_payment_request["paid_amount"] = fee.get_deposit_amount()
			return [deposit_payment_request]

		return False

	@frappe.whitelist()
	def get_hd_ticket_details(self):
		def get_refno(guardians):
			student = set(
				frappe.get_all(
					"Student Guardian",
					filters={"guardian": ["in", guardians], "parenttype": "Student"},
					pluck="parent",
				)
			)
			refno = frappe.get_all("Student", filters={"name": ["in", student]}, pluck="reference_number")
			return ",".join(list(map(str, refno)))

		guardian_names = [guardian.guardian for guardian in self.guardians]
		refno = get_refno(guardian_names)

		guardian_emails = frappe.get_all(
			"Guardian", filters={"name": ["in", guardian_names]}, pluck="email_address"
		)

		tickets = frappe.get_all(
			"HD Ticket",
			filters={"raised_by": ["in", guardian_emails]},
			fields=["name", "subject", "status"],
		)
		if tickets:
			for ticket in tickets:
				ticket["refno"] = refno
			return tickets
		return False

	def on_update(self, method=None):
		self.invalidate_walsh_cache()

	def invalidate_walsh_cache(self):
		for guardian in self.guardians:
			user = frappe.db.get_value("Guardian", {"name": guardian.guardian}, "user")
			students_key = f"walsh:guardian_students_{user}"

			if frappe.cache().get_value(students_key):
				frappe.cache().delete_value(students_key)
