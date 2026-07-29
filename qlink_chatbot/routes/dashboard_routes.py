
import json
import os
import re

import pandas as pd
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from starlette.requests import Request

from qlink_chatbot.database.db_utils import (
    get_all_docs_dashboard,
    get_call_by_id,
    get_doc_by_id,
    get_recent_calls,
    get_recent_docs,
    list_calls,
    return_kb_prompt,
    return_system_prompt,
    update_kb_prompt,
    update_system_prompt,
    set_venue_entry_flag,
    get_all_attendees,
    get_all_stalls,
    add_attendee,
    delete_attendee,
    update_attendee,
    get_stalls_by_ids,
    get_attendees_by_user_ids,
    get_attendees_by_stall_id,
    get_attendee_by_id,
    get_stall_by_id,
    list_sessions,
    get_sessions_by_ids,
    get_session_by_id,
    get_similar_attendees_by_phone,
    get_attendees_by_session_id,
    get_all_sessions_feedback_analytics,
    get_event_analytics,
    create_campaign,
    set_campaign_recipient_sent,
    get_all_campaigns,
    get_campaign_by_id,
    get_all_leads,
    get_lead_category_counts,
)
from qlink_chatbot.database.collections import attendee, leads
from qlink_chatbot.utils.env_load import password as pwd
from qlink_chatbot.utils.env_load import username as us
from qlink_chatbot.utils.logger_config import logger
from qlink_chatbot.whatsapp_functions.calls.send_call import send_call
from qlink_chatbot.whatsapp_functions.dashboard.create_template import (
    create_template,
    upload_template_media,
)
from qlink_chatbot.whatsapp_functions.dashboard.delete_template import (
    delete_template_by_name,
)
from qlink_chatbot.whatsapp_functions.dashboard.get_all_templates import (
    get_all_templates,
)
from qlink_chatbot.whatsapp_functions.dashboard.send_template_by_id import (
    send_template_message,
)


class LoginData(BaseModel):
    username: str
    password: str

class SystemPromptUpdate(BaseModel):
    prompt: str

class KBPromptUpdate(BaseModel):
    kb: dict

dashboard_router = APIRouter()

@dashboard_router.get("/ping")
def ping():
    """General Ping."""
    try:
        logger.info("dashboard Ping Received")
        return JSONResponse({"success":True}, status_code=201)
    except Exception as e:
        logger.info("Error Occured in dashboard ping", extra={"error": e})
        return JSONResponse({
            "success": False, "message": str(e)
        }, status_code=501)
    
@dashboard_router.post("/login")
def login(data: LoginData):
    """Dashboard Login."""  
    username = data.username
    password = data.password
    try:
        if not password or not username:
            return JSONResponse({"success":False, "message": "Invalid Request"}, status_code=401)
        elif (
            username != us or password != pwd
        ):
            return JSONResponse({"success":False, "message": "Invalid Username or Password"}, status_code=402)
        else:
            return JSONResponse({"success":True}, status_code=201)
    except Exception as e:
        logger.info("Error Occured in login", extra={"error": e})
        return JSONResponse({
            "success": False, "message": str(e)
        }, status_code=501)
    
@dashboard_router.get("/chat/all")
async def fetch_all_docs(page: int = 1, limit: int = 20):
    """Fetch all docs with only _id, phone_number, created_at — latest first."""
    try:
        docs = get_all_docs_dashboard(page=page, limit=limit)
        return JSONResponse(
            content={"success": True, "data": docs},
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error fetching all docs", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching documents"},
            status_code=500,
        )
    
@dashboard_router.get("/chat/{doc_id}")
async def fetch_doc_by_id(doc_id: str):
    """Fetch a document by its _id."""
    try:
        doc = get_doc_by_id(doc_id)
        if not doc:
            return JSONResponse(
                content={"success": False, "message": "Document not found"},
                status_code=404,
            )
        
        return JSONResponse(
            content={"success": True, "data": doc},
            status_code=200,
        )
    except Exception as e:
        logger.exception(
            "Error fetching doc by id", extra={"exception": e, "_id": doc_id}
        )
        return JSONResponse(
            content={"success": False, "message": "Error fetching document"},
            status_code=500,
        )
    
