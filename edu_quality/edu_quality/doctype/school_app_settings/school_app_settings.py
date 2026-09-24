# Copyright (c) 2026, Hybrowlabs Technologies and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class SchoolAppSettings(Document):
	def validate(self):
		for field in ("primary_color", "secondary_color", "ink_color"):
			value = self.get(field)
			if value and not HEX_COLOR.match(value):
				frappe.throw(
					_("{0} must be a six-digit hex colour such as #93342C.").format(
						self.meta.get_label(field)
					)
				)

	def on_update(self):
		from edu_quality.api.school_app import clear_branding_cache

		clear_branding_cache()
