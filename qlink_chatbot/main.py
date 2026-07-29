
import os

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from qlink_chatbot.database.db_utils import save_to_mongo, update_campaign_recipient_status
from qlink_chatbot.models.service_list import ServiceList
from qlink_chatbot.pipelines.inference_pipeline import (
    AgendaPipeline,
    GeneralPipeline,
    InitialPipeline,
    StallSponserPipeline,
    ScanQRPipeline,
    QuizPipeline
)
from qlink_chatbot.processors.response_manager import ResponseManager
from qlink_chatbot.utils.logger_config import logger

app = FastAPI(
    title="Qlink AAC-FSAI backend API",
    version="0.1.0",
    redoc_url=None,
    docs_url=None,
    openapi_url=None
)

from qlink_chatbot.routes.dashboard_routes import dashboard_router

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api/v1")

app.include_router(router=dashboard_router, prefix="/dashboard")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/ping")
def ping():
    """Ping endpoint to check if the server is running."""
    return {"message": "Qlink <> PAAC-FSAI backend API is up and running"}


@app.post("/gupshup/fsai/message")
async def messages(request: Request):
    """Message endpoint to send a message to the chatbot."""
    request_data = await request.json()
    logger.info("Request received with data", extra={"data": request_data})
    phone_number = None
    response_manager = ResponseManager()
    pipeline_data = None

    try:
        # Gupshup's native "V3" webhook format for message status events —
        # this is what our webhook subscription is actually registered as,
        # and it does NOT use the entry/changes/value shape below.
        # Shape: {"type": "message-event", "payload": {"id": ..., "type": "sent"|"delivered"|"read"|"failed", ...}}
        if request_data.get("type") == "message-event":
            event_payload = request_data.get("payload") or {}
            gupshup_message_id = event_payload.get("id")
            status = event_payload.get("type") or event_payload.get("status")

            logger.info(
                "V3 message-event webhook received",
                extra={"message_id": gupshup_message_id, "status": status},
            )

            if gupshup_message_id and status:
                matched = update_campaign_recipient_status(
                    gupshup_message_id, status
                )
                if matched:
                    logger.info(
                        "Campaign recipient status updated",
                        extra={
                            "message_id": gupshup_message_id,
                            "status": status,
                        },
                    )
            return {"status": "success"}

        if "payload" in request_data:
            logger.info("Payload found in request data, ignoring it")
            return None

        whatsapp_event = request_data["entry"][0]["changes"][0]["value"]

        # logger.info("Whatsapp event", extra={"whatsapp_event": whatsapp_event})

        if "statuses" in whatsapp_event:
            status_obj = whatsapp_event["statuses"][0]
            if "type" in status_obj:
                status = status_obj["type"]
            else:
                status = status_obj["status"]

            gupshup_message_id = status_obj.get("id")
            if gupshup_message_id:
                matched = update_campaign_recipient_status(
                    gupshup_message_id, status
                )
                if matched:
                    logger.info(
                        "Campaign recipient status updated",
                        extra={
                            "message_id": gupshup_message_id,
                            "status": status,
                        },
                    )

            logger.info(
                "Ignoring message with status", extra={"status": status}
            )
            return {"status": "success"}

        messages = whatsapp_event["messages"][0]
        phone_number = messages["from"]
        whatsapp_username = (
            request_data["entry"][0]["changes"][0]["value"]["contacts"][0][
                "profile"
            ]["name"]
            if "contacts" in request_data["entry"][0]["changes"][0]["value"]
            else ""
        )

        pipeline_data = {
            "phone_number": phone_number,
            "messages": messages,
            "whatsapp_username": whatsapp_username,
        }
        logger.info(
            "Data object to pipeline",
            extra={"data": pipeline_data, "phone_number": phone_number},
        )

        pipeline = InitialPipeline()
        pipeline_data = await pipeline.run(data=pipeline_data)

        if "bot_response" in pipeline_data:
            logger.info(
                "Bot response",
                extra={
                    "bot_response": pipeline_data["bot_response"],
                    "phone_number": phone_number,
                },
            )

            save_to_mongo(data=pipeline_data)
            response_manager.handle_responses(data=pipeline_data)

        else:
            logger.info(
                "Going to service selected pipeline",
                extra={
                    "phone_number": phone_number,
                    "service_selected": pipeline_data["user_profile"][
                        "service_selected"
                    ],
                },
            )
            user_profile = pipeline_data["user_profile"]

            if user_profile["service_selected"] == ServiceList.GENERAL.value:
                pipeline = GeneralPipeline()

            elif (
                user_profile["service_selected"] == ServiceList.AGENDA.value
            ):
                pipeline = AgendaPipeline()

            elif (
                user_profile["service_selected"] == ServiceList.STALL.value
            ):
                pipeline = StallSponserPipeline()

            elif (
                user_profile["service_selected"] == ServiceList.SCAN.value
            ):
                pipeline = ScanQRPipeline()
            
            elif user_profile["service_selected"] == ServiceList.QUIZ.value:
                pipeline = QuizPipeline()

            pipeline_data = await pipeline.run(data=pipeline_data)
            save_to_mongo(data=pipeline_data)
            response_manager.handle_responses(data=pipeline_data)


    except Exception as e:
        logger.exception(
            "Exception occured while running message endpoint",
            extra={"exception": e, "phone_number": phone_number},
        )
        if not phone_number:
            return {"status": "ignored", "reason": "no phone_number"}

        if pipeline_data is None:
            pipeline_data = {
                "phone_number": phone_number,
                "messages": {},
                "whatsapp_username": "",
            }

        pipeline_data["bot_response"] = [
            {
                "type": "text",
                "text": "Unexpected error occured.",
            }
        ]
        save_to_mongo(data=pipeline_data)
        response_manager.handle_responses(data=pipeline_data)