@dashboard_router.get("/chat/template/all")
async def fetch_all_templates():
    """Routes to fetch all templates"""
    try:
        doc = get_all_templates()
        if not doc:
            return JSONResponse(
                content={"success": False, "message": "Error fetching Templates."},
                status_code=401,
            )
        
        return JSONResponse(
            content={"success": True, "data": doc},
            status_code=200,
        )
    except Exception as e:
        logger.exception(
            "Error fetching templates", extra={"exception": e}
        )
        return JSONResponse(
            content={"success": False, "message": "Error fetching Templates."},
            status_code=500,
        )
    
TEMPLATE_CATEGORIES = {"UTILITY", "MARKETING", "AUTHENTICATION"}
LEAD_CATEGORIES = {
    "all_leads",
    "corporate_member",
    "individual_member",
    "life_member",
    "other_member",
}
ATTENDEE_CATEGORIES = {"all", "office_bearers", "sponsor", "vip", "spouse"}
ELEMENT_NAME_RE = re.compile(r"^[a-z0-9_]+$")
TEMPLATE_IMAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static",
    "templates",
)
PUBLIC_BASE_URL = "https://api.do2.qlink.in"


@dashboard_router.post("/chat/template")
async def create_template_route(
    element_name: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    example: str = Form(...),
    language_code: str = Form("en"),
    header: str | None = Form(None),
    footer: str | None = Form(None),
    buttons: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    """Create a new WhatsApp template and submit it to Gupshup for approval.

    `buttons`, if provided, is a JSON string: [{"text": "...", "url": "..."}, ...]
    """
    try:
        if not ELEMENT_NAME_RE.match(element_name):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "element_name must be lowercase_snake_case (letters, numbers, underscores only)",
                },
                status_code=400,
            )

        if category not in TEMPLATE_CATEGORIES:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"category must be one of {sorted(TEMPLATE_CATEGORIES)}",
                },
                status_code=400,
            )

        gupshup_payload = {
            "elementName": element_name,
            "languageCode": language_code,
            "category": category,
            "content": content,
            "example": example,
            "vertical": element_name,
        }

        if header:
            gupshup_payload["header"] = header
        if footer:
            gupshup_payload["footer"] = footer

        if buttons:
            try:
                button_list = json.loads(buttons)
            except json.JSONDecodeError:
                return JSONResponse(
                    content={"success": False, "message": "buttons must be valid JSON"},
                    status_code=400,
                )

            gupshup_buttons = [
                {
                    "type": "URL",
                    "text": b["text"],
                    "url": b["url"],
                    "example": [b["url"]],
                }
                for b in button_list
                if b.get("text") and b.get("url")
            ]
            if gupshup_buttons:
                gupshup_payload["buttons"] = json.dumps(gupshup_buttons)

        file_bytes = None
        if image is not None:
            file_bytes = await image.read()
            handle = upload_template_media(
                file_bytes, image.filename, image.content_type
            )
            gupshup_payload["templateType"] = "IMAGE"
            gupshup_payload["exampleMedia"] = handle
        else:
            gupshup_payload["templateType"] = "TEXT"

        result = create_template(gupshup_payload)

        if result.get("status") != "success":
            return JSONResponse(
                content={
                    "success": False,
                    "message": result.get("message", "Template creation failed"),
                },
                status_code=400,
            )

        template_data = result.get("template") or {}

        # Persist the header image locally so it has a stable, public URL we
        # can reference when actually sending this template later — the
        # media handle from upload_template_media above is only valid for
        # Gupshup's approval-time preview, not for real sends.
        if file_bytes is not None and template_data.get("id"):
            ext = os.path.splitext(image.filename or "")[1] or ".jpg"
            os.makedirs(TEMPLATE_IMAGE_DIR, exist_ok=True)
            with open(
                os.path.join(TEMPLATE_IMAGE_DIR, f"{template_data['id']}{ext}"),
                "wb",
            ) as f:
                f.write(file_bytes)

        return JSONResponse(
            content={"success": True, "data": template_data},
            status_code=201,
        )

    except Exception as e:
        logger.exception("Error creating template", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error creating template"},
            status_code=500,
        )


@dashboard_router.delete("/chat/template/{template_name}")
async def delete_templates(template_name: str):
    """Routes to fetch all templates"""
    try:
        doc = delete_template_by_name(template_name=template_name)
        if not doc:
            return JSONResponse(
                content={"success": False, "message": "Error deleting Templates."},
                status_code=401,
            )
        
        return JSONResponse(
            content={"success": True},
            status_code=200,
        )
    except Exception as e:
        logger.exception(
            "Error deleting templates", extra={"exception": e}
        )
        return JSONResponse(
            content={"success": False, "message": "Error deleting Templates."},
        )
    
