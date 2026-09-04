import json
from datetime import datetime

import frappe
import qrcode
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_company_defaults,
	get_payment_entry,
)
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.accounts.utils import get_account_currency
from frappe.utils import flt, get_url, nowdate

try:
	from nextai.funnel.custom_trigger import trigger_event
except ImportError:

	def trigger_event(*args, **kwargs):
		frappe.log_error(
			title="Fee: nextai not installed",
			message="trigger_event was called but the 'nextai' app is not installed on this bench.",
		)


from edu_quality.edu_quality.server_scripts.payment_plan import (
	remove_payment_plan_discount,
)
from edu_quality.edu_quality.server_scripts.student_applicant import (
	referal_discount,
	update_referral_discount,
)
from edu_quality.fees.doctype.fee_advance.fee_advance import (
	cancel_liability_entries,
	get_one_time_discounts,
)
from edu_quality.overrides import make_payment_request
from edu_quality.public.py.discount import (
	add_discount,
	calculate_discount,
	get_all_discounts,
	get_label,
	payment_plan,
	remove_discount,
	time_based_discount,
	update_breakup_after_pp_change,
	update_payment_schedule,
)
from edu_quality.public.py.payment_request import update_payment_request_after_discount
from edu_quality.public.py.utils import (
	gen_qr_code_b64,
	gen_qr_code_b64_transparent,
	im_2_b64,
)


def after_insert(doc, method=None):
	payment_plan(doc)
	apply_referral_for_unpaid_fee_advance(doc)
	doc.reload()


def before_submit(doc, method=None):
	time_dis = time_based_discount(doc)
	ref_dis = referal_discount(doc)
	payplan_discount = update_payment_schedule(doc)
	doc.generate_split()

	# payment_split(doc, ref_dis, time_dis, payplan_discount)
	doc.total_discount = get_all_discounts(doc)


def on_submit(doc, method=None):
	filters = {
		"student": doc.student,
		"outstanding_amount": ["<=", 0],
		"next_program": doc.program,
		"academic_year": doc.academic_year,
		"docstatus": 1,
	}
	if frappe.db.exists("Fee Advance", filters):
		payment_amount = doc.payment_schedule[0].payment_amount
		fee_advance = frappe.get_doc("Fee Advance", filters)
		doc.payment_plan = fee_advance.payment_plan
		# cancel_liability_entries(fee_advance)
		discount_applied = get_one_time_discounts(fee_advance)
		for discount in discount_applied.keys():
			if "payplan" not in discount.lower():
				add_discount(doc.name, discount)
		if fee_advance.referral_amount:
			update_referral_discount(doc, fee_advance.referral_amount, True)
		if doc.payment_schedule:
			payment_schedule = doc.payment_schedule[0]
			frappe.db.set_value("Payment Schedule", payment_schedule.name, "outstanding", 0)
			term_first_amount = frappe.get_value("Payment Schedule", payment_schedule.name, "payment_amount")
			fee_outstanding_amount = max(0, doc.outstanding_amount - term_first_amount)
			frappe.db.set_value("Fees", doc.name, "outstanding_amount", fee_outstanding_amount)
		doc.reload()
	else:
		filters = {
			"student": doc.student,
			"outstanding_amount": [">", 0],
			"next_program": doc.program,
			"academic_year": doc.academic_year,
			"docstatus": 1,
		}
		fee_advance = frappe.get_value("Fee Advance", filters)
		if fee_advance:
			fee_advance = frappe.get_doc("Fee Advance", fee_advance)
			fee_advance.cancel()

	doc.generate_split()


