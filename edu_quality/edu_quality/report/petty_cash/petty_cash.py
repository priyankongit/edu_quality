# Copyright (c) 2024, Hybrowlabs Technologies and contributors
# For license information, please see license.txt

from json import JSONDecodeError

import frappe
from erpnext.accounts.utils import get_balance_on
from frappe import _
from frappe.utils import add_days

TYPE_MAP = {"Payment": "Cash Entry", "Cash Withdrawal": "Bank Entry"}
REVERSE_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}


def execute(filters: dict | None = None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	return [
		create_column("Timestamp", "timestamp", "Datetime", 180),
		create_column("Voucher No", "voucher_no", "Link", 200, "Journal Entry"),
		create_column("Company", "company", "Link", 300, "Company"),
		create_column("Category", "category", "Data", 100),
		create_column("School", "school", "Link", 200, "School"),
		create_column("Head Type", "head_type", "Link", 200, "Account"),
		create_column("Type", "type", "Data", 150),
		create_column("Amount", "amount", "Currency", 100),
		create_column("To/From", "to_from", "Data", 150),
		create_column("Created By", "created_by", "Link", 200, "User"),
		create_column("Voucher Status", "voucher_status", "Data", 150),
		create_column("Attachment", "attachment", "Data", 100),
		create_column("Description", "description", "Data", 200),
	]


def create_column(label: str, fieldname: str, fieldtype: str, width: int, options: str = None) -> dict:
	column = {
		"label": _(label),
		"fieldname": fieldname,
		"fieldtype": fieldtype,
		"width": width,
	}
	if options:
		column["options"] = options
	return column


def get_data(filters) -> list[list]:
	base_filters = get_base_filters(filters)
	account = get_account(filters)
	journal_entries = fetch_journal_entries(base_filters)

	data = []
	for entry in journal_entries:
		entry_data = prepare_data_entry(entry)
		if entry_data:
			data.append(entry_data)

	if account:
		company = filters.get("company")
		start_date = filters.get("start_date")
		prev_date = add_days(start_date, -1)  # Get the previous day of the start date
		end_date = filters.get("end_date")  # Assuming you have an end_date filter
		add_balance_entry(data, account, company, prev_date, end_date)
	return data


def add_balance_entry(data, account, company, start_date, end_date) -> list:
	"""
	Add opening and closing balance entries to the data list
	"""
	if not data:
		return

	def create_balance_entry(company, balance_type, balance_amount):
		"""
		Create a balance entry with the specified balance
		"""
		entry = [""] * len(get_columns())
		entry[0] = frappe.utils.now()
		entry[2] = company
		entry[6] = balance_type
		entry[7] = balance_amount
		return entry

	opening_balance = get_balance_on(account, company=company, date=start_date)
	closing_balance = get_balance_on(account, company=company, date=end_date)

	opening_entry = create_balance_entry(company, "Opening Amount", opening_balance)
	closing_entry = create_balance_entry(company, "Closing Amount", closing_balance)

	data.insert(0, opening_entry)
	data.append(closing_entry)


def get_base_filters(filters) -> dict:
	base_filters = {"docstatus": ["in", [0, 1]], "is_petty_cash": 1}

	if filters.get("company"):
		base_filters["company"] = filters["company"]

	if filters.get("school"):
		base_filters["user_remark"] = ["like", f"%{filters['school']}%"]

	if filters.get("type"):
		base_filters["voucher_type"] = TYPE_MAP[filters["type"]]
	if filters.get("start_date"):
		base_filters["posting_date"] = [
			">=",
			filters["start_date"],
		]
	if filters.get("end_date"):
		base_filters["posting_date"] = [
			"<=",
			filters["end_date"],
		]
	if filters.get("start_date") and filters.get("end_date"):
		base_filters["posting_date"] = [
			"between",
			[filters["start_date"], filters["end_date"]],
		]
	if filters.get("show_only_draft"):
		base_filters["docstatus"] = 0

	return base_filters


def get_account(filters) -> str:
	if filters.get("school"):
		return frappe.get_value("School", filters["school"], "petty_cash_account")
	elif filters.get("company"):
		return frappe.get_value("Company", filters["company"], "default_petty_cash")
	return None


def fetch_journal_entries(base_filters) -> list:
	return frappe.get_all(
		"Journal Entry",
		fields=[
			"name",
			"voucher_type",
			"company",
			"owner",
			"user_remark",
			"total_debit",
			"pay_to_recd_from",
			"petty_cash_approved",
			"docstatus",
			"creation",
		],
		filters=base_filters,
		order_by="posting_date desc",
	)


def prepare_data_entry(entry) -> list:
	"""
	Prepare the data for the report
	Args:
	    entry (dict): Journal Entry document

	Returns:
	    list: List of data for the report
	"""
	try:
		user_remark = frappe.parse_json(entry.user_remark or "{}")
		file_url = frappe.get_value("File", {"attached_to_name": entry.name}, "file_url")
		attachment = f"<a href='{file_url}' target='_blank'>View</a>" if file_url else None
		doc_status = {0: "Draft", 1: "Submitted", 2: "Cancelled", 3: "Approved"}
		journal_entry_account = frappe.get_value(
			"Journal Entry Account", {"parent": entry.name, "credit": 0}, "account"
		)
		voucher_status = doc_status.get(entry.docstatus, "")
		if entry.petty_cash_approved and entry.docstatus == 0:
			voucher_status = "Approved"
		return [
			entry.creation,
			entry.name,
			entry.company,
			entry.voucher_type,
			user_remark.get("School"),
			journal_entry_account,
			REVERSE_TYPE_MAP[entry.voucher_type],
			entry.total_debit,
			entry.pay_to_recd_from,
			entry.owner,
			voucher_status,
			attachment,
			user_remark.get("Description"),
		]
	except JSONDecodeError:
		return []


@frappe.whitelist()
def handle_approval(data, approve: bool = False, reject: bool = False) -> bool:
	"""
	Handle the approval or rejection of petty cash entries

	Args:
	    data (str): JSON string of the entries to approve or reject
	    approve (bool): Whether to approve the entries
	    reject (bool): Whether to reject the entries

	Returns:
	    bool: True if successful, False otherwise

	If the document is in draft state, approve it. Else, delete it.
	"""
	try:
		data = frappe.parse_json(data)
		for entry in data:
			je = frappe.get_doc("Journal Entry", entry)
			if approve:
				je.petty_cash_approved = 1
				je.save()
			elif reject:
				if je.docstatus == 0:
					frappe.sendmail(
						recipients=frappe.get_cached_value("User", je.owner, "email"),
						subject=_("Petty Cash Entry Rejected"),
						message=_("Your petty cash entry has been rejected."),
						attachments=[frappe.attach_print("Journal Entry", je.name)],
					)
					frappe.delete_doc("Journal Entry", je.name)
		frappe.db.commit()
		return True
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			_(f"Error in approving/rejecting petty cash entries: {str(e)}"),
			frappe.get_traceback(),
		)
		return False
