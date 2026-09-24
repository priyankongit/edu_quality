# Copyright (c) 2026, Hybrowlabs Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class Homework(Document):
	def validate(self):
		if self.due_date and self.assigned_on and getdate(self.due_date) < getdate(self.assigned_on):
			frappe.throw(_("Due date can't be before the date it was assigned."))
