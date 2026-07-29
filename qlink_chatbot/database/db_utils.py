import time
from collections import defaultdict
from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from qlink_chatbot.database.collections import (
    appoinments,
    git,
    idac,
    pims_calls,
    pims_systems,
    attendee,
    stall,
    session,
    campaigns,
    leads,
)
from qlink_chatbot.utils.format_chathistory import format_chat_history
from qlink_chatbot.utils.logger_config import logger

from uuid import uuid4


def mongo_search(query, collection):
    """Executes a MongoDB search based on a given query."""
    try:
        logger.debug("Executing MongoDB search", extra={"query": query})
        results = list(collection.find(query))
        logger.info("Found results of length", extra={"length": len(results)})
        return results

    except Exception as e:
        logger.exception("MongoDB search failed:", extra={"exception": e})
        raise e


def save_to_mongo(data):
    """Saves the data to a MongoDB collection."""
    try:
        logger.info(
            "Request received to save user profile with data",
            extra={"phone_number": data["phone_number"]},
        )
        query = data["messages"]
        
        assistant = data["bot_response"] if "bot_response" in data else None
        phone_number = data["phone_number"]
        user_profile_data = data["user_profile"]

        new_chat = format_chat_history(
            user=query, assistant=assistant, phone_number=phone_number
        )

        current_history = user_profile_data.get("chat_history", [])
        user_profile_data["chat_history"] = current_history + new_chat
        user_profile_data["updated_at"] = datetime.now()
        user_profile_data["username"] = data["whatsapp_username"]

        response = idac.find_one_and_update(
            {"phone_number": phone_number},
            {"$set": user_profile_data},
            upsert=True,  # Insert if document doesn't exist
            return_document=ReturnDocument.AFTER,
        )

        logger.info(
            "User profile saved successfully",
            extra={
                "response_id": response.get("_id"),
                "phone_number": phone_number,
            },
        )
        response.pop("_id")
        return response
    except Exception as e:
        logger.exception(
            "MongoDB save failed:",
            extra={"exception": e, "phone_number": phone_number},
        )
        raise e
    
def git_save_to_mongo(data):
    """Saves the data to a MongoDB collection."""
    try:
        logger.info(
            "Request received to save user profile with data",
            extra={"phone_number": data["phone_number"]},
        )
        query = data["messages"]
        
        assistant = data["bot_response"] if "bot_response" in data else None
        phone_number = data["phone_number"]
        user_profile_data = data["user_profile"]

        new_chat = format_chat_history(
            user=query, assistant=assistant, phone_number=phone_number
        )

        current_history = user_profile_data.get("chat_history", [])
        user_profile_data["chat_history"] = current_history + new_chat
        user_profile_data["updated_at"] = datetime.now()
        user_profile_data["username"] = data["whatsapp_username"]

        response = git.find_one_and_update(
            {"phone_number": phone_number},
            {"$set": user_profile_data},
            upsert=True,  # Insert if document doesn't exist
            return_document=ReturnDocument.AFTER,
        )

        logger.info(
            "User profile saved successfully",
            extra={
                "response_id": response.get("_id"),
                "phone_number": phone_number,
            },
        )
        response.pop("_id")
        return response
    except Exception as e:
        logger.exception(
            "MongoDB save failed:",
            extra={"exception": e, "phone_number": phone_number},
        )
        raise e


def save_user_profile(phone_number: str, profile_data: dict):
    """Saves data to user profile collection."""
    try:
        logger.info(
            "Request received to save user profile with data",
            extra={"profile_data": profile_data, "phone_number": phone_number},
        )
        profile_data["created_at"] = datetime.now()
        profile_data["updated_at"] = datetime.now()

        response = idac.find_one_and_update(
            {"phone_number": phone_number},
            {"$set": profile_data},
            upsert=True,  # Insert if document doesn't exist
            return_document=True,
        )

        logger.info(
            "User profile saved successfully",
            extra={
                "response_id": response.get("_id"),
                "phone_number": phone_number,
            },
        )
        response.pop("_id")
        return response
    except Exception as e:
        logger.exception(
            "MongoDB save failed:",
            extra={"exception": e, "phone_number": phone_number},
        )
        raise e


def get_user_profile(phone_number: str):
    """Get User Profile data."""
    try:
        profile = idac.find_one({"phone_number": phone_number})

        if not profile:
            logger.exception(
                "No profile exists for phone number.",
                extra={"phone_number": phone_number},
            )
            return None

        return profile
    except Exception as e:
        logger.exception(
            "Exception occured while fetching user profile.",
            extra={"phone_number": phone_number},
        )
        raise e


def get_doc_by_id(doc_id: str):
    """Fetch a document by its _id and return a clean structured dict."""
    try:
        doc = idac.find_one({"_id": ObjectId(doc_id)})
        if not doc:
            logger.warning(
                "No document found for given ID", extra={"_id": doc_id}
            )
            return None

        new_doc = {
            "_id": str(doc["_id"]),
            "phone_number": doc.get("phone_number", ""),
            "username": doc.get("username", ""),
            "chat_history": doc.get("chat_history", []),
            "service_selected": doc.get("service_selected", ""),
            "updated_at": (
                doc["updated_at"].isoformat()
                if isinstance(doc.get("updated_at"), datetime)
                else doc.get("updated_at")
            ),
            "find_doctor": doc.get("Find a Doctor", 0),
            "direction": doc.get("Direction", 0),
            "contact_us": doc.get("Contact Us", 0),
            "book_an_appointment": doc.get("Book an Appointment", 0),
            "other": doc.get("Other", 0),
        }

        return new_doc

    except Exception as e:
        logger.exception(
            "Error fetching document by ID",
            extra={"exception": e, "_id": doc_id},
        )
        raise e