# def update_referral_discount(doc, fee_advance):
#     if fee_advance.referral_amount:
#         for component in doc.components:
#             if component.fees_category in ["Tuition Fee", 'Tuition Fee (KG)']:
#                 fee_comp = frappe.get_value(
#                     "Fee Component", component.name, ["amount","custom_discount_amount", "custom_amount_after_discount","custom_discounts"], as_dict=True
#                 )
#                 discount_amount = fee_comp.custom_discount_amount + fee_advance.referral_amount
#                 if fee_comp.custom_discounts:
#                     fee_comp.custom_discounts += ", Referral"
#                 else:
#                     fee_comp.custom_discounts = "Referral"
#                 updates = {
#                     "custom_discount_amount": fee_comp.custom_discount_amount + fee_advance.referral_amount,
#                     "custom_amount_after_discount": fee_comp.custom_amount_after_discount - fee_advance.referral_amount,
#                     "custom_discount_percentage": calculate_discount(fee_comp.amount, discount_amount),
#                     "custom_discounts": fee_comp.custom_discounts
#                 }
#                 frappe.db.set_value("Fee Component", component.name, updates)
#                 doc.add_discount_entry(component.custom_company, fee_advance.referral_amount)
#         return fee_advance.referral_amount
#     return 0


def apply_referral_for_unpaid_fee_advance(doc):
	total_discount = 0
	filters = {
		"student": doc.student,
		"outstanding_amount": [">", 0],
		"next_program": doc.program,
		"academic_year": doc.academic_year,
		"docstatus": 1,
	}
	fee_advance = frappe.get_value("Fee Advance", filters)
	if fee_advance:
		fee_advance = frappe.get_doc("Fee Advance", filters)
		fee_advance.reload()
		doc.payment_plan = fee_advance.payment_plan
		doc.save()
		doc.reload()
		discount_applied = get_one_time_discounts(fee_advance)
		for discount in discount_applied.keys():
			if "payplan" not in discount.lower():
				add_discount(doc.name, discount)

		if fee_advance.referral_amount:
			update_referral_discount(doc, fee_advance.referral_amount)
		return fee_advance


def verify_invoice_portion(payment_schedule):
	total_portion = sum([ps.invoice_portion for ps in payment_schedule])
	if total_portion != 100:
		frappe.throw(title="Payment Schedule", msg="Total Invoice Portion must be 100%")


def verify_payment_term(payment_schedule):
	terms = []
	for ps in payment_schedule:
		if ps.payment_term in terms:
			frappe.throw(title="Payment Schedule", msg="Duplicate Terms not allowed")
		else:
			terms.append(ps.payment_term)


def validate_discounts(doc):
	for component in doc.components:
		if "Payment Plan" in component.custom_discounts:
			frappe.throw("Remove Payment Plan Discount to customize payment plan!")


def custom_payment_plan(doc):
	try:
		return
		remove_payment_plan_discount(doc, custom_payment_plan=1)
		doc.save()
		update_breakup_after_pp_change(doc)
		update_payment_request_after_discount(doc)
	except Exception as e:
		frappe.log_error(title="Custom Error", message=frappe.get_traceback())


def after_save(doc, method=None):
	return
	from edu_quality.public.py.discount import update_total_discount_in_fees

	update_total_discount_in_fees(doc)


def on_update(doc, method=None):
	old_doc = doc.get_doc_before_save()
	if old_doc.payment_plan != doc.payment_plan:
		return

	if doc.parent_otp == 0 and old_doc.payment_schedule != doc.payment_schedule:
		if old_doc.payment_plan == doc.payment_plan:
			doc.need_otp = 1
			custom_payment_plan(doc)
			return

	if old_doc.payment_plan != doc.payment_plan:
		# update_breakup_after_pp_change(doc)
		# update_payment_request_after_discount(doc)
		return
	verify_invoice_portion(doc.payment_schedule)
	verify_payment_term(doc.payment_schedule)
	if old_doc.payment_schedule != doc.payment_schedule:
		for term, old_term in zip(doc.payment_schedule, old_doc.payment_schedule, strict=False):
			if old_term.outstanding == 0 and term.outstanding != 0:
				frappe.throw("Cannot Change term - " + term.payment_term + " As it is already Paid!")
			if term.invoice_portion:
				term.payment_amount = (term.invoice_portion * doc.grand_total) / 100
			elif term.payment_amount:
				term.invoice_portion = (term.payment_amount / doc.grand_total) * 100

		payment_schedule = doc.payment_schedule
		doc.payment_schedule = []
		old_payment_plan = frappe.get_doc("Payment Plan", doc.payment_plan)

		for i, ps in enumerate(payment_schedule):
			amount = (ps.invoice_portion * doc.grand_total) / 100
			description = f"Installment {i+1}"
			deposit = get_deposit(old_doc.payment_schedule, old_payment_plan.payment_schedule)

			# if it is 1st term and deposit in previous payment schedule is not 0
			if i == 0 and deposit != 0:
				description += " and Deposit"
				amount += deposit

			doc.append(
				"payment_schedule",
				{
					"payment_term": ps.payment_term,
					"description": description,
					"invoice_portion": ps.invoice_portion,
					"payment_amount": amount,
					"outstanding": amount,
					"due_date": ps.due_date,
				},
			)
		update_payment_request_after_discount(doc)


