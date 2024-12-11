import os
import csv
import datetime
from .common import db, Field, auth
from pydal.validators import *

class DataSeeder:
    @staticmethod
    def _read_csv(file_path):
        """
        Helper method to safely read CSV files
        
        Args:
            file_path (str): Path to the CSV file
        
        Returns:
            list: List of dictionaries containing CSV data
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r') as f:
                return list(csv.DictReader(f))
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []

    @classmethod
    def seed_table(cls, table, csv_path, mapping_func):
        """
        Generic method to seed database tables
        
        Args:
            table: Database table to seed
            csv_path (str): Path to the CSV file
            mapping_func (callable): Function to map CSV rows to database rows
        """
        # Clear existing data before seeding
        db(table.id > 0).delete()
        db.commit()

        data = cls._read_csv(csv_path)
        try:
            for row in data:
                table.insert(**mapping_func(row))
            db.commit()
            print(f"{table._tablename} table seeded successfully.")
        except Exception as e:
            print(f"Error seeding {table._tablename} table: {e}")

def get_user_email():
    return auth.current_user.get('email') if auth.current_user else None

def get_time():
    return datetime.datetime.utcnow()

def define_database_tables():
    """
    Database table definitions with clear, unique field creation
    """
    # Species table
    if 'species' not in db.tables():
        db.define_table('species', 
            Field('COMMON_NAME', 'string')
        )

    # Sightings table
    if 'sightings' not in db.tables():
        db.define_table('sightings', 
            Field('SAMPLING_EVENT_IDENTIFIER', 'string'),
            Field('COMMON_NAME', 'string'),
            Field('OBSERVATION_COUNT', 'string')
        )

    # Checklist table
    if 'checklist' not in db.tables():
        db.define_table('checklist', 
            Field('SAMPLING_EVENT_IDENTIFIER', 'string'),
            Field('LATITUDE', 'double'),
            Field('LONGITUDE', 'double'),
            Field('OBSERVATION_DATE', 'date'),
            Field('TIME_OBSERVATIONS_STARTED', 'time'),
            Field('OBSERVER_ID', 'string'),
            Field('DURATION_MINUTES', 'double')
        )

    # My Checklist table
    if 'my_checklist' not in db.tables():
        db.define_table('my_checklist', 
            Field('SAMPLING_EVENT_IDENTIFIER', 'string'),
            Field('COMMON_NAME', 'string'),
            Field('LATITUDE', 'double'),
            Field('LONGITUDE', 'double'),
            Field('OBSERVATION_DATE', 'date'),
            Field('TIME_OBSERVATIONS_STARTED', 'time'),
            Field('OBSERVER_ID', 'string'),
            Field('DURATION_MINUTES', 'double')
        )

def seed_database():
    base_path = os.path.join(os.getcwd(), "apps/birds/uploads")
    
    # Seeding configurations
    seeding_config = [
        {
            'table': db.species,
            'file': os.path.join(base_path, 'species.csv'),
            'mapper': lambda row: {'COMMON_NAME': row['COMMON NAME'].strip()}
        },
        {
            'table': db.sightings,
            'file': os.path.join(base_path, 'sightings.csv'),
            'mapper': lambda row: {
                'SAMPLING_EVENT_IDENTIFIER': row['SAMPLING_EVENT_IDENTIFIER'],
                'COMMON_NAME': row['COMMON_NAME'],
                'OBSERVATION_COUNT': row.get('OBSERVATION_COUNT', 0)
            }
        },
        {
            'table': db.checklist,
            'file': os.path.join(base_path, 'checklists.csv'),
            'mapper': lambda row: {
                'SAMPLING_EVENT_IDENTIFIER': row['SAMPLING_EVENT_IDENTIFIER'],
                'LATITUDE': float(row['LATITUDE']),
                'LONGITUDE': float(row['LONGITUDE']),
                'OBSERVATION_DATE': row['OBSERVATION_DATE'],
                'TIME_OBSERVATIONS_STARTED': row['TIME_OBSERVATIONS_STARTED'],
                'OBSERVER_ID': row['OBSERVER_ID'],
                'DURATION_MINUTES': float(row['DURATION_MINUTES'])
            }
        }
    ]
    
    # Seed tables
    for config in seeding_config:
        DataSeeder.seed_table(
            config['table'], 
            config['file'], 
            config['mapper']
        )

# Initialize tables and seed database
define_database_tables()
seed_database()