@dashboard_router.get("/call/all")
async def fetch_all_calls(page: int = 1, limit: int = 20):
    """Fetch all ca;;s with only _id, phone_number, created_at — latest first."""
    try:
        docs = list_calls(page=page, limit=limit)
        return JSONResponse(
            content={"success": True, "data": docs},
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error fetching all calls", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching calls"},
            status_code=500,
        )
    
@dashboard_router.get("/call/{doc_id}")
async def fetch_call_by_id(doc_id: str):
    """Fetch a call by its _id."""
    try:
        doc = get_call_by_id(doc_id)
        if not doc:
            return JSONResponse(
                content={"success": False, "message": "Call not found"},
                status_code=404,
            )
        
        return JSONResponse(
            content={"success": True, "data": doc},
            status_code=200,
        )
    except Exception as e:
        logger.exception(
            "Error fetching call by id", extra={"exception": e, "_id": doc_id}
        )
        return JSONResponse(
            content={"success": False, "message": "Error fetching Call"},
            status_code=500,
        )
    
@dashboard_router.get("/recents")
@dashboard_router.get("/analytics/recents")  # legacy alias; ad-blockers may block /analytics/
async def fetch_recents_data():
    """Get all recents calls and docs."""
    try:
        doc = get_recent_docs()
        calls = get_recent_calls()

        if not doc and not calls:
            return JSONResponse(
                content={"success": False, "message": "recents data not found"},
                status_code=404,
            )
        
        return JSONResponse(
            content={"success": True, "data": {
                "doc": doc,
                "call": calls
            }},
            status_code=200,
        )
    except Exception as e:
        logger.exception(
            "Error fetching recents", extra={"exception": e}
        )
        return JSONResponse(
            content={"success": False, "message": "Error fetching recents"},
            status_code=500,
        )
    
@dashboard_router.get("/prompt/system")
async def get_system_prompt():
    """Get system prompt."""
    try:
        prompt = return_system_prompt()
        return JSONResponse(
            content={"success": True, "data": prompt},
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error fetching system prompt", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching system prompt"},
            status_code=500,
        )


@dashboard_router.put("/prompt/system")
async def update_system_prompt_route(data: SystemPromptUpdate):
    """Update system prompt."""
    try:
        updated = update_system_prompt(data.prompt)
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "System prompt not updated"},
                status_code=400,
            )

        return JSONResponse(
            content={"success": True},
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error updating system prompt", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error updating system prompt"},
            status_code=500,
        )


@dashboard_router.get("/prompt/kb")
async def get_kb_prompt():
    """Get knowledge base prompt."""
    try:
        kb = return_kb_prompt()
        return JSONResponse(
            content={"success": True, "data": kb},
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error fetching kb prompt", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching kb prompt"},
            status_code=500,
        )


@dashboard_router.put("/prompt/kb")
async def update_kb_prompt_route(data: KBPromptUpdate):
    """Update knowledge base prompt."""
    try:
        updated = update_kb_prompt(data.kb)
        if not updated:
            return JSONResponse(
                content={"success": False, "message": "KB prompt not updated"},
                status_code=400,
            )

        return JSONResponse(
            content={"success": True},
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error updating kb prompt", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error updating kb prompt"},
            status_code=500,
        )
    
class PhoneItem(BaseModel):
    phone_code: str
    phone_number: str