def get_deposit(doc_payment_plan, payment_plan):
	if "deposit" in doc_payment_plan[0].description.lower():
		return doc_payment_plan[0].payment_amount - payment_plan[0].payment_amount
	return 0


def sync_student_data(doc, method=None):
	student = frappe.get_value(
		"Student",
		doc.student,
		["has_allergies", "allergies", "is_handicap", "handicap", "student_status"],
		as_dict=True,
	)
	doc.has_allergies = student.has_allergies
	doc.allergies = student.allergies
	doc.is_handicap = student.is_handicap
	doc.handicap = student.handicap
	doc.custom_status = student.student_status


def create_id_card(doc, method=None):
	student = frappe.get_doc("Student", doc.student)
	qrcode_image = gen_qr_code_b64_transparent(
		f"{doc.get('academic_year')}/{doc.get('custom_school')}/{student.get('reference_number')}"
	)
	id_card = frappe.get_doc(
		{
			"doctype": "Student ID Card",
			"program_enrolled_in": doc.name,
			"qr_code": qrcode_image,
		}
	)
	id_card.insert()
	frappe.db.set_value("Program Enrollment", doc.name, "custom_id_card", id_card.name)
	doc.reload()


def create_fees(doc, method=None):
	try:
		student = frappe.get_doc("Student", doc.student)
		if student.imported and student.student_status not in [
			"Cancelled",
			"New student",
		]:
			existing_pe = frappe.get_all("Program Enrollment", {"student": doc.student, "docstatus": 1})
			if len(existing_pe) <= 1:
				return
		fee_structure_filters = {"program": doc.program, "academic_year": doc.academic_year, "docstatus": 1}
		if student.student_category:
			fee_structure_filters["student_category"] = student.student_category

		fee_structure = frappe.get_value("Fee Structure", fee_structure_filters, "name")
		fee_schedule = frappe.get_value(
			"Fee Schedule", {"fee_structure": fee_structure, "docstatus": 1}, "name"
		)
		if student.student_applicant:
			stude_appli_class = student.student_applicant
		else:
			stude_appli_class = frappe.get_value(
				"Student Applicant",
				{"student_email_id": student.student_email_id, "program": doc.program},
				"name",
			)
		if not stude_appli_class:
			fee_data = {
				"doctype": "Fees",
				"student": student.name,
				"posting_date": nowdate(),
				"program_enrollment": doc.name,
				"fee_structure": fee_structure,
				"fee_schedule": fee_schedule,
				"academic_year": doc.academic_year,
				"custom_school": doc.custom_school,
				"company": frappe.get_value("Fee Structure", fee_structure, "institution"),
			}
			fee = frappe.get_doc(fee_data)
			fee_structure = frappe.get_doc("Fee Structure", fee_structure)
			for component in fee_structure.components:
				fee.append(
					"components",
					{
						"fees_category": component.fees_category,
						"amount": component.amount,
						"description": component.description,
						"custom_company": component.custom_company,
						"school": component.school,
						"label": component.label,
					},
				)
			fee.insert()
			fee.submit()
			from edu_quality.public.py.student import update_student_group

			update_student_group(doc.name, fee_structure=fee_structure.name)
		else:
			student_applicant = frappe.get_doc("Student Applicant", stude_appli_class)
			fees = frappe.get_doc(
				{
					"doctype": "Fees",
					"student": student.name,
					"posting_date": nowdate(),
					"program_enrollment": frappe.get_value(
						"Program Enrollment",
						{"student": doc.student, "program": doc.program},
						"name",
					),
					"fee_structure": student_applicant.fee_structure,
					"fee_schedule": student_applicant.fee_schedule,
					"academic_year": student_applicant.academic_year,
					"custom_school": student_applicant.school,
					"company": student_applicant.institution,
				}
			)
			if len(student_applicant.fee_components) > 0:
				for component in student_applicant.fee_components:
					fees.append(
						"components",
						{
							"fees_category": component.fees_category,
							"amount": component.amount,
							"description": component.description,
							"custom_company": component.custom_company,
							"school": component.school,
							"label": component.label,
						},
					)
			else:
				fee_structure = frappe.get_doc("Fee Structure", student_applicant.fee_structure)
				for component in fee_structure.components:
					fees.append(
						"components",
						{
							"fees_category": component.fees_category,
							"amount": component.amount,
							"description": component.description,
							"custom_company": component.custom_company,
							"school": component.school,
							"label": component.label,
						},
					)
			fees.insert()
			fees.submit()
			from edu_quality.public.py.student import update_student_group

			update_student_group(fees.program_enrollment, fee_structure=student_applicant.fee_structure)
		student.custom_school = doc.custom_school
		student.save()
		update_lead_status(doc)
	except Exception as e:
		frappe.log_error(title="Fee Error", message=frappe.get_traceback())
		frappe.throw(str(e))