def get_all_docs():
    """Return all docs."""
    try:
        docs = list(
            idac.find(
                {},
                {
                    "_id": 1,
                    "phone_number": 1,
                    "updated_at": 1,
                    "username": 1,
                    "chat_history": 1,
                },
            ).sort("updated_at", -1)
        )
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            doc["updated_at"] = (
                doc["updated_at"].isoformat()
                if isinstance(doc.get("updated_at"), datetime)
                else doc.get("updated_at")
            )
            doc["total_interaction"] = len(doc.get("chat_history", [])) // 2
            doc.pop("chat_history", None)
        return docs
    except Exception as e:
        logger.exception(
            "Error fetching all document summaries", extra={"exception": e}
        )
        raise e
    
# get all docs
def get_all_docs_dashboard(page: int = 1, limit: int = 20):
    """Return paginated docs with total pages."""
    try:
        skip = (page - 1) * limit

        total_docs = idac.count_documents({})
        total_pages = (total_docs + limit - 1) // limit

        docs = list(
            idac.find(
                {},
                {
                    "_id": 1,
                    "phone_number": 1,
                    "updated_at": 1,
                    "username": 1,
                    "chat_history": 1,
                },
            )
            .sort("updated_at", -1)
            .skip(skip)
            .limit(limit)
        )

        for doc in docs:
            doc["_id"] = str(doc["_id"])
            doc["updated_at"] = (
                doc["updated_at"].isoformat()
                if isinstance(doc.get("updated_at"), datetime)
                else doc.get("updated_at")
            )
            doc["total_interaction"] = len(doc.get("chat_history", [])) // 2
            doc.pop("chat_history", None)

        return {
            "page": page,
            "limit": limit,
            "total_docs": total_docs,
            "total_pages": total_pages,
            "docs": docs,
        }

    except Exception as e:
        logger.exception(
            "Error fetching all document summaries",
            extra={"exception": e}
        )
        raise e

# get recent docs  
def get_recent_docs(limit: int = 5):
    """Return the most recent docs."""
    try:
        docs = list(
            idac.find(
                {},
                {
                    "_id": 1,
                    "phone_number": 1,
                    "updated_at": 1,
                    "username": 1,
                    "chat_history": 1,
                },
            )
            .sort("updated_at", -1)
            .limit(limit)
        )

        for doc in docs:
            doc["_id"] = str(doc["_id"])
            doc["updated_at"] = (
                doc["updated_at"].isoformat()
                if isinstance(doc.get("updated_at"), datetime)
                else doc.get("updated_at")
            )
            doc["total_interaction"] = len(doc.get("chat_history", [])) // 2
            doc.pop("chat_history", None)

        return docs

    except Exception as e:
        logger.exception(
            "Error fetching recent docs", extra={"exception": e}
        )
        raise e


def get_full_analytics():
    """Generate complete analytics including interactions, unsubscribe, and site visit data."""
    try:
        docs = list(idac.find({}))
        if not docs:
            return {"success": False, "message": "No data found"}

        total_users = len(docs)
        total_interactions = 0
        service_counts = defaultdict(int)
        user_activity = []
        unsubscribed_users = []
        site_visit_users = []

        for doc in docs:
            chat_history = doc.get("chat_history", [])
            chat_len = (
                len(chat_history) // 2
            )  # user + assistant = 1 interaction
            total_interactions += chat_len

            username = doc.get("username", "")
            phone_number = doc.get("phone_number", "")
            user_activity.append(
                {
                    "username": username,
                    "phone_number": phone_number,
                    "interactions": chat_len,
                }
            )

            service_counts["find_doctor"] += doc.get("Find a Doctor", 0)
            service_counts["direction"] += doc.get("Direction", 0)
            service_counts["other"] += doc.get("Other", 0)
            service_counts["contact_us"] += doc.get("Contact Us", 0)
            service_counts["book_an_appointment"] += doc.get(
                "Book an Appointment", 0
            )

            for msg in chat_history:
                if msg.get("role") == "user" and isinstance(
                    msg.get("content"), str
                ):
                    # detect unsubscribe
                    if "stop" in msg["content"].lower():
                        unsubscribed_users.append(
                            {"username": username, "phone_number": phone_number}
                        )
                        break

                if msg.get("role") == "assistant" and isinstance(
                    msg.get("content"), str
                ):
                    # detect site visit confirmation message
                    if (
                        "thanks! our team will confirm your appointment soon."
                        in msg["content"].lower()
                    ):  # noqa
                        site_visit_users.append(
                            {"username": username, "phone_number": phone_number}
                        )
                        break

        avg_interactions_per_user = (
            round(total_interactions / total_users, 2) if total_users else 0
        )

        most_active_user = (
            max(user_activity, key=lambda x: x["interactions"])
            if user_activity
            else None
        )

        analytics = {
            "success": True,
            "summary": {
                "total_users": total_users,
                "total_interactions": total_interactions,
                "avg_interactions_per_user": avg_interactions_per_user,
                "most_active_user": most_active_user,
                "service_wise_interactions": dict(service_counts),
                "total_unsubscribed_users": len(unsubscribed_users),
                "unsubscribed_users": unsubscribed_users,
                "total_appointment_users": len(site_visit_users),
                "appointment_booked_users": site_visit_users,
            },
        }

        return analytics

    except Exception as e:
        logger.exception(
            "Error generating full analytics", extra={"exception": e}
        )
        raise e


