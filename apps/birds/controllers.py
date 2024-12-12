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
            table: Database table to retrieve checklists from (default: checklist)
        
        Returns:
            dict: Checklists or error information
        """
        try:
            checklists = db(table).select().as_list()
            return dict(checklists=checklists)
        except Exception as e:
            logger.error(f"Error retrieving checklists: {str(e)}")
            return dict(error=str(e))

    @classmethod
    def submit_checklist(cls, data):
        """
        Submit a new checklist with associated species sightings
        
        Args:
            data (dict): Checklist and sighting data
        
        Returns:
            dict: Submission status
        """
        try:
            # Validate required fields
            if not all(key in data for key in ['speciesName', 'latitude', 'longitude', 'observationDate']):
                return dict(status="error", message="Missing required checklist fields")

            # Create checklist entry
            checklist_data = {
                "COMMON_NAME": str(data.get("speciesName")),
                "LATITUDE": float(data.get("latitude")),
                "LONGITUDE": float(data.get("longitude")),
                "OBSERVATION_DATE": data.get("observationDate"),
                "TIME_OBSERVATIONS_STARTED": data.get("timeObservationsStarted", None),
                "DURATION_MINUTES": float(data.get("durationMinutes", 0)),
                "OBSERVER_ID": get_user_email()
            }
            checklist_id = db.my_checklist.insert(**checklist_data)

            # Add species sightings
            for species in data.get("species", []):
                db.sightings.insert(
                    SAMPLING_EVENT_IDENTIFIER=checklist_id,
                    COMMON_NAME=species.get("COMMON_NAME"),
                    OBSERVATION_COUNT=int(species.get("count", 1))
                )
            
            db.commit()
            return dict(status="success", checklist_id=checklist_id)
        
        except Exception as e:
            db.rollback()
            logger.error(f"Checklist submission error: {str(e)}")
            return dict(status="error", message=str(e))

    @classmethod
    def modify_checklist(cls, checklist_id, action_type, data=None):
        """
        Modify an existing checklist (edit or delete)
        
        Args:
            checklist_id (int): ID of the checklist to modify
            action_type (str): Type of modification ('edit' or 'delete')
            data (dict, optional): Data for editing the checklist
        
        Returns:
            dict: Modification status
        """
        try:
            checklist = db.my_checklist(checklist_id)
            if not checklist:
                return dict(status="error", message="Checklist not found")

            if action_type == 'delete':
                # Delete associated sightings first
                db(db.sightings.SAMPLING_EVENT_IDENTIFIER == checklist_id).delete()
                db(db.my_checklist.id == checklist_id).delete()
                db.commit()
                return dict(status="success", message="Checklist deleted successfully")
            
            elif action_type == 'edit':
                update_data = {
                    "COMMON_NAME": data.get("COMMON_NAME", checklist.COMMON_NAME),
                    "LATITUDE": float(data.get("LATITUDE", checklist.LATITUDE)),
                    "LONGITUDE": float(data.get("LONGITUDE", checklist.LONGITUDE)),
                    "OBSERVATION_DATE": data.get("OBSERVATION_DATE", checklist.OBSERVATION_DATE),
                    "TIME_OBSERVATIONS_STARTED": data.get("TIME_OBSERVATIONS_STARTED", checklist.TIME_OBSERVATIONS_STARTED),
                    "DURATION_MINUTES": float(data.get("DURATION_MINUTES", checklist.DURATION_MINUTES))
                }
                db(db.my_checklist.id == checklist_id).update(**update_data)
                db.commit()
                return dict(status="success", message="Checklist updated successfully")
        
        except Exception as e:
            db.rollback()
            logger.error(f"Checklist modification error: {str(e)}")
            return dict(status="error", message=f"Error processing checklist: {str(e)}")

# Bird Sightings and Location Routes
@action("get_bird_sightings", method=["POST"])
@action.uses(db)
def get_bird_sightings():
    """
    Retrieve bird sightings within specified geographic bounds
    
    Expected JSON payload:
    {
        'north': float,
        'south': float,
        'east': float,
        'west': float,
        'species': optional species filter
    }
    """
    try:
        bounds = request.json
        
        # Validate bounds
        north = bounds.get('north')
        south = bounds.get('south')
        east = bounds.get('east')
        west = bounds.get('west')
        selected_species = bounds.get('species')
        
        if not all([north, south, east, west]):
            return dict(error="Invalid geographic bounds", sightings=[])
        
        # Modify query to use both my_checklist and checklist tables
        query = (
            (db.checklist.LATITUDE <= north) & 
            (db.checklist.LATITUDE >= south) & 
            (db.checklist.LONGITUDE <= east) & 
            (db.checklist.LONGITUDE >= west)
        )
        
        # Add species filtering if specified
        if selected_species:
            query &= (db.sightings.COMMON_NAME == selected_species)
        
        # Join checklist and sightings to get comprehensive data
        observations = db(query).select(
            db.checklist.LATITUDE, 
            db.checklist.LONGITUDE, 
            db.sightings.COMMON_NAME,
            db.sightings.OBSERVATION_COUNT,
            left=db.sightings.on(db.checklist.SAMPLING_EVENT_IDENTIFIER == db.sightings.SAMPLING_EVENT_IDENTIFIER)
        )
        
        # Process observations into heat map format
        sightings = []
        for obs in observations:
            try:
                count = int(obs.sightings.OBSERVATION_COUNT or 1)
                sightings.append({
                    'lat': obs.checklist.LATITUDE,
                    'lon': obs.checklist.LONGITUDE,
                    'species': obs.sightings.COMMON_NAME,
                    'intensity': min(count, 10)  # Cap intensity for visual clarity
                })
            except (ValueError, TypeError):
                # Skip invalid entries
                continue
        
        return dict(sightings=sightings)
    
    except Exception as e:
        logger.error(f"Error in get_bird_sightings: {str(e)}")
        return dict(error=str(e), sightings=[])

@action("get_hotspot_details", method=["POST"])
@action.uses(db)
def get_hotspot_details():
    """
    Retrieve detailed information for a specific geographic point
    
    Expected JSON payload:
    {
        'lat': float,
        'lon': float,
        'species': optional species filter
    }
    """
    try:
        data = request.json
        lat = data.get('lat')
        lon = data.get('lon')
        species = data.get('species')

        # Base query for the specific location
        query = (
            (db.my_checklist.LATITUDE == lat) & 
            (db.my_checklist.LONGITUDE == lon)
        )

        # Add species filter if provided
        if species:
            query &= (db.sightings.COMMON_NAME == species)

        # Fetch species and observation details
        observations = db(query).select(
            db.sightings.COMMON_NAME, 
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
            groupby=db.sightings.COMMON_NAME
        )

        # Prepare the response
        species_details = [
            {
                'species': row.COMMON_NAME, 
                'count': row.total_count
            } for row in observations
        ]

        return dict(
            species_count=len(species_details),
            species_details=species_details,
            total_observations=sum(row['count'] for row in species_details)
        )

    except Exception as e:
        logger.error(f"Error in get_hotspot_details: {str(e)}")
        return dict(error=str(e))

# Species and Checklist Routes
@action("get_species", method=["GET"])
@action.uses(db)
def get_species():
    """Retrieve all species"""
    return ChecklistManager.get_checklists(db.species)

@action('get_checklists', method=["GET"])
@action.uses(db, auth.user)
def get_checklists():
    """Retrieve all checklists"""
    return ChecklistManager.get_checklists()

@action('get_my_checklists', method=["GET"])
@action.uses(db, auth.user)
def get_my_checklists():
    """Retrieve user's personal checklists"""
    return ChecklistManager.get_checklists(db.my_checklist)

