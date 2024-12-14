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
        
        # Modify query to use both my_checklist and checklist tables with explicit joins
        query = (
            (db.sightings.SAMPLING_EVENT_IDENTIFIER == db.checklist.SAMPLING_EVENT_IDENTIFIER) &
            (db.checklist.LATITUDE <= north) & 
            (db.checklist.LATITUDE >= south) & 
            (db.checklist.LONGITUDE <= east) & 
            (db.checklist.LONGITUDE >= west)
        )
        
        # Add species filtering if specified
        if selected_species:
            query &= (db.sightings.COMMON_NAME == selected_species)
        
        # Perform comprehensive join and selection
        observations = db(query).select(
            db.checklist.LATITUDE, 
            db.checklist.LONGITUDE, 
            db.sightings.COMMON_NAME,
            db.sightings.OBSERVATION_COUNT
        )
        
        # Process observations into heat map format with better error handling
        sightings = []
        for obs in observations:
            try:
                # Ensure we have valid data before processing
                if obs.checklist.LATITUDE and obs.checklist.LONGITUDE and obs.sightings.COMMON_NAME:
                    count = int(obs.sightings.OBSERVATION_COUNT or 1)
                    sightings.append({
                        'lat': obs.checklist.LATITUDE,
                        'lon': obs.checklist.LONGITUDE,
                        'species': obs.sightings.COMMON_NAME,
                        'intensity': min(count, 10)  # Cap intensity for visual clarity
                    })
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Skipping invalid observation: {e}")
        
        return dict(sightings=sightings)
    
    except Exception as e:
        logger.error(f"Error in get_bird_sightings: {str(e)}")
        return dict(error=str(e), sightings=[])

@action("get_hotspot_details", method=["POST"])
@action.uses(db)
def get_hotspot_details():
    """
    Retrieve detailed information for a specific geographic point
    """
    try:
        data = request.json
        lat = data.get('lat')
        lon = data.get('lon')
        species = data.get('species')

        # Use a tighter tolerance for matching coordinates
        query = (
            (db.checklist.LATITUDE >= lat - 0.01) & 
            (db.checklist.LATITUDE <= lat + 0.01) & 
            (db.checklist.LONGITUDE >= lon - 0.01) & 
            (db.checklist.LONGITUDE <= lon + 0.01)
        )

        # Create join condition for sightings
        join_condition = (db.sightings.SAMPLING_EVENT_IDENTIFIER == db.checklist.SAMPLING_EVENT_IDENTIFIER)
        
        # Apply species filter if provided
        if species:
            join_condition &= (db.sightings.COMMON_NAME == species)

        # Fetch observations with comprehensive selection
        observations = db(query).select(
            db.checklist.SAMPLING_EVENT_IDENTIFIER,
            db.checklist.LATITUDE, 
            db.checklist.LONGITUDE,
            db.sightings.COMMON_NAME, 
            db.sightings.OBSERVATION_COUNT,
            left=db.sightings.on(join_condition)
        )

        # Prepare detailed species information
        species_details = {}
        species_checklists = set()

        for obs in observations:
            if obs.sightings.COMMON_NAME:  # Ensure we have a valid species name
                species_name = obs.sightings.COMMON_NAME
                count = obs.sightings.OBSERVATION_COUNT or 1
                checklist_id = obs.checklist.SAMPLING_EVENT_IDENTIFIER
                species_checklists.add(checklist_id)
                
                if species_name not in species_details:
                    species_details[species_name] = {
                        'total_count': count,
                        'observation_count': 1,
                        'checklists': {checklist_id}
                    }
                else:
                    species_details[species_name]['total_count'] += count
                    species_details[species_name]['observation_count'] += 1
                    species_details[species_name]['checklists'].add(checklist_id)

        # Convert to list for easier frontend processing
        formatted_species_details = [
            {
                'species': species, 
                'total_count': details['total_count'],
                'observation_count': details['observation_count'],
                'unique_checklists': len(details['checklists'])
            } for species, details in species_details.items()
        ]

        # Sort by total count in descending order
        formatted_species_details.sort(key=lambda x: x['total_count'], reverse=True)

        return dict(
            species_count=len(formatted_species_details),
            species_details=formatted_species_details,
            total_observations=sum(details['total_count'] for details in formatted_species_details) if formatted_species_details else 0,
            location_lat=lat,
            location_lon=lon,
            unique_checklists=len(species_checklists)
        )

    except Exception as e:
        logger.error(f"Error in get_hotspot_details: {str(e)}")
        return dict(error=str(e), species_count=0, species_details=[], total_observations=0)
    