def add_registration(data):
    """Function to add registration."""
    try:
        data["created_at"] = datetime.utcnow()

        appoinments.insert_one(data)

    except Exception as e:
        logger.error(
            "Error occured while returning the analytics",
            extra={
                "error": str(e)
            }
        )

        return None
    
def add_call_entry(data: dict):
    """Create or update call entry based on callSid."""
    try:
        pims_calls.update_one(
            {"callSid": data.get("callSid")},
            {
                "$set": {
                    **data,
                    "updated_at": int(time.time())
                },
                "$setOnInsert": {
                    "created_at": int(time.time())
                }
            },
            upsert=True
        )
    except Exception as e:
        logger.exception("Error adding/updating call entry", extra={"error": str(e)})
        raise



def list_calls(page: int = 1, limit: int = 20):
    """Return paginated call logs."""
    try:
        skip = (page - 1) * limit

        total_docs = pims_calls.count_documents({})
        total_pages = (total_docs + limit - 1) // limit

        docs = list(
            pims_calls.find(
                {},
                {
                    "_id": 1,
                    "status": 1,
                    "created_at": 1,
                    "telephonyData.recordingUrl": 1,
                    "contextDetails.recipientPhoneNumber": 1,
                },
            )
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        # clean + flatten
        cleaned = []
        for d in docs:
            cleaned.append({
                "_id": str(d["_id"]),
                "recipientPhoneNumber": d.get("contextDetails", {}).get("recipientPhoneNumber"),
                "recordingUrl": d.get("telephonyData", {}).get("recordingUrl"),
                "status": d.get("status"),
                "created_at": d.get("created_at"),
            })

        return {
            "page": page,
            "limit": limit,
            "total_docs": total_docs,
            "total_pages": total_pages,
            "calls": cleaned,
        }

    except Exception as e:
        logger.exception("Error listing calls", extra={"error": e})
        raise e

def get_recent_calls(limit: int = 5):
    """Return the most recent call logs."""
    try:
        docs = list(
            pims_calls.find(
                {},
                {
                    "_id": 1,
                    "status": 1,
                    "created_at": 1,
                    "telephonyData.recordingUrl": 1,
                    "contextDetails.recipientPhoneNumber": 1,
                },
            )
            .sort("created_at", -1)
            .limit(limit)
        )

        cleaned = []
        for d in docs:
            cleaned.append({
                "_id": str(d["_id"]),
                "recipientPhoneNumber": d.get("contextDetails", {}).get("recipientPhoneNumber"),
                "recordingUrl": d.get("telephonyData", {}).get("recordingUrl"),
                "status": d.get("status"),
                "created_at": d.get("created_at"),
            })

        return cleaned

    except Exception as e:
        logger.exception("Error fetching recent calls", extra={"error": e})
        raise e
    
def get_call_by_id(call_id: str):
    """Return full call document by ID."""
    try:
        doc = pims_calls.find_one({"_id": ObjectId(call_id)})

        if not doc:
            return None

        # convert _id to string
        doc["_id"] = str(doc["_id"])

        return doc

    except Exception as e:
        logger.exception("Error fetching call by ID", extra={"error": e})
        raise e
    
def return_system_prompt():
    try:
        doc = pims_systems.find_one(
            {"category": "system_prompt"},
            {"_id": 0, "prompt": 1}
        )
        return doc.get("prompt") if doc else ""
    except Exception as e:
        raise e


def return_kb_prompt():
    try:
        doc = pims_systems.find_one(
            {"category": "kb_prompt"},
            {"_id": 0, "kb": 1}
        )
        return doc.get("kb") if doc else {}
    except Exception as e:
        raise e


def update_system_prompt(prompt: str):
    try:
        result = pims_systems.update_one(
            {"category": "system_prompt"},
            {"$set": {"prompt": prompt}},
            upsert=False
        )
        return result.modified_count > 0
    except Exception as e:
        raise e


def update_kb_prompt(kb: dict):
    try:
        result = pims_systems.update_one(
            {"category": "kb_prompt"},   # ✅ FIXED
            {"$set": {"kb": kb}},
            upsert=False
        )
        return result.modified_count > 0
    except Exception as e:
        raise e


def mark_attendance(phone_number: str, stall_id: str):
    try:
        # check attendee
        user = attendee.find_one({"contact_number": phone_number})
        if not user:
            return {"success": False, "error": "invalid_user"}

        # check stall
        stall_doc = stall.find_one(
            {"stall_id": stall_id},
            {"_id": 0}
        )
        if not stall_doc:
            return {"success": False, "error": "invalid_stall"}

        # mark attendance (avoid duplicates)
        attendee.update_one(
            {
                "contact_number": phone_number,
                "visited_stalls.stall_id": {"$ne": stall_id}
            },
            {
                "$push": {
                    "visited_stalls": {
                        "stall_id": stall_id,
                        "timeframe": int(time.time())
                    }
                }
            }
        )

        return {"success": True, "stall": stall_doc}

    except Exception as e:
        raise e
    
def mark_session_attendance(phone_number: str, session_id: int):
    try:
        # check attendee
        user = attendee.find_one({"contact_number": phone_number})
        if not user:
            return {"success": False, "error": "invalid_user"}

        # check session
        session_doc = session.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        if not session_doc:
            return {"success": False, "error": "invalid_session"}

        # mark attendance (avoid duplicates)
        attendee.update_one(
            {
                "contact_number": phone_number,
                "visited_sessions.session_id": {"$ne": session_id}
            },
            {
                "$push": {
                    "visited_sessions": {
                        "session_id": session_id,
                        "timeframe": int(time.time())
                    }
                }
            }
        )

        return {"success": True, "session": session_doc}

    except Exception as e:
        raise e


def mark_venue_entry(user_id: str):
    """Mark venue entry for an attendee by user_id.

    Appends the current epoch time to the `entered_venue` list.
    Returns success/failure dict similar to mark_session_attendance.
    """
    try:
        # check attendee exists
        user = attendee.find_one({"user_id": user_id})
        if not user:
            return {"success": False, "error": "attendee_not_exist"}

        # push current epoch time into entered_venue list
        attendee.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "entered_venue": int(time.time())
                }
            }
        )

        return {
            "success": True,
            "message": "Attendance marked successfully",
            "name": user.get("name", ""),
        }

    except Exception as e:
        logger.exception(
            "Error marking venue entry",
            extra={"error": str(e), "user_id": user_id}
        )
        raise e

    
