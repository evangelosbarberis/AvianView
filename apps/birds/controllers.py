from py4web import action, request, abort, redirect, URL
from yatl.helpers import A
from .common import db, session, T, cache, auth, logger, authenticated, unauthenticated, flash
from py4web.utils.url_signer import URLSigner
from .models import get_user_email

class ChecklistManager:
    url_signer = URLSigner(session)

    @classmethod
    def get_checklists(cls, table=db.checklist):
        """
        Retrieve checklists from a specified table
        
        Args:
            table (DAL table, optional): Table to retrieve checklists from. Defaults to db.checklist
        
        Returns:
            dict: Dictionary with checklists or error
        """
        try:
            checklists = db(table).select().as_list()
            return dict(checklists=checklists)
        except Exception as e:
            return dict(error=str(e))

    @classmethod
    def submit_checklist(cls, data):
        """
        Submit a new checklist with associated species sightings
        
        Args:
            data (dict): Checklist and species data
        
        Returns:
            dict: Status of the submission
        """
        try:
            checklist_data = {
                "COMMON_NAME": str(data.get("speciesName")),
                "LATITUDE": float(data.get("latitude")),
                "LONGITUDE": float(data.get("longitude")),
                "OBSERVATION_DATE": data.get("observationDate"),
                "TIME_OBSERVATIONS_STARTED": data.get("timeObservationsStarted"),
                "DURATION_MINUTES": float(data.get("durationMinutes")),
            }
            checklist_id = db.my_checklist.insert(**checklist_data)

            for species in data.get("species", []):
                db.sightings.insert(
                    SAMPLING_EVENT_IDENTIFIER=checklist_id,
                    COMMON_NAME=species.get("COMMON_NAME"),
                    OBSERVATION_COUNT=species.get("count"),
                )
            db.commit()
            return dict(status="success")
        except Exception as e:
            db.rollback()
            return dict(status="error", message=str(e))

    @classmethod
    def modify_checklist(cls, checklist_id, action_type, data=None):
        """
        Centralized method for editing or deleting checklists
        
        Args:
            checklist_id (int): ID of the checklist
            action_type (str): 'edit' or 'delete'
            data (dict, optional): Data for editing
        
        Returns:
            dict: Result of the operation
        """
        try:
            checklist = db.my_checklist(checklist_id)
            if not checklist:
                return dict(status="error", message="Checklist not found")

            if action_type == 'delete':
                db(db.my_checklist.id == checklist_id).delete()
                db.commit()
                return dict(status="success", message="Checklist deleted successfully")
            
            elif action_type == 'edit':
                update_data = {
                    "COMMON_NAME": data.get("COMMON_NAME"),
                    "LATITUDE": float(data.get("LATITUDE")),
                    "LONGITUDE": float(data.get("LONGITUDE")),
                    "OBSERVATION_DATE": data.get("OBSERVATION_DATE"),
                    "TIME_OBSERVATIONS_STARTED": data.get("TIME_OBSERVATIONS_STARTED"),
                    "DURATION_MINUTES": float(data.get("DURATION_MINUTES")),
                }
                db(db.my_checklist.id == checklist_id).update(**update_data)
                db.commit()
                return dict(status="success", message="Checklist updated successfully")
        
        except Exception as e:
            db.rollback()
            return dict(status="error", message=f"Error processing checklist: {str(e)}")

# Route Handlers
@action('index')
@action.uses('index.html', db, auth, ChecklistManager.url_signer)
def index():
    return dict(my_callback_url=URL('my_callback', signer=ChecklistManager.url_signer))

@action('my_callback')
def my_callback():
    return dict(my_value=3)

@action("get_species", method=["GET"])
@action.uses(db)
def get_species():
    return ChecklistManager.get_checklists(db.species)

@action('get_checklists', method=["GET"])
@action.uses(db, auth.user)
def get_checklists():
    return ChecklistManager.get_checklists()

@action('get_my_checklists', method=["GET"])
@action.uses(db, auth.user)
def get_my_checklists():
    return ChecklistManager.get_checklists(db.my_checklist)

@action("search_species", method=["GET"])
@action.uses(db)
def search_species():
    query = request.params.get("q", "").strip().lower()
    species = [] if not query else \
        db(db.species.COMMON_NAME.contains(query)).select().as_list()
    return dict(species=species)

@action("submit_checklist", method=["POST"])
@action.uses(db)
def submit_checklist():
    return ChecklistManager.submit_checklist(request.json)

@action('delete_checklist/<checklist_id>', method=["DELETE"])
@action.uses(db, auth.user)
def delete_checklist(checklist_id):
    return ChecklistManager.modify_checklist(checklist_id, 'delete')
 
@action('edit_checklist/<checklist_id>', method=["POST"])
@action.uses(db, auth.user)
def edit_checklist(checklist_id):
    return ChecklistManager.modify_checklist(checklist_id, 'edit', request.json)

# Static route handlers
@action('add_checklist')
@action.uses('add_checklist.html', db, auth)
def add_checklist():
    return dict()

@action('my_checklists')
@action.uses('my_checklists.html', db, auth)
def my_checklists():
    return dict()

@action('stats')
@action.uses('stats.html', db, auth)
def stats():
    return dict()

@action('location')
@action.uses('location.html', db, auth)
def location():
    return dict()