import json
import os

import frappe

from edu_quality.edu_quality.overrides.company import ACCOUNT_HEADS, create_account_head


def after_install():
	create_default_roles()
	companies = frappe.get_all("Company", pluck="name")
	for company in companies:
		for account_head in ACCOUNT_HEADS:
			create_account_head(
				account_head["account_name"],
				account_head["parent_account_name"],
				company,
			)


def create_default_roles():
	"""Ensure app-specific roles referenced in permissions/customizations exist.

	The Custom DocPerm fixture replaces standard permissions (e.g. Notification Log's "All")
	with rows for roles like Teacher and Principal. If those roles are missing, nobody but
	System Manager can open the affected doctypes, so create every role the fixture uses.
	Runs after install and after every migrate.
	"""
	for role_name in {"School Admin", *_fixture_roles()}:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def _fixture_roles():
	path = frappe.get_app_path("edu_quality", "fixtures", "custom_docperm.json")
	if not os.path.exists(path):
		return set()
	with open(path) as f:
		return {row["role"] for row in json.load(f) if row.get("role")}