def is_flow_id_exist(flow_id: str) -> bool:
    try:
        flow_doc = session.find_one(
            {"flow_id": flow_id},
            {"_id": 1}
        )
        return flow_doc is not None

    except Exception as e:
        raise e
    
def save_session_feedback(phone_number: str, flow_id: str, flow_data: dict):
    try:
        feedback_response = {
            "phone_number": phone_number,
            "q1": flow_data.get("q1", ""),
            "q2": flow_data.get("q2", ""),
            "q3": flow_data.get("q3", ""),
            "timestamp": int(time.time())
        }

        # First try updating existing feedback of that phone number
        update_result = session.update_one(
            {
                "flow_id": flow_id,
                "feedback.phone_number": phone_number
            },
            {
                "$set": {
                    "feedback.$": feedback_response
                }
            }
        )

        # If no existing feedback found, push new one
        if update_result.matched_count == 0:
            push_result = session.update_one(
                {"flow_id": flow_id},
                {
                    "$push": {
                        "feedback": feedback_response
                    }
                }
            )

            if push_result.matched_count == 0:
                return False
        return True
    except Exception as e:
        raise e 

def save_quiz_score(phone_number: str, day: str, score: int) -> bool:
    """
    Save quiz score for a specific day in attendee collection.
    
    Args:
        phone_number: Phone number of the attendee
        day: Day identifier (day1, day2, day3)
        score: Quiz score to save
        
    Returns:
        bool: True if successful, False if attendee not found
    """
    try:
        # Check if attendee exists
        user = attendee.find_one({"contact_number": phone_number}, {"_id": 1})
        if not user:
            return False

        # Construct the field name for the specific day
        field_name = f"quiz_score.{day}"
        
        # Update the attendee with the quiz score
        attendee.update_one(
            {"contact_number": phone_number},
            {
                "$set": {
                    field_name: score,
                    "updated_at": int(time.time())
                }
            }
        )
        return True
    except Exception as e:
        logger.exception("Error saving quiz score", extra={"error": str(e), "phone_number": phone_number})
        raise e

def set_venue_entry_flag(phone_number: str, flag: bool) -> bool:
    try:
        user = attendee.find_one({"contact_number": phone_number}, {"_id": 1})
        if not user:
            return False

        attendee.update_one(
            {"contact_number": phone_number},
            {
                "$set": {
                    "venue_entry": flag
                }
            }
        )
        return True
    except Exception as e:
        raise e

 
def add_attendee(data: dict) -> bool:
    try:
        existing = attendee.find_one(
            {"contact_number": data.get("contact_number")},
            {"_id": 1}
        )
        if existing:
            return False

        attendee_doc = {
            "user_id": str(uuid4().int)[:5],
            "name": data.get("name"),
            "email": data.get("email"),
            "designation": data.get("designation"),
            "company": data.get("company"),
            "contact_number": data.get("contact_number"),
            "category": data.get("category"),
            "venue_entry": False,
        }

        attendee.insert_one(attendee_doc)
        return True
    except Exception as e:
        raise e
    

def get_all_stalls():
    try:
        return list(stall.find({}, {"_id": 0}))
    except Exception as e:
        raise e


def _calculate_attendee_score(doc: dict) -> dict:
    """Calculate and attach score fields to an attendee document.

    Scoring rules:
      - 10 points per visited stall
      - 10 points per visited session
      - Sum of all quiz_score day values
    """
    stall_score = len(doc.get("visited_stalls", [])) * 25
    session_score = len(doc.get("visited_sessions", [])) * 50
    quiz_scores = doc.get("quiz_score", {})
    quiz_total = sum(quiz_scores.values()) if isinstance(quiz_scores, dict) else 0

    doc["stall_score"] = stall_score
    doc["session_score"] = session_score
    doc["quiz_total_score"] = quiz_total
    doc["total_score"] = stall_score + session_score + quiz_total
    return doc


