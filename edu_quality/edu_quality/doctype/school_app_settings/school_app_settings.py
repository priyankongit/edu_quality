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

		self._publish_brand_files()
		clear_branding_cache()

	def _publish_brand_files(self):
		"""The logo and app icon are shown on the sign-in screen and used as the PWA icon, so
		guests must be able to load them. Uploaded attachments default to private (a 403 for a
		signed-out visitor, which is why the login circle is blank), so mark them public.

		Handles logo and app_icon pointing at the same file, and a field still holding the old
		/private URL of a file that an earlier save already moved to public."""
		remap: dict[str, str] = {}
		for field in ("logo", "app_icon"):
			url = self.get(field)
			if not url or url in remap:
				continue
			try:
				name = frappe.db.get_value("File", {"file_url": url}, "name")
				if not name:
					public = url.replace("/private/files/", "/files/", 1)
					if public != url and frappe.db.exists("File", {"file_url": public}):
						remap[url] = public
					continue
				file = frappe.get_doc("File", name)
				if file.is_private:
					file.is_private = 0
					file.save(ignore_permissions=True)  # rewrites the URL to /files
				remap[url] = file.file_url
			except Exception:
				frappe.log_error(title="Could not publish brand file", message=frappe.get_traceback())

		for field in ("logo", "app_icon"):
			url = self.get(field)
			if url and remap.get(url) and remap[url] != url:
				self.db_set(field, remap[url], update_modified=False)