@action("get_user_checklist_statistics", method=["GET"])
@action.uses(db, auth.user)
def get_user_checklist_statistics():
    """
    Retrieve comprehensive statistics for a specific user's checklists
    
    Returns:
    - Total observations
    - Unique species observed
    - Most frequently observed species
    - Total checklists created
    - Date range of observations
    """
    try:
        # Get current user's email
        user_email = get_user_email()
        
        if not user_email:
            return dict(error="User not authenticated")
        
        # Query my_checklist and sightings tables for user's data
        query = (db.my_checklist.user_email == user_email)
        
        # Aggregate species statistics
        species_summary = db(query).select(
            db.sightings.COMMON_NAME, 
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
            groupby=db.sightings.COMMON_NAME,
            orderby=~db.sightings.OBSERVATION_COUNT.sum()
        )
        
        # Fetch user's checklists
        user_checklists = db(query).select(
            db.my_checklist.OBSERVATION_DATE,
            orderby=db.my_checklist.OBSERVATION_DATE
        )
        
        # Calculate total observations and unique species
        total_observations = sum(row.total_count for row in species_summary)
        unique_species = len(species_summary)
        total_checklists = len(user_checklists)
        
        # Find most frequently observed species
        most_observed_species = species_summary[0] if species_summary else None
        
        # Find date range of observations
        if user_checklists:
            first_observation = min(checklist.OBSERVATION_DATE for checklist in user_checklists)
            last_observation = max(checklist.OBSERVATION_DATE for checklist in user_checklists)
        else:
            first_observation = last_observation = None
        
        return dict(
            total_observations=total_observations,
            unique_species=unique_species,
            total_checklists=total_checklists,
            most_observed_species={
                'name': most_observed_species.sightings.COMMON_NAME if most_observed_species else None,
                'count': most_observed_species.total_count if most_observed_species else 0
            },
            first_observation=first_observation,
            last_observation=last_observation,
            species_summary=[
                {
                    'species': row.sightings.COMMON_NAME, 
                    'total_count': row.total_count,
                    'percentage': (row.total_count / total_observations * 100) if total_observations > 0 else 0
                } for row in species_summary
            ]
        )
    
    except Exception as e:
        logger.error(f"Error in get_user_checklist_statistics: {str(e)}")
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

# @action("get_region_statistics", method=["GET"])
# @action.uses(db)
# def get_region_statistics():
#     """
#     Retrieve detailed statistics for a specific geographic region
    
#     Query parameters:
#     - north: Northern latitude bound
#     - south: Southern latitude bound
#     - east: Eastern longitude bound
#     - west: Western longitude bound
#     """
#     try:
#         # Parse region bounds from query parameters
#         north = float(request.params.get('north', 0))
#         south = float(request.params.get('south', 0))
#         east = float(request.params.get('east', 0))
#         west = float(request.params.get('west', 0))
        
#         # Region bounds query
#         query = (
#             (db.my_checklist.LATITUDE <= north) & 
#             (db.my_checklist.LATITUDE >= south) & 
#             (db.my_checklist.LONGITUDE <= east) & 
#             (db.my_checklist.LONGITUDE >= west)
#         )
        
#         # Aggregate species statistics
#         species_summary = db(query).select(
#             db.sightings.COMMON_NAME, 
#             db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
#             groupby=db.sightings.COMMON_NAME,
#             orderby=~db.sightings.OBSERVATION_COUNT.sum()  # Sort by descending count
#         )
        
#         # Total observations and unique species
#         total_observations = sum(row.total_count for row in species_summary)
#         unique_species = len(species_summary)
        
#         return dict(
#             species_summary=[
#                 {
#                     'species': row.sightings.COMMON_NAME, 
#                     'total_count': row.total_count,
#                     'percentage': (row.total_count / total_observations * 100) if total_observations > 0 else 0
#                 } for row in species_summary
#             ],
#             total_observations=total_observations,
#             unique_species=unique_species
#         )
    