def get_all_attendees():
    try:
        docs = list(attendee.find({}, {"_id": 0}))
        for doc in docs:
            _calculate_attendee_score(doc)
        return docs
    except Exception as e:
        raise e
    
def get_stalls_by_ids(stall_ids: list[str]):
    try:
        return list(
            stall.find(
                {"stall_id": {"$in": stall_ids}},
                {"_id": 0}
            )
        )
    except Exception as e:
        raise e
    

def get_attendees_by_stall_id(stall_id: str):
    try:
        return list(
            attendee.find(
                {"visited_stalls.stall_id": stall_id},
                {"_id": 0}
            )
        )
    except Exception as e:
        raise e



def get_attendees_by_user_ids(user_ids: list[str]):
    try:
        return list(
            attendee.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0}
            )
        )
    except Exception as e:
        raise e
    
def get_attendee_by_id(user_id: str):
    try:
        doc = attendee.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        if doc:
            _calculate_attendee_score(doc)
        return doc
    except Exception as e:
        raise e


def get_stall_by_id(stall_id: str):
    try:
        return stall.find_one(
            {"stall_id": stall_id},
            {"_id": 0}
        )
    except Exception as e:
        raise e


def update_attendee(user_id: str, update_data: dict) -> bool:
    try:
        result = attendee.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return result.matched_count > 0
    except Exception as e:
        raise e


def delete_attendee(user_id: str) -> bool:
    try:
        result = attendee.delete_one(
            {"user_id": user_id}
        )
        return result.deleted_count > 0
    except Exception as e:
        raise e


# ──────────────────────────────────────────────
# Session Utilities
# ──────────────────────────────────────────────

def list_sessions():
    """Return all sessions."""
    try:
        docs = list(
            session.find(
                {},
                {
                    "_id": 0,
                    "session_id": 1,
                    "session_name": 1,
                    "session_datetime": 1,
                    "venue": 1,
                    "flow_id": 1,
                },
            )
            .sort("session_datetime", -1)
        )

        for doc in docs:
            dt = doc.get("session_datetime")
            if isinstance(dt, datetime):
                doc["session_datetime"] = dt.isoformat()

        return docs

    except Exception as e:
        logger.exception("Error listing sessions", extra={"error": e})
        raise e


def get_session_by_id(session_id: int):
    """Return full session document by session_id."""
    try:
        doc = session.find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        if not doc:
            return None

        dt = doc.get("session_datetime")
        if isinstance(dt, datetime):
            doc["session_datetime"] = dt.isoformat()

        return doc

    except Exception as e:
        logger.exception("Error fetching session by ID", extra={"error": e})
        raise e


def get_attendees_by_session_id(session_id: int):
    """Return attendees who visited a given session."""
    try:
        return list(
            attendee.find(
                {"visited_sessions.session_id": session_id},
                {"_id": 0}
            )
        )
    except Exception as e:
        logger.exception("Error fetching attendees by session", extra={"error": e})
        raise e


def get_similar_attendees_by_phone(phone_number: str):
    """
    Find attendees who share at least one visited session
    with the given phone number.
    """
    try:
        # 1. Get the target attendee
        target = attendee.find_one(
            {"contact_number": phone_number},
            {"_id": 0, "visited_sessions": 1}
        )
        if not target:
            return []

        visited = target.get("visited_sessions", [])
        if not visited:
            return []

        # 2. Collect session_ids the target attended
        session_ids = [s["session_id"] for s in visited]

        # 3. Find other attendees who share any of those sessions
        similar = list(
            attendee.find(
                {
                    "contact_number": {"$ne": phone_number},
                    "visited_sessions.session_id": {"$in": session_ids},
                },
                {"_id": 0}
            )
        )

        return similar

    except Exception as e:
        logger.exception("Error fetching similar attendees", extra={"error": e})
        raise e


def get_sessions_by_ids(session_ids: list[int]):
    """Return sessions matching the provided list of session_id integers."""
    try:
        docs = list(
            session.find(
                {"session_id": {"$in": session_ids}},
                {"_id": 0}
            )
        )

        for doc in docs:
            dt = doc.get("session_datetime")
            if isinstance(dt, datetime):
                doc["session_datetime"] = dt.isoformat()

        return docs

    except Exception as e:
        logger.exception("Error fetching sessions by IDs", extra={"error": e})
        raise e


# question metadata from the WhatsApp flow
FEEDBACK_QUESTIONS = {
    "q1": {
        "label": "Was this worth your time?",
        "options": ["0_Absolutely", "1_Somewhat", "2_Not_enough_valueion"],
    },
    "q2": {
        "label": "Practical, actionable insights",
        "options": ["0_Yes", "1_Partly", "2_No"],
    },
    "q3": {
        "label": "Go deeper next PACC?",
        "options": [
            "0_Yes_–_Full_Session_Needed",
            "1_Maybe_–_Breakout_Format",
            "2_Prefer_New_Topic",
        ],
    },
}