def update_lead_status(doc, method=None):
	student_applicant = frappe.get_value("Student", doc.student, "student_applicant")
	if student_applicant:
		lead = frappe.get_value("Student Applicant", student_applicant, "lead")
		frappe.set_value("Lead", lead, "status", "Enrolled")


def append_program_enrollment(doc, method=None):
	return


def remove_program_enrollment(doc, method=None):
	try:
		student = frappe.get_doc("Student", doc.student)
		for i, program_enrollment in enumerate(student.class_details):
			if program_enrollment.program_enrollment == doc.name:
				student.class_details.remove(student.class_details[i])
				student.save()
				return
	except Exception as e:
		frappe.throw(str(e))


@frappe.whitelist()
def get_due_date(fee):
	fee = frappe.get_doc("Fees", fee)
	due_date = ""
	for term in fee.payment_schedule:
		if not due_date:
			due_date = term.due_date
		if frappe.db.exists(
			"Payment Request",
			{"payment_term": term.payment_term, "reference_name": fee.name},
		):
			due_date = term.due_date
	return due_date


def payment_split(doc, ref_dis=None, time_dis=None, payplan_discount=0):
	"""
	ref_dis: referal discount
	time_dis: time based discount
	payplan_discount: discount from payment plan
	"""
	split_payments = dict()
	company_wise_split = dict()
	component_wise_split = dict()
	if doc.doctype == "Fees":
		if doc.payment_schedule:
			for schedule in doc.payment_schedule:
				term = schedule.payment_term
				due_date = schedule.due_date
				invoice_portion = schedule.invoice_portion
				if "deposit" in schedule.description:
					split_payments[term] = get_split_payment(doc, invoice_portion, True)
					company_wise_split[term] = company_wise(doc, invoice_portion, True)
					component_wise_split[term] = component_wise(doc, due_date, invoice_portion, True)
				else:
					split_payments[schedule.payment_term] = get_split_payment(doc, invoice_portion)
					company_wise_split[term] = company_wise(doc, invoice_portion)
					component_wise_split[term] = component_wise(doc, due_date, invoice_portion)

			if ref_dis:
				(
					split_payments,
					company_wise_split,
					component_wise_split,
				) = update_splits(
					split_payments,
					company_wise_split,
					component_wise_split,
					dis=ref_dis,
					term=1,
				)
			if time_dis:
				(
					split_payments,
					company_wise_split,
					component_wise_split,
				) = update_splits(
					split_payments,
					company_wise_split,
					component_wise_split,
					dis=time_dis,
					term=1,
				)
			if payplan_discount:
				(
					split_payments,
					company_wise_split,
					component_wise_split,
				) = update_splits(
					split_payments,
					company_wise_split,
					component_wise_split,
					doc,
					payplan_discount,
					term=-1,
				)
		company_wise_split["Deposit"] = company_wise_deposit(doc)
		split_payments["Deposit"] = get_split_payment(doc, 100, False, True)
		component_wise_split["Deposit"] = component_wise(doc, doc.due_date, 100, False, True)

	elif doc.doctype == "Fee Advance":
		if isinstance(doc.due_date, str):
			doc.due_date = datetime.strptime(doc.due_date, "%Y-%m-%d").date()
		split_payments[doc.payment_term] = get_split_payment(doc, 100)
		company_wise_split[doc.payment_term] = company_wise(doc, 100)
		component_wise_split[doc.payment_term] = component_wise(doc, doc.due_date, 100)

	doc.split_payments = json.dumps(split_payments)
	doc.company_split = json.dumps(company_wise_split)
	doc.component_split = json.dumps(component_wise_split)