@dashboard_router.post("/template/trigger/{template_id}")
async def trigger_campaign_v2(
    request: Request,
    template_id: str,
    file: UploadFile = File(None),
    phone_numbers: str | None = Form(None),
    phone_codes: str | None = Form(None),
    category: str | None = Form(None),
    sub_category: str | None = Form(None),
):
    try:
        records = []

        # If category selected
        if category:
            if category in LEAD_CATEGORIES:
                query: dict = {}
                if category != "all_leads":
                    query["category"] = category
                if sub_category:
                    query["sub_category"] = sub_category
                lead_docs = list(
                    leads.find(query, {"contact_number": 1, "_id": 0})
                )
                records = [
                    {"phone_code": "", "phone_number": lead["contact_number"]}
                    for lead in lead_docs
                ]
            elif category == "all":
                attendees = list(
                    attendee.find(
                        {},
                        {"contact_number": 1, "_id": 0}
                    )
                )
                records = [
                    {"phone_code": "", "phone_number": a["contact_number"]}
                    for a in attendees
                ]
            else:
                attendees = list(
                    attendee.find(
                        {"category": category},
                        {"contact_number": 1, "_id": 0}
                    )
                )
                records = [
                    {"phone_code": "", "phone_number": a["contact_number"]}
                    for a in attendees
                ]

        # If file uploaded
        elif file:
            if file.filename.endswith(".xlsx"):
                df = pd.read_excel(file.file, engine="openpyxl")
            elif file.filename.endswith(".xls"):
                df = pd.read_excel(file.file, engine="xlrd")
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Invalid file format"},
                )

            records = df[["phone_code", "phone_number"]].to_dict(orient="records")

        # Manual numbers
        elif phone_numbers and phone_codes:
            numbers = phone_numbers.split(",")
            codes = phone_codes.split(",")

            if len(numbers) != len(codes):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Length mismatch"},
                )

            records = [
                {"phone_code": c, "phone_number": n}
                for c, n in zip(codes, numbers)
            ]

        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Provide file, phone list or category"},
            )

        phones = [
            r["phone_number"] if category else f"{r['phone_code']}{r['phone_number']}"
            for r in records
        ]

        all_templates = get_all_templates() or []
        template_name = next(
            (t["elementName"] for t in all_templates if t.get("id") == template_id),
            template_id,
        )

        campaign_id = create_campaign(template_id, template_name, phones)

        # If this template was created with a header image, it was saved
        # locally at creation time — build its public URL so the send
        # actually attaches the header image instead of silently failing.
        # Uses a hardcoded public domain rather than request.base_url, since
        # that can resolve to an internal address depending on how TLS
        # termination/proxying in front of the server is configured.
        image_url = None
        if os.path.isdir(TEMPLATE_IMAGE_DIR):
            for filename in os.listdir(TEMPLATE_IMAGE_DIR):
                if os.path.splitext(filename)[0] == template_id:
                    image_url = f"{PUBLIC_BASE_URL}/static/templates/{filename}"
                    logger.info(
                        "Resolved header image for campaign trigger",
                        extra={"template_id": template_id, "image_url": image_url},
                    )
                    break

        # SEND LOOP
        success, failed = 0, []

        for phone in phones:
            try:
                rsp = send_template_message(phone, template_id, image_url=image_url)
                set_campaign_recipient_sent(
                    campaign_id, phone, rsp["message_id"], rsp["success"]
                )
                if rsp["success"]:
                    success += 1
                else:
                    failed.append({
                        "phone": phone,
                        "error": rsp.get("error") or "Send failed",
                    })
            except Exception as e:
                set_campaign_recipient_sent(campaign_id, phone, None, False)
                failed.append({"phone": phone, "error": str(e)})

        return JSONResponse(
            status_code=200,
            content={
                "success": success > 0,
                "campaign_id": campaign_id,
                "total": len(records),
                "sent": success,
                "failed": failed,
                "message": (
                    "No messages were accepted by WhatsApp. Check failed numbers or template status."
                    if success == 0
                    else None
                ),
            },
        )

    except Exception as e:
        logger.error("error occured while sending campaign", extra={"error": e})
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Error triggering campaign"},
        )


@dashboard_router.get("/campaigns")
async def fetch_all_campaigns():
    """List all campaigns with summary delivery stats."""
    try:
        data = get_all_campaigns()
        return JSONResponse(content={"success": True, "data": data}, status_code=200)
    except Exception as e:
        logger.exception("Error fetching campaigns", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching campaigns"},
            status_code=500,
        )


@dashboard_router.get("/campaigns/{campaign_id}")
async def fetch_campaign_by_id(campaign_id: str):
    """Get full campaign detail including per-recipient delivery status."""
    try:
        data = get_campaign_by_id(campaign_id)
        if not data:
            return JSONResponse(
                content={"success": False, "message": "Campaign not found"},
                status_code=404,
            )
        return JSONResponse(content={"success": True, "data": data}, status_code=200)
    except Exception as e:
        logger.exception("Error fetching campaign", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching campaign"},
            status_code=500,
        )