def get_all_sessions_feedback_analytics():
    """
    Return feedback analytics for every session.
    Each question gets a breakdown of option → count.
    """
    try:
        docs = list(
            session.find(
                {},
                {
                    "_id": 0,
                    "session_id": 1,
                    "session_name": 1,
                    "session_datetime": 1,
                    "venue": 1,
                    "feedback": 1,
                },
            ).sort("session_datetime", -1)
        )

        results = []
        for doc in docs:
            dt = doc.get("session_datetime")
            if isinstance(dt, datetime):
                doc["session_datetime"] = dt.isoformat()

            feedbacks = doc.get("feedback", [])
            total = len(feedbacks)

            summary = {}
            for q_key, q_meta in FEEDBACK_QUESTIONS.items():
                counts = {opt: 0 for opt in q_meta["options"]}
                for fb in feedbacks:
                    val = fb.get(q_key, "")
                    if val in counts:
                        counts[val] += 1
                summary[q_key] = {
                    "label": q_meta["label"],
                    "options": counts,
                }

            results.append({
                "session_id": doc.get("session_id"),
                "session_name": doc.get("session_name"),
                "session_datetime": doc.get("session_datetime"),
                "venue": doc.get("venue"),
                "total_feedback": total,
                "feedback_summary": summary,
            })

        return results

    except Exception as e:
        logger.exception("Error building feedback analytics", extra={"error": e})
        raise e


def get_attendee_activity_data(phone_number: str):
    """
    Get attendee's activity data including visited sessions, visited stalls, and quiz scores.
    
    Args:
        phone_number: Phone number of the attendee
        
    Returns:
        dict: Contains lists of visited_sessions, visited_stalls, and quiz_scores
    """
    try:
        # Get attendee data
        user = attendee.find_one(
            {"contact_number": phone_number},
            {
                "_id": 0,
                "visited_sessions": 1,
                "visited_stalls": 1,
                "quiz_score": 1
            }
        )
        
        if not user:
            return {"success": False, "error": "invalid_user"}

        # Extract data with defaults
        visited_sessions = user.get("visited_sessions", [])
        visited_stalls = user.get("visited_stalls", [])
        quiz_score = user.get("quiz_score", {})
        
        # Convert quiz_score dict to list format
        quiz_scores_list = []
        for day, score in quiz_score.items():
            quiz_scores_list.append({
                "day": day,
                "score": score
            })

        return {
            "success": True,
            "data": {
                "visited_sessions": visited_sessions,
                "visited_stalls": visited_stalls,
                "quiz_scores": quiz_scores_list
            }
        }

    except Exception as e:
        logger.exception("Error fetching attendee activity data", extra={"error": str(e), "phone_number": phone_number})
        raise e


def get_all_attendees_activity_data():
    """
    Get all attendees' activity data including visited sessions, visited stalls, and quiz scores.
    
    Returns:
        dict: Contains lists of all attendees with their visited_sessions, visited_stalls, and quiz_scores
    """
    try:
        # Get all attendees data
        users = list(attendee.find(
            {},
            {
                "_id": 0,
                "contact_number": 1,
                "name": 1,
                "email": 1,
                "company": 1,
                "visited_sessions": 1,
                "visited_stalls": 1,
                "quiz_score": 1
            }
        ))
        
        if not users:
            return {"success": False, "error": "no_attendees_found"}

        attendees_data = []
        for user in users:
            # Extract data with defaults
            visited_sessions = user.get("visited_sessions", [])
            visited_stalls = user.get("visited_stalls", [])
            quiz_score = user.get("quiz_score", {})
            
            # Convert quiz_score dict to list format
            quiz_scores_list = []
            for day, score in quiz_score.items():
                quiz_scores_list.append({
                    "day": day,
                    "score": score
                })

            attendees_data.append({
                "visited_sessions": visited_sessions,
                "visited_stalls": visited_stalls,
                "quiz_scores": quiz_scores_list
            })

        return {
            "success": True,
            "data": attendees_data
        }

    except Exception as e:
        logger.exception("Error fetching all attendees activity data", extra={"error": str(e)})
        raise e