def update_splits(
	split_payments,
	company_wise_split=None,
	component_wise_split=None,
	doc=None,
	payplan_discount=None,
	dis=None,
	term=None,
):
	"""
	subtract payplan_discount amount from split payment in the last term from the respected account
	if the time or referral discount then substract from 1st term
	"""
	try:
		if payplan_discount and doc and term == -1:
			for component in doc.components:
				dis_filter = {
					"payment_plan": doc.payment_plan,
					"fee_structure": doc.fee_structure,
					"enabled": 1,
					"fee_category": component.fees_category,
				}
				fees_category = frappe.db.get_value("Discount Configuration", dis_filter, "fee_category")
				if fees_category:
					label = get_label(fees_category)

					last_term = list(split_payments.keys())[-1]
					last_term_split = split_payments[last_term]
					last_term_split[label] -= payplan_discount
					split_payments[last_term] = last_term_split
					company_wise_split = update_company_wise_split(
						company_wise_split=company_wise_split,
						fee_category=fees_category,
						payplan_discount=payplan_discount,
					)
					component_wise_split = update_component_wise_split(
						component_wise_split=component_wise_split,
						fee_category=fees_category,
						payplan_discount=payplan_discount,
					)

					return split_payments, company_wise_split, component_wise_split

		elif dis and term == 1 and company_wise_split:
			label = next(iter(dis)).split("-")[0].strip()
			discount_amount = list(dis.get(label).values())[0]

			first_term = next(iter(split_payments))
			first_term_split = split_payments.get(first_term, {})
			first_term_split[label] = first_term_split.get(label, 0) - discount_amount
			split_payments[first_term] = first_term_split
			company_wise_split = update_company_wise_split(company_wise_split=company_wise_split, dis=dis)
			component_wise_split = update_component_wise_split(
				component_wise_split=component_wise_split, dis=dis
			)
			return split_payments, company_wise_split, component_wise_split

	except Exception as e:
		frappe.log_error(title="UpdateSplits Error", message=frappe.get_traceback())
		return split_payments, company_wise_split, component_wise_split


def update_company_wise_split(company_wise_split, fee_category=None, payplan_discount=None, dis=None):
	"""
	subtract payplan discount amount from company split in the Last term from the respected account from fee category,
	if the time or referral discount then substract from 1st term
	"""
	if not company_wise_split:
		return company_wise_split

	term_keys = list(company_wise_split.keys())
	last_term, first_term = term_keys[-1], term_keys[0]

	if payplan_discount and fee_category:
		term_split = company_wise_split[last_term]
	elif dis:
		label = next(iter(dis)).split("-")[0].strip()
		fee_dis = dis.get(label)
		fee_category, payplan_discount = (
			list(fee_dis.keys())[0],
			list(fee_dis.values())[0],
		)
		term_split = company_wise_split.get(first_term, {})
	else:
		return company_wise_split

	for split in term_split:
		for fee in split.get("fee_categories"):
			if fee_category in fee:
				split["amount"] -= payplan_discount
				fee[fee_category] -= payplan_discount
				return company_wise_split

	return company_wise_split


