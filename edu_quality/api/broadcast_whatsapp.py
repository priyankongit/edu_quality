import json
import re

import frappe
from frappe.utils import get_url

try:
	from nextai.utils import get_host_with_protocol
except ImportError:
	get_host_with_protocol = get_url

from edu_quality.public.py.utils import generate_fields_map

# queueing all the messages sequentially assuming on average it take some time for request to resolve


# edu_quality.api.broadcast_whatsapp.message
@frappe.whitelist()
def message(**data):
	members = data.get("members")
	message = data.get("message")
	current_url = get_host_with_protocol()
	if not members or not message:
		return "Members or message not found"
	for i in members:
		frappe.enqueue(
			"edu_quality.api.broadcast_whatsapp.send",
			member_lead_id=i.get("member_name"),
			message=message,
			current_url=current_url,
			# fields=trimmed_field_map,
			queue="long",
			timeout=1800,
		)
	return "Queued Successfully"


# for lead only
@frappe.whitelist()
def send(member_lead_id, message, current_url):
	lead_doc = frappe.get_doc("Lead", member_lead_id)
	# raise Exception(message)
	pattern = r"\{([^}]+)\}"
	template_data_array = json.loads(message.get("template_data"))
	replaced_template_data_array = [
		{
			"type": "text",
			"text": re.sub(
				pattern,
				lambda match: lead_doc.get(match.group(1), match.group(0)),
				i.get("text"),
			),
		}
		if i.get("type") == "text"
		else i
		for i in template_data_array
	]

	message_body = re.sub(
		pattern,
		lambda match: lead_doc.get(match.group(1), match.group(0)),
		message.get("message_body"),
	)
	message["template_data"] = json.dumps(replaced_template_data_array)
	message["message_body"] = message_body

	contact_doc_name = frappe.db.get_value(
		"Contact",
		{
			"first_name": lead_doc.first_name,
			"last_name": lead_doc.last_name,
			"email_id": lead_doc.fathers_email,
			"mobile_no": lead_doc.fathers_phone,
		},
		"name",
	)
	if not contact_doc_name:
		raise frappe.exceptions.MandatoryError("Cannot find any contact with the details provided")
	message["to"] = contact_doc_name
	message["doctype"] = "WhatsApp Message"
	message_doc = frappe.get_doc(message)
	message_doc.insert()

	if message_doc.get("media_file"):
		message_doc.upload_media()

	message_doc.send_templated_message(current_url)