def get_event_analytics():
    """
    Build comprehensive event analytics from attendee, stall, session, and chatbot collections.

    Returns a dict with sections:
      - attendee_overview
      - stall_analytics
      - session_analytics
      - quiz_analytics
      - engagement_leaderboard
      - chatbot_analytics
      - timeline (hourly visit heatmap)
    """
    try:
        all_attendees = list(attendee.find({}, {"_id": 0}))
        all_stalls = list(stall.find({}, {"_id": 0}))
        all_sessions = list(session.find({}, {"_id": 0}))
        all_users = list(idac.find({}, {"_id": 0}))

        total_attendees = len(all_attendees)

        venue_entries = sum(1 for a in all_attendees if a.get("venue_entry"))
        category_breakdown = defaultdict(int)
        for a in all_attendees:
            category_breakdown[a.get("category", "unknown")] += 1

        attendee_overview = {
            "total_registered": total_attendees,
            "venue_check_ins": venue_entries,
            "venue_check_in_rate": round(venue_entries / total_attendees * 100, 1) if total_attendees else 0,
            "category_breakdown": dict(category_breakdown),
        }

        stall_visit_counts = defaultdict(int)     
        total_stall_visits = 0
        stall_hourly = defaultdict(int)           

        for a in all_attendees:
            for v in a.get("visited_stalls", []):
                sid = v.get("stall_id")
                stall_visit_counts[sid] += 1
                total_stall_visits += 1
                ts = v.get("timeframe")
                if ts:
                    stall_hourly[datetime.utcfromtimestamp(ts).hour] += 1

        stall_map = {s["stall_id"]: s.get("company_name", s["stall_id"]) for s in all_stalls}
        stall_category_map = {s["stall_id"]: s.get("category", "unknown") for s in all_stalls}

        sorted_stalls = sorted(stall_visit_counts.items(), key=lambda x: x[1], reverse=True)
        most_visited_stalls = [
            {"stall_id": sid, "company_name": stall_map.get(sid, sid), "visits": cnt}
            for sid, cnt in sorted_stalls[:5]
        ]
        least_visited_stalls = [
            {"stall_id": sid, "company_name": stall_map.get(sid, sid), "visits": cnt}
            for sid, cnt in sorted_stalls[-5:]
        ] if sorted_stalls else []

        stall_category_visits = defaultdict(int)
        for sid, cnt in stall_visit_counts.items():
            stall_category_visits[stall_category_map.get(sid, "unknown")] += cnt

        stall_analytics = {
            "total_stalls": len(all_stalls),
            "total_stall_visits": total_stall_visits,
            "avg_stalls_per_attendee": round(total_stall_visits / total_attendees, 2) if total_attendees else 0,
            "most_visited": most_visited_stalls,
            "least_visited": least_visited_stalls,
            "visits_by_stall_category": dict(stall_category_visits),
        }

        session_visit_counts = defaultdict(int)     
        total_session_visits = 0
        session_hourly = defaultdict(int)

        for a in all_attendees:
            for v in a.get("visited_sessions", []):
                sid = v.get("session_id")
                session_visit_counts[sid] += 1
                total_session_visits += 1
                ts = v.get("timeframe")
                if ts:
                    session_hourly[datetime.utcfromtimestamp(ts).hour] += 1

        session_map = {}
        for s in all_sessions:
            dt = s.get("session_datetime")
            if isinstance(dt, datetime):
                dt = dt.isoformat()
            session_map[s["session_id"]] = {
                "session_name": s.get("session_name", ""),
                "venue": s.get("venue", ""),
                "session_datetime": dt,
                "total_feedback": len(s.get("feedback", [])),
            }

        sorted_sessions = sorted(session_visit_counts.items(), key=lambda x: x[1], reverse=True)
        most_attended_sessions = [
            {
                "session_id": sid,
                "session_name": session_map.get(sid, {}).get("session_name", str(sid)),
                "attendees": cnt,
            }
            for sid, cnt in sorted_sessions[:5]
        ]
        least_attended_sessions = [
            {
                "session_id": sid,
                "session_name": session_map.get(sid, {}).get("session_name", str(sid)),
                "attendees": cnt,
            }
            for sid, cnt in sorted_sessions[-5:]
        ] if sorted_sessions else []

        session_analytics = {
            "total_sessions": len(all_sessions),
            "total_session_visits": total_session_visits,
            "avg_sessions_per_attendee": round(total_session_visits / total_attendees, 2) if total_attendees else 0,
            "most_attended": most_attended_sessions,
            "least_attended": least_attended_sessions,
        }

        day_scores = defaultdict(list)  
        quiz_participants = 0

        for a in all_attendees:
            qs = a.get("quiz_score", {})
            if qs and isinstance(qs, dict):
                quiz_participants += 1
                for day, score in qs.items():
                    day_scores[day].append(score)

        quiz_per_day = {}
        for day, scores in sorted(day_scores.items()):
            quiz_per_day[day] = {
                "participants": len(scores),
                "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
            }

        scorer_list = []
        for a in all_attendees:
            qs = a.get("quiz_score", {})
            if qs and isinstance(qs, dict):
                total = sum(qs.values())
                scorer_list.append({
                    "user_id": a.get("user_id"),
                    "name": a.get("name", ""),
                    "company": a.get("company", ""),
                    "total_quiz_score": total,
                })
        scorer_list.sort(key=lambda x: x["total_quiz_score"], reverse=True)

        quiz_analytics = {
            "total_participants": quiz_participants,
            "per_day": quiz_per_day,
            "top_scorers": scorer_list[:10],
        }

        leaderboard = []
        for a in all_attendees:
            _calculate_attendee_score(a)
            leaderboard.append({
                "user_id": a.get("user_id"),
                "name": a.get("name", ""),
                "company": a.get("company", ""),
                "category": a.get("category", ""),
                "stall_score": a.get("stall_score", 0),
                "session_score": a.get("session_score", 0),
                "quiz_total_score": a.get("quiz_total_score", 0),
                "total_score": a.get("total_score", 0),
            })
        leaderboard.sort(key=lambda x: x["total_score"], reverse=True)

        avg_score = (
            round(sum(l["total_score"] for l in leaderboard) / len(leaderboard), 2)
            if leaderboard else 0
        )

        engagement = {
            "avg_engagement_score": avg_score,
            "leaderboard_top_10": leaderboard[:10],
        }

        category_top = defaultdict(list)
        for entry in leaderboard:
            cat = entry.get("category", "unknown")
            if len(category_top[cat]) < 3:
                category_top[cat].append({
                    "user_id": entry["user_id"],
                    "name": entry["name"],
                    "company": entry["company"],
                    "total_score": entry["total_score"],
                })

        engagement["top_scorer_by_category"] = dict(category_top)

        total_chatbot_users = len(all_users)
        total_interactions = 0
        service_counts = defaultdict(int)

        service_fields = ["Agenda", "Exhibitors", "Navigation", "Other"]

        for u in all_users:
            chat_history = u.get("chat_history", [])
            total_interactions += len(chat_history) // 2
            for sf in service_fields:
                service_counts[sf] += u.get(sf, 0)

        chatbot_analytics = {
            "total_chatbot_users": total_chatbot_users,
            "total_interactions": total_interactions,
            "avg_interactions_per_user": round(total_interactions / total_chatbot_users, 2) if total_chatbot_users else 0,
            "service_usage": dict(service_counts),
        }

        timeline = {
            "stall_visits_by_hour": {str(h): stall_hourly.get(h, 0) for h in range(24)},
            "session_visits_by_hour": {str(h): session_hourly.get(h, 0) for h in range(24)},
        }

        return {
            "attendee_overview": attendee_overview,
            "stall_analytics": stall_analytics,
            "session_analytics": session_analytics,
            "quiz_analytics": quiz_analytics,
            "engagement": engagement,
            "chatbot_analytics": chatbot_analytics,
            "timeline": timeline,
        }

    except Exception as e:
        logger.exception("Error building event analytics", extra={"error": e})
        raise e