def update_component_wise_split(component_wise_split, fee_category=None, payplan_discount=None, dis=None):
	"""
	subtract payplan discount amount from component split in the Last term from the respected account from fee category,
	if the time or referral discount then substract from 1st term
	"""
	if not component_wise_split:
		return component_wise_split

	term_keys = list(component_wise_split.keys())
	last_term, first_term = term_keys[-1], term_keys[0]

	if payplan_discount and fee_category:
		term_split = component_wise_split[last_term]
	elif dis:
		label = next(iter(dis)).split("-")[0].strip()
		fee_dis = dis.get(label)
		fee_category, payplan_discount = (
			list(fee_dis.keys())[0],
			list(fee_dis.values())[0],
		)
		term_split = component_wise_split.get(first_term, {})
	else:
		return component_wise_split

	for item in term_split["breakup"]:
		if fee_category in item.values():
			amount = frappe.utils.flt(item["amount"].split(" ")[1])
			amount -= payplan_discount
			item["amount"] = frappe.utils.fmt_money(amount, currency="INR")
			return component_wise_split

	return component_wise_split


def get_split_payment(doc, portion, combination=False, only_deposit=False):
	split_payment = {}
	remaining_amount = 0
	default_account = frappe.get_value("Fees Settings", None, "default_account").split("-")[0].strip()
	if doc.components:
		invoice_portion = portion
		for component in doc.components:
			if not only_deposit:
				fee_type = frappe.db.get_value("Fee Category", component.fees_category, "type")
				if fee_type != "Regular" and invoice_portion != 100 and combination:
					amount = component.amount
					label = frappe.get_value("Fee Category", component.fees_category, "custom_label")
				elif fee_type == "Regular" and invoice_portion != 100 and combination:
					amount = (invoice_portion / 100) * component.amount
					label = frappe.get_value("Fee Category", component.fees_category, "custom_label")
				elif fee_type == "Regular" and not combination:
					amount = (invoice_portion / 100) * component.amount
					label = frappe.get_value("Fee Category", component.fees_category, "custom_label")
				else:
					continue

				if label:
					label = label.split("-")[0].strip()
					split_payment[label] = split_payment.get(label, 0) + amount
				else:
					remaining_amount += amount
			else:
				fee_type = frappe.db.get_value("Fee Category", component.fees_category, "type")
				if fee_type != "Regular":
					amount = component.amount
					label = frappe.get_value("Fee Category", component.fees_category, "custom_label")
				else:
					continue

				if label:
					label = label.split("-")[0].strip()
					split_payment[label] = split_payment.get(label, 0) + amount
				else:
					remaining_amount += amount
	elif doc.doctype == "Fee Advance":
		remaining_amount = doc.amount

	split_payment[default_account] = split_payment.get(default_account, 0) + remaining_amount
	return split_payment


def company_wise(fees, invoice_portion, combination=False):
	paid_from_dict = {}
	paid_to_dict = {}
	companies = {}
	fee_categories = {}
	for component in fees.components:
		doc = frappe.get_doc("Fee Category", component.fees_category)
		company = doc.custom_company
		paid_to = frappe.get_value("Company", company, "default_easebuzz_account")
		paid_from = frappe.get_value("Company", company, "default_receivable_account")
		fee_type = frappe.db.get_value("Fee Category", component.fees_category, "type")
		amount = component.amount
		if fee_type != "Regular" and combination is True:
			amount = flt(amount, 2)
		elif fee_type == "Regular":
			amount = flt((invoice_portion / 100) * amount, 2)

		if paid_from_dict.get(paid_from):
			if fee_type != "Regular" and combination is True:
				paid_from_dict[paid_from] += amount
				fee_categories[paid_from].append({component.fees_category: amount})
			elif fee_type == "Regular":
				paid_from_dict[paid_from] += amount
				fee_categories[paid_from].append({component.fees_category: amount})
		else:
			if fee_type != "Regular" and combination is True:
				paid_from_dict[paid_from] = amount
				fee_categories[paid_from] = [{component.fees_category: amount}]
			elif fee_type == "Regular":
				paid_from_dict[paid_from] = amount
				fee_categories[paid_from] = [{component.fees_category: amount}]
		paid_to_dict[paid_from] = paid_to
		companies[paid_from] = company

	company_wise_split = []
	for paid_from, amount in paid_from_dict.items():
		cost_center = frappe.get_value("Cost Center", {"company": companies[paid_from]}, ["name"])
		company_wise_split.append(
			{
				"amount": amount,
				"paid_from": paid_from,
				"paid_to": paid_to_dict[paid_from],
				"company": companies[paid_from],
				"cost_center": cost_center,
				"fee_categories": fee_categories[paid_from],
			}
		)
	return company_wise_split