#     except Exception as e:
#         logger.error(f"Error in get_region_statistics: {str(e)}")
#         return dict(error=str(e))

# Static route handlers for HTML templates
@action('index')
@action.uses('index.html', db, auth, ChecklistManager.url_signer)
def index():
    return dict(my_callback_url=URL('my_callback', signer=ChecklistManager.url_signer))

@action('my_callback')
def my_callback():
    return dict(my_value=3)

@action('add_checklist')
@action.uses('add_checklist.html', db, session, auth.user)
def add_checklist():
    return dict()

@action('my_checklists')
@action.uses('my_checklists.html', db, session, auth.user)
def my_checklists():
    return dict()

@action('stats')
@action.uses('stats.html', db, session, auth.user)
def stats():
    return dict()

@action('location')
@action.uses('location.html', db, auth)
def location():
    return dict()
@action("get_species_statistics", method=["POST"])
@action.uses(db)
def get_species_statistics():
    """
    Retrieve comprehensive statistics for a specific species
    """
    try:
        species_name = request.json.get('species')
        
        if not species_name:
            return dict(error="No species specified")
        
        # Calculate total species observations specifically for this species
        total_species_observations = db(
            (db.sightings.COMMON_NAME == species_name)
        ).select(
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count')
        ).first().total_count or 0
        
        # Find top hotspot specifically for this species
        top_hotspot = db(
            (db.sightings.COMMON_NAME == species_name) &
            (db.sightings.SAMPLING_EVENT_IDENTIFIER == db.my_checklist.id)
        ).select(
            db.my_checklist.LATITUDE, 
            db.my_checklist.LONGITUDE,
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
            groupby=(db.my_checklist.LATITUDE, db.my_checklist.LONGITUDE),
            orderby=~db.sightings.OBSERVATION_COUNT.sum(),
            limitby=(1,0)
        ).first()
        
        # Total species observations globally
        total_species_observations_global = db(
            db.sightings.COMMON_NAME == species_name
        ).count()
        
        # Prepare top hotspot data
        top_hotspot_data = None
        if top_hotspot:
            top_hotspot_data = {
                'latitude': top_hotspot.my_checklist.LATITUDE,
                'longitude': top_hotspot.my_checklist.LONGITUDE,
                'location': f"Lat {top_hotspot.my_checklist.LATITUDE}, Lon {top_hotspot.my_checklist.LONGITUDE}",
                'count': top_hotspot.total_count
            }
        
        return dict(
            species=species_name,
            total_observations=total_species_observations,
            total_species_observations=total_species_observations_global,
            top_hotspot=top_hotspot_data
        )
    
    except Exception as e:
        logger.error(f"Error in get_species_statistics: {str(e)}")
        return dict(error=str(e))
    