@dashboard_router.post("/call/trigger")
async def trigger_call_v2(
    file: UploadFile = File(None),
    phone_numbers: str | None = Form(None),
    phone_codes: str | None = Form(None),
):
    try:
        records = []

        if file:
            if file.filename.endswith(".xlsx"):
                df = pd.read_excel(file.file, engine="openpyxl")
            elif file.filename.endswith(".xls"):
                df = pd.read_excel(file.file, engine="xlrd")
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Invalid file format"},
                )
            
            records = df[["phone_code", "phone_number"]].to_dict(orient="records")

        elif phone_numbers and phone_codes:
            numbers = phone_numbers.split(",")
            codes = phone_codes.split(",")

            if len(numbers) != len(codes):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Length mismatch"},
                )

            records = [
                {"phone_code": c, "phone_number": n}
                for c, n in zip(codes, numbers)
            ]

        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Provide file or phone list"},
            )

        success, failed = 0, []

        for r in records:
            phone = f"{r['phone_code']}{r['phone_number']}"
            try:
                rsp = send_call(phone)
                if rsp:
                    success += 1
                else:
                    failed.append({"phone": phone, "error": str(e)})
            except Exception as e:
                failed.append({"phone": phone, "error": str(e)})

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "total": len(records),
                "sent": success,
                "failed": failed,
            },
        )

    except Exception as e:
        logger.error("error occured while sending campaign", extra={"error": e})
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Error triggering campaign"},
        )


@dashboard_router.get("/leads")
async def fetch_all_leads():
    try:
        data = get_all_leads()
        return JSONResponse(content={"success": True, "data": data}, status_code=200)
    except Exception as e:
        logger.exception("Error fetching leads", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching leads"},
            status_code=500,
        )


@dashboard_router.get("/leads/categories")
async def fetch_lead_category_counts():
    try:
        data = get_lead_category_counts()
        return JSONResponse(content={"success": True, "data": data}, status_code=200)
    except Exception as e:
        logger.exception("Error fetching lead categories", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching lead categories"},
            status_code=500,
        )


@dashboard_router.get("/attendees")
async def fetch_all_attendees():
    try:
        attendees = get_all_attendees()
        return JSONResponse(
            content={"success": True, "data": attendees},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error fetching attendees"},
            status_code=500
        )
    
@dashboard_router.get("/stalls")
async def fetch_all_stalls():
    try:
        stalls = get_all_stalls()
        return JSONResponse(
            content={"success": True, "data": stalls},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error fetching stalls"},
            status_code=500
        )

@dashboard_router.post("/attendees/by-ids")
async def fetch_attendees_by_ids(request: Request):
    try:
        payload = await request.json()
        user_ids = payload.get("user_ids", [])

        attendees = get_attendees_by_user_ids(user_ids)
        return JSONResponse(
            content={"success": True, "data": attendees},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error fetching attendees"},
            status_code=500
        )


@dashboard_router.post("/stalls/by-ids")
async def fetch_stalls_by_ids(request: Request):
    try:
        payload = await request.json()
        stall_ids = payload.get("stall_ids", [])

        stalls = get_stalls_by_ids(stall_ids)
        return JSONResponse(
            content={"success": True, "data": stalls},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error fetching stalls"},
            status_code=500
        )
    
@dashboard_router.get("/attendees/by-stall/{stall_id}")
async def fetch_attendees_by_stall(stall_id: str):
    try:
        attendees = get_attendees_by_stall_id(stall_id)
        return JSONResponse(
            content={"success": True, "data": attendees},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error fetching attendees"},
            status_code=500
        )
    
@dashboard_router.get("/attendee/{user_id}")
async def fetch_attendee_by_id(user_id: str):
    try:
        attendee = get_attendee_by_id(user_id)
        if not attendee:
            return JSONResponse(
                content={"success": False, "message": "Attendee not found"},
                status_code=404
            )

        return JSONResponse(
            content={"success": True, "data": attendee},
            status_code=200
        )
    except Exception:
        return JSONResponse(
            content={"success": False, "message": "Error fetching attendee"},
            status_code=500
        )


@dashboard_router.get("/stall/{stall_id}")
async def fetch_stall_by_id(stall_id: str):
    try:
        stall = get_stall_by_id(stall_id)
        if not stall:
            return JSONResponse(
                content={"success": False, "message": "Stall not found"},
                status_code=404
            )

        return JSONResponse(
            content={"success": True, "data": stall},
            status_code=200
        )
    except Exception:
        return JSONResponse(
            content={"success": False, "message": "Error fetching stall"},
            status_code=500
        )




@dashboard_router.post("/attendee")
async def create_attendee(request: Request):
    try:
        payload = await request.json()


        success = add_attendee(payload)
        if not success:
            return JSONResponse(
                content={"success": False, "message": "Attendee already exists"},
                status_code=400
            )

        return JSONResponse(
            content={"success": True, "message": "Attendee added successfully"},
            status_code=201
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error adding attendee"},
            status_code=500
        )
    