def company_wise_deposit(fees):
	paid_from_dict = {}
	paid_to_dict = {}
	companies = {}
	fee_categories = {}
	for component in fees.components:
		doc = frappe.get_doc("Fee Category", component.fees_category)
		company = doc.custom_company
		paid_to = frappe.get_value("Company", company, "default_easebuzz_account")
		paid_from = frappe.get_value("Company", company, "default_receivable_account")
		fee_type = frappe.db.get_value("Fee Category", component.fees_category, "type")
		amount = component.amount

		if fee_type != "Regular":
			if paid_from_dict.get(paid_from):
				paid_from_dict[paid_from] += amount
				fee_categories[paid_from].append({component.fees_category: amount})
			else:
				paid_from_dict[paid_from] = amount
				fee_categories[paid_from] = [{component.fees_category: amount}]
		paid_to_dict[paid_from] = paid_to
		companies[paid_from] = company

	company_wise_split = []
	for paid_from, amount in paid_from_dict.items():
		cost_center = frappe.get_value("Cost Center", {"company": companies[paid_from]}, ["name"])
		company_wise_split.append(
			{
				"amount": amount,
				"paid_from": paid_from,
				"paid_to": paid_to_dict[paid_from],
				"company": companies[paid_from],
				"cost_center": cost_center,
				"fee_categories": fee_categories[paid_from],
			}
		)
	return company_wise_split


def component_wise(doc, due_date, invoice_portion, combination=False, only_deposit=False):
	component_wise_split = dict()
	breakup = []
	for component in doc.components:
		if not only_deposit:
			fee_type = frappe.db.get_value("Fee Category", component.fees_category, "type")
			amount = component.amount
			if fee_type != "Regular" and combination is True:
				amount = (frappe.utils.fmt_money(amount, currency="INR"),)
				breakup.append(
					{
						"fees_category": component.fees_category,
						"company": component.custom_company,
						"amount": amount,
					}
				)
			elif fee_type == "Regular":
				amount = flt((invoice_portion / 100) * amount, 2)
				breakup.append(
					{
						"fees_category": component.fees_category,
						"company": component.custom_company,
						"amount": frappe.utils.fmt_money(amount, currency="INR"),
					}
				)
		else:
			fee_type = frappe.db.get_value("Fee Category", component.fees_category, "type")
			amount = component.amount
			if fee_type != "Regular":
				amount = (frappe.utils.fmt_money(amount, currency="INR"),)
				breakup.append(
					{
						"fees_category": component.fees_category,
						"company": component.custom_company,
						"amount": amount,
					}
				)
	due_date = due_date.strftime("%Y-%m-%d") if due_date else None
	component_wise_split["due_date"] = due_date
	component_wise_split["breakup"] = breakup
	component_wise_split["is_deposit"] = combination
	return component_wise_split


def create_birthday_card(self, method=None):
	if frappe.db.exists("Birthday Card", {"program_enrollment": self.name}):
		name = frappe.db.get_value("Birthday Card", {"program_enrollment": self.name}, "name")
		return frappe.get_doc("Birthday Card", name)

	return frappe.get_doc({"doctype": "Birthday Card", "program_enrollment": self.name}).insert(
		ignore_permissions=True
	)


def collect_birthday_details_on_submit(self, method=None):
	try:
		birthday_card = create_birthday_card(self, None)
		trigger_event(doc=birthday_card, event_name="collect_birthday_details")
	except Exception as e:
		frappe.log_error(title="CollectBirthdayCardDetailsEmail Error", message=frappe.get_traceback())
