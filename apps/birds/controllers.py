from py4web import action, request, abort, redirect, URL
from yatl.helpers import A
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated, flash
from py4web.utils.url_signer import URLSigner
from .models import get_user_email

url_signer = URLSigner(session)

@action("index")
@action.uses("index.html", db, auth, url_signer)
def index():
    return {
        "callback_url": URL("callback", signer=url_signer),
    }

@action("callback")
@action.uses()
def callback():
    return {"value": 42}

@action("species", method=["GET"])
@action.uses(db)
def get_species():
    try:
        species = db(db.species).select().as_list()
        return {"species": species}
    except Exception as e:
        return {"error": str(e)}

@action("add_checklist")
@action.uses("add_checklist.html", db, auth)
def add_checklist():
    return {}

@action("my_checklists")
@action.uses("my_checklists.html", db, auth)
def my_checklists():
    return {}

@action("stats")
@action.uses("stats.html", db, auth)
def stats():
    return {}

@action("location")
@action.uses("location.html", db, auth)
def location():
    return {}

@action("search_species", method=["GET"])
@action.uses(db)
def search_species():
    query = request.params.get("q", "").strip().lower()
    species = []
    if query:
        species = db(db.species.COMMON_NAME.contains(query)).select().as_list()
    return {"species": species}

@action("get_hotspots")
@action.uses(db)
def get_hotspots():
    hotspots = db(db.hotspots).select().as_list()
    return {"hotspots": hotspots}

@action("submit_checklist", method=["POST"])
@action.uses(db)
def submit_checklist():
    try:
        data = request.json
        checklist_id = db.my_checklist.insert(
            COMMON_NAME=str(data.get("speciesName")),
            LATITUDE=float(data.get("latitude")),
            LONGITUDE=float(data.get("longitude")),
            OBSERVATION_DATE=data.get("observationDate"),
            TIME_OBSERVATIONS_STARTED=data.get("timeObservationsStarted"),
            DURATION_MINUTES=float(data.get("durationMinutes"))
        )
        for s in data.get("species", []):
            db.sightings.insert(
                SAMPLING_EVENT_IDENTIFIER=checklist_id,
                COMMON_NAME=s.get("COMMON_NAME"),
                OBSERVATION_COUNT=s.get("count")
            )
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@action("delete_checklist/<checklist_id>", method=["DELETE"])
@action.uses(db, auth.user)
def delete_checklist(checklist_id):
    try:
        checklist = db.my_checklist(checklist_id)
        if not checklist:
            return {"status": "error", "message": "Checklist not found"}
        db(db.my_checklist.id == checklist_id).delete()
        db.commit()
        return {"status": "success", "message": "Checklist deleted successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@action("edit_checklist/<checklist_id>", method=["POST"])
@action.uses(db, auth.user)
def edit_checklist(checklist_id):
    try:
        checklist = db.my_checklist(checklist_id)
        if not checklist:
            return {"status": "error", "message": "Checklist not found"}
        data = request.json
        db(db.my_checklist.id == checklist_id).update(
            COMMON_NAME=data.get("COMMON_NAME"),
            LATITUDE=float(data.get("LATITUDE")),
            LONGITUDE=float(data.get("LONGITUDE")),
            OBSERVATION_DATE=data.get("OBSERVATION_DATE"),
            TIME_OBSERVATIONS_STARTED=data.get("TIME_OBSERVATIONS_STARTED"),
            DURATION_MINUTES=float(data.get("DURATION_MINUTES"))
        )
        db.commit()
        return {"status": "success", "message": "Checklist updated successfully"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
