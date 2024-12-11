import datetime
import os
import csv
from .common import db, auth
from pydal import Field
from pydal.validators import *

def get_user_email():
    return auth.current_user.get('email') if auth.current_user else None

def current_utc_time():
    return datetime.datetime.utcnow()

# Database Table Definitions
db.define_table(
    "bird_species",
    Field("name", "string", requires=IS_NOT_EMPTY(), label="Species Name")
)

db.define_table(
    "bird_sightings",
    Field("event_code", "string", label="Event Code"),
    Field("species_name", "string", label="Species Name"),
    Field("count", "integer", requires=IS_INT_IN_RANGE(0, None), label="Count")
)

db.define_table(
    "observation_checklist",
    Field("event_code", "string", label="Event Code"),
    Field("lat", "double", requires=IS_FLOAT_IN_RANGE(-90, 90), label="Latitude"),
    Field("lon", "double", requires=IS_FLOAT_IN_RANGE(-180, 180), label="Longitude"),
    Field("date", "date", requires=IS_DATE(), label="Observation Date"),
    Field("start_time", "time", requires=IS_TIME(), label="Start Time"),
    Field("observer", "string", label="Observer ID"),
    Field("duration", "double", requires=IS_FLOAT_IN_RANGE(0, None), label="Duration (Minutes)")
)

db.define_table(
    "user_observations",
    Field("event_code", "string", label="Event Code"),
    Field("species_name", "string", label="Species Name"),
    Field("lat", "double", requires=IS_FLOAT_IN_RANGE(-90, 90), label="Latitude"),
    Field("lon", "double", requires=IS_FLOAT_IN_RANGE(-180, 180), label="Longitude"),
    Field("date", "date", requires=IS_DATE(), label="Observation Date"),
    Field("start_time", "time", requires=IS_TIME(), label="Start Time"),
    Field("observer", "string", label="Observer ID"),
    Field("duration", "double", requires=IS_FLOAT_IN_RANGE(0, None), label="Duration (Minutes)")
)

# Seed Functions
def populate_species():
    species_file = os.path.join(os.getcwd(), "apps/birds/uploads/species.csv")
    db(db.bird_species.id > 0).delete()
    db.commit()
    if os.path.exists(species_file):
        try:
            with open(species_file, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    db.bird_species.insert(name=row["COMMON NAME"].strip())
            db.commit()
            print("Successfully seeded bird_species table.")
        except Exception as error:
            print(f"Error populating bird_species: {error}")
    else:
        print(f"File not found: {species_file}")

def populate_sightings():
    sightings_file = os.path.join(os.getcwd(), "apps/birds/uploads/sightings.csv")
    if db(db.bird_sightings).isempty():
        try:
            with open(sightings_file, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    count = int(row["OBSERVATION_COUNT"]) if row["OBSERVATION_COUNT"].isdigit() else 0
                    db.bird_sightings.insert(
                        event_code=row["SAMPLING_EVENT_IDENTIFIER"],
                        species_name=row["COMMON NAME"],
                        count=count
                    )
            db.commit()
            print("Successfully seeded bird_sightings table.")
        except Exception as error:
            print(f"Error populating bird_sightings: {error}")

def populate_checklists():
    checklist_file = os.path.join(os.getcwd(), "apps/birds/uploads/checklists.csv")
    if db(db.observation_checklist).isempty():
        try:
            with open(checklist_file, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    db.observation_checklist.insert(
                        event_code=row["SAMPLING_EVENT_IDENTIFIER"],
                        lat=float(row["LATITUDE"]),
                        lon=float(row["LONGITUDE"]),
                        date=row["OBSERVATION_DATE"],
                        start_time=row["TIME_OBSERVATIONS_STARTED"],
                        observer=row["OBSERVER_ID"],
                        duration=float(row["DURATION_MINUTES"])
                    )
            db.commit()
            print("Successfully seeded observation_checklist table.")
        except Exception as error:
            print(f"Error populating observation_checklist: {error}")

populate_species()
populate_sightings()
populate_checklists()

db.commit()