@dashboard_router.patch("/attendee/venue-entry")
async def update_venue_entry(phone_number: str, flag: bool):
    try:
        success = set_venue_entry_flag(phone_number=phone_number, flag=flag)
        if not success:
            return JSONResponse(
                content={"success": False, "message": "Attendee not found"},
                status_code=404
            )

        return JSONResponse(
            content={"success": True, "message": "Venue entry updated"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error updating venue entry"},
            status_code=500
        )
    

@dashboard_router.patch("/attendee/{user_id}")
async def update_attendee_route(user_id: str, request: Request):
    try:
        payload = await request.json()

        success = update_attendee(user_id=user_id, update_data=payload)
        if not success:
            return JSONResponse(
                content={"success": False, "message": "Attendee not found"},
                status_code=404
            )

        return JSONResponse(
            content={"success": True, "message": "Attendee updated successfully"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error updating attendee"},
            status_code=500
        )


@dashboard_router.delete("/attendee/{user_id}")
async def delete_attendee_route(user_id: str):
    try:
        success = delete_attendee(user_id=user_id)
        if not success:
            return JSONResponse(
                content={"success": False, "message": "Attendee not found"},
                status_code=404
            )

        return JSONResponse(
            content={"success": True, "message": "Attendee deleted successfully"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": "Error deleting attendee"},
            status_code=500
        )

@dashboard_router.get("/sessions")
async def fetch_all_sessions():
    """List all sessions."""
    try:
        data = list_sessions()
        return JSONResponse(
            content={"success": True, "data": data},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching sessions", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching sessions"},
            status_code=500
        )


@dashboard_router.get("/session/{session_id}")
async def fetch_session_by_id(session_id: int):
    """Get full session details by session_id (integer)."""
    try:
        doc = get_session_by_id(session_id)
        if not doc:
            return JSONResponse(
                content={"success": False, "message": "Session not found"},
                status_code=404
            )
        return JSONResponse(
            content={"success": True, "data": doc},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching session", extra={"exception": e, "session_id": session_id})
        return JSONResponse(
            content={"success": False, "message": "Error fetching session"},
            status_code=500
        )


@dashboard_router.get("/session/{session_id}/attendees")
async def fetch_attendees_by_session(session_id: int):
    """Get all attendees who visited a given session."""
    try:
        attendees = get_attendees_by_session_id(session_id)
        return JSONResponse(
            content={"success": True, "data": attendees},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching attendees for session", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching attendees"},
            status_code=500
        )


@dashboard_router.get("/attendees/similar-by-phone")
async def fetch_similar_attendees(phone_number: str):
    """Get attendees who share visited sessions with the given phone number."""
    try:
        similar = get_similar_attendees_by_phone(phone_number)
        return JSONResponse(
            content={"success": True, "data": similar},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching similar attendees", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching similar attendees"},
            status_code=500
        )


@dashboard_router.post("/sessions/by-ids")
async def fetch_sessions_by_ids(request: Request):
    """Get sessions by a list of session_id integers."""
    try:
        payload = await request.json()
        session_ids = payload.get("session_ids", [])
        sessions = get_sessions_by_ids(session_ids)
        return JSONResponse(
            content={"success": True, "data": sessions},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching sessions by IDs", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching sessions"},
            status_code=500
        )

@dashboard_router.get("/sessions/feedback-summary")
@dashboard_router.get("/sessions/feedback-analytics")  # legacy alias; ad-blockers may block /analytics/
async def fetch_feedback_analytics():
    """Aggregated feedback analytics for all sessions."""
    try:
        data = get_all_sessions_feedback_analytics()
        return JSONResponse(
            content={"success": True, "data": data},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching feedback analytics", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching feedback analytics"},
            status_code=500
        )


@dashboard_router.get("/event-overview")
@dashboard_router.get("/analytics/event")  # legacy alias; ad-blockers may block /analytics/
async def fetch_event_analytics():
    """Comprehensive event analytics across all collections."""
    try:
        data = get_event_analytics()
        return JSONResponse(
            content={"success": True, "data": data},
            status_code=200
        )
    except Exception as e:
        logger.exception("Error fetching event analytics", extra={"exception": e})
        return JSONResponse(
            content={"success": False, "message": "Error fetching event analytics"},
            status_code=500
        )