@action("search_species", method=["GET"])
@action.uses(db)
def search_species():
    """
    Search for species with optional filtering
    
    Query parameters:
    - q: Search query
    - min_obs: Minimum number of observations
    """
    query = request.params.get("q", "").strip().lower()
    min_observations = int(request.params.get("min_obs", 0))
    
    # Base query
    species_query = db.species.COMMON_NAME.contains(query)
    
    # Optional observation count filter
    if min_observations > 0:
        species_with_obs = db.sightings.groupby(db.sightings.COMMON_NAME).having(
            db.sightings.OBSERVATION_COUNT.sum() >= min_observations
        )
        species_query &= (db.species.COMMON_NAME.belongs(species_with_obs))
    
    species = db(species_query).select().as_list()
    return dict(species=species)

@action("submit_checklist", method=["POST"])
@action.uses(db, auth.user)
def submit_checklist():
    """Submit a new checklist"""
    return ChecklistManager.submit_checklist(request.json)

@action('delete_checklist/<checklist_id>', method=["DELETE"])
@action.uses(db, auth.user)
def delete_checklist(checklist_id):
    """Delete a specific checklist"""
    return ChecklistManager.modify_checklist(checklist_id, 'delete')
 
@action('edit_checklist/<checklist_id>', method=["POST"])
@action.uses(db, auth.user)
def edit_checklist(checklist_id):
    """Edit a specific checklist"""
    return ChecklistManager.modify_checklist(checklist_id, 'edit', request.json)

@action("get_region_statistics", method=["GET"])
@action.uses(db)
def get_region_statistics():
    """
    Retrieve detailed statistics for a specific geographic region
    
    Query parameters:
    - north: Northern latitude bound
    - south: Southern latitude bound
    - east: Eastern longitude bound
    - west: Western longitude bound
    """
    try:
        # Parse region bounds from query parameters
        north = float(request.params.get('north', 0))
        south = float(request.params.get('south', 0))
        east = float(request.params.get('east', 0))
        west = float(request.params.get('west', 0))
        
        # Region bounds query
        query = (
            (db.my_checklist.LATITUDE <= north) & 
            (db.my_checklist.LATITUDE >= south) & 
            (db.my_checklist.LONGITUDE <= east) & 
            (db.my_checklist.LONGITUDE >= west)
        )
        
        # Aggregate species statistics
        species_summary = db(query).select(
            db.sightings.COMMON_NAME, 
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
            groupby=db.sightings.COMMON_NAME,
            orderby=~db.sightings.OBSERVATION_COUNT.sum()  # Sort by descending count
        )
        
        # Total observations and unique species
        total_observations = sum(row.total_count for row in species_summary)
        unique_species = len(species_summary)
        
        return dict(
            species_summary=[
                {
                    'species': row.sightings.COMMON_NAME, 
                    'total_count': row.total_count,
                    'percentage': (row.total_count / total_observations * 100) if total_observations > 0 else 0
                } for row in species_summary
            ],
            total_observations=total_observations,
            unique_species=unique_species
        )
    
    except Exception as e:
        logger.error(f"Error in get_region_statistics: {str(e)}")
        return dict(error=str(e))

# Static route handlers for HTML templates
@action('index')
@action.uses('index.html', db, auth, ChecklistManager.url_signer)
def index():
    return dict(my_callback_url=URL('my_callback', signer=ChecklistManager.url_signer))

@action('my_callback')
def my_callback():
    return dict(my_value=3)

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