@action("get_region_statistics", method=["GET"])
@action.uses(db)
def get_region_statistics():
    try:
        # Parse region bounds from query parameters
        north = float(request.params.get('north', 90))
        south = float(request.params.get('south', -90))
        east = float(request.params.get('east', 180))
        west = float(request.params.get('west', -180))

        # Region bounds query
        query = (
            (db.checklist.LATITUDE <= north) & 
            (db.checklist.LATITUDE >= south) & 
            (db.checklist.LONGITUDE <= east) & 
            (db.checklist.LONGITUDE >= west)
        )

        # Aggregate species statistics
        species_summary = db(query).select(
            db.sightings.COMMON_NAME, 
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
            groupby=db.sightings.COMMON_NAME,
            orderby=~db.sightings.OBSERVATION_COUNT.sum(),
            limitby=(0, 10)  # Limit to top 10
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

    
@action("get_species_time_series", method=["POST"])
@action.uses(db)
def get_species_time_series():
    try:
        species_name = request.json.get('species')
        if not species_name:
            return dict(error="No species specified")
        
        # Query to get time series data
        time_series_data = db(
            (db.sightings.COMMON_NAME == species_name) &
            (db.sightings.SAMPLING_EVENT_IDENTIFIER == db.checklist.SAMPLING_EVENT_IDENTIFIER)
        ).select(
            db.checklist.OBSERVATION_DATE,
            db.sightings.OBSERVATION_COUNT.sum().with_alias('count'),
            groupby=db.checklist.OBSERVATION_DATE,
            orderby=~db.checklist.OBSERVATION_DATE,
            limitby=(0, 5)  # Limit to the most recent 5 periods
        )
        
        return dict(time_series=[{
            'date': row.checklist.OBSERVATION_DATE,
            'count': row.count
        } for row in time_series_data])
    
    except Exception as e:
        logger.error(f"Error in get_species_time_series: {str(e)}")
        return dict(error=str(e))
    
@action("get_top_contributors", method=["GET"])
@action.uses(db)
def get_top_contributors():
    try:
        # Ensure the correct table and field names are used
        contributors_data = db(db.checklist).select(
            db.checklist.OBSERVER_ID,
            db.checklist.id.count().with_alias('total_observations'),
            groupby=db.checklist.OBSERVER_ID,
            orderby=~db.checklist.id.count(),
            limitby=(0, 5)  # Limit to top 5
        )
        
        # Optionally, you can include unique species if needed
        # This requires a join with the sightings table
        contributors = []
        for row in contributors_data:
            unique_species_count = db(
                (db.sightings.SAMPLING_EVENT_IDENTIFIER == db.checklist.SAMPLING_EVENT_IDENTIFIER) &
                (db.checklist.OBSERVER_ID == row.checklist.OBSERVER_ID)
            ).select(
                db.sightings.COMMON_NAME.count(distinct=True).with_alias('unique_species')
            ).first().unique_species or 0
            
            contributors.append({
                'name': row.checklist.OBSERVER_ID,
                'total_observations': row.total_observations,
                'unique_species': unique_species_count
            })
        
        return dict(contributors=contributors)
    
    except Exception as e:
        logger.error(f"Error in get_top_contributors: {str(e)}")
        return dict(error=str(e))

@action("get_top_observed_birds", method=["GET"])
@action.uses(db)
def get_top_observed_birds():
    """
    Retrieve the top 10 most observed birds
    """
    try:
        # Query sightings table to get the top 10 most observed birds
        top_observed_birds = db(db.sightings).select(
            db.sightings.COMMON_NAME, 
            db.sightings.OBSERVATION_COUNT.sum().with_alias('total_count'),
            groupby=db.sightings.COMMON_NAME,
            orderby=~db.sightings.OBSERVATION_COUNT.sum(),
            limitby=(0, 10)
        )
        
        # Prepare data for frontend
        bird_data = [
            {
                'species': row.sightings.COMMON_NAME, 
                'total_count': row.total_count
            } for row in top_observed_birds
        ]
        
        return dict(
            success=True,
            species_summary=bird_data
        )
    
    except Exception as e:
        logger.error(f"Error in get_top_observed_birds: {str(e)}")
        return dict(error=str(e), success=False)


@action("get_bird_observation_times", method=["GET"])
@action.uses(db)
def get_bird_observation_times():
    """
    Retrieve top 10 birds by total observation time
    """
    try:
        # First, ensure you have the correct table and field names
        # If 'sightings' table doesn't have DURATION_MINUTES, you might need to join with 'checklist'
        bird_times = db(db.sightings).select(
            db.sightings.COMMON_NAME,
            # Use a subquery or join to get duration
            db.checklist.DURATION_MINUTES.sum().with_alias('total_minutes'),
            left=[db.checklist.on(
                db.checklist.SAMPLING_EVENT_IDENTIFIER == db.sightings.SAMPLING_EVENT_IDENTIFIER
            )],
            groupby=db.sightings.COMMON_NAME,
            orderby=~db.checklist.DURATION_MINUTES.sum(),
            limitby=(0, 10)
        )

        # Prepare data for frontend
        bird_time_data = [
            {
                'species': row.sightings.COMMON_NAME,
                'total_minutes': row.total_minutes
            } for row in bird_times
        ]

        return dict(
            success=True,
            bird_times=bird_time_data
        )
    except Exception as e:
        logger.error(f"Error in get_bird_observation_times: {str(e)}")
        return dict(error=str(e), success=False)