# ──────────────────────────────────────────────
# Campaign Analytics
# ──────────────────────────────────────────────

def create_campaign(template_id: str, template_name: str, recipients: list) -> str:
    """Creates a campaign record with one pending entry per recipient phone number."""
    campaign_id = str(uuid4())
    campaigns.insert_one({
        "campaign_id": campaign_id,
        "template_id": template_id,
        "template_name": template_name,
        "recipients": [
            {
                "phone_number": phone,
                "status": "pending",
                "gupshup_message_id": None,
            }
            for phone in recipients
        ],
        "created_at": datetime.now(),
    })
    return campaign_id


def set_campaign_recipient_sent(
    campaign_id: str, phone_number: str, message_id: str, success: bool
):
    """Records the outcome of sending a single campaign message."""
    campaigns.update_one(
        {"campaign_id": campaign_id, "recipients.phone_number": phone_number},
        {
            "$set": {
                "recipients.$.status": "sent" if success else "failed",
                "recipients.$.gupshup_message_id": message_id,
            }
        },
    )


def update_campaign_recipient_status(message_id: str, status: str) -> bool:
    """Updates a recipient's delivery status by Gupshup message id.

    Returns True if a matching recipient was found (most status webhooks
    won't match, since they fire for every outbound message, not just
    campaign sends).
    """
    result = campaigns.update_one(
        {"recipients.gupshup_message_id": message_id},
        {"$set": {"recipients.$.status": status}},
    )
    return result.matched_count > 0


def _campaign_stats(recipients: list) -> dict:
    total = len(recipients)
    delivered = sum(1 for r in recipients if r["status"] in ("delivered", "read"))
    read = sum(1 for r in recipients if r["status"] == "read")
    failed = sum(1 for r in recipients if r["status"] in ("failed", "undelivered"))

    return {
        "total": total,
        "delivered": delivered,
        "read": read,
        "failed": failed,
        "delivery_rate": round(delivered / total * 100, 1) if total else 0,
        "read_rate": round(read / total * 100, 1) if total else 0,
    }


def get_all_campaigns():
    """Returns all campaigns with summary stats, latest first."""
    docs = list(campaigns.find({}).sort("created_at", -1))
    result = []
    for doc in docs:
        stats = _campaign_stats(doc.get("recipients", []))
        created_at = doc.get("created_at")
        result.append({
            "campaign_id": doc["campaign_id"],
            "template_name": doc.get("template_name"),
            "created_at": created_at.isoformat()
            if isinstance(created_at, datetime)
            else created_at,
            **stats,
        })
    return result


def get_campaign_by_id(campaign_id: str):
    """Returns full campaign detail including per-recipient status and summary stats."""
    doc = campaigns.find_one({"campaign_id": campaign_id}, {"_id": 0})
    if not doc:
        return None

    doc["stats"] = _campaign_stats(doc.get("recipients", []))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


def get_all_leads():
    """Returns all imported membership leads."""
    docs = list(leads.find({}, {"_id": 0}))
    for doc in docs:
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            doc["created_at"] = created_at.isoformat()
    return docs


def get_lead_category_counts():
    """Returns lead counts grouped by category and sub-category."""
    pipeline = [
        {
            "$group": {
                "_id": {"category": "$category", "sub_category": "$sub_category"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]
    rows = list(leads.aggregate(pipeline))

    categories = defaultdict(int)
    subcategories = defaultdict(lambda: defaultdict(int))
    for row in rows:
        category = row["_id"].get("category") or "unknown"
        sub_category = row["_id"].get("sub_category") or "unknown"
        count = row["count"]
        categories[category] += count
        subcategories[category][sub_category] = count

    return {
        "total": sum(categories.values()),
        "categories": dict(categories),
        "subcategories": {
            category: dict(subs) for category, subs in subcategories.items()
        },
    }