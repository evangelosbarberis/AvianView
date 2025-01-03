import os
import csv
import datetime
from .common import db, Field, auth
from pydal.validators import *

def get_user_email():
    """Returns the current user's email or None"""
    return auth.current_user.get('email') if auth.current_user else None

def get_time():
    """Returns the current UTC time"""
    return datetime.datetime.utcnow()

class DataSeeder:
    @staticmethod
    def _read_csv(file_path):
        """
        Read a CSV file and return its contents as a list of dictionaries
        
        Args:
            file_path (str): Path to the CSV file
        
        Returns:
            list: Contents of the CSV file
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Use strip to remove potential whitespace
                return [
                    {k.strip(): v.strip() for k, v in row.items()} 
                    for row in csv.DictReader(f)
                ]
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []

    @classmethod
    def seed_table(cls, table, csv_path, mapping_func, verbose=True):
        """
        Seed a database table from a CSV file with robust error handling
        
        Args:
            table: Database table to seed
            csv_path (str): Path to the CSV file
            mapping_func (callable): Function to map CSV rows to table fields
            verbose (bool): Whether to print seeding progress
        """
        # Clear existing data before seeding
        db(table.id > 0).delete()
        db.commit()

        data = cls._read_csv(csv_path)
        
        if not data:
            print(f"No data found in {csv_path}")
            return

        try:
            inserted_count = 0
            for row in data:
                try:
                    # Use mapping function with error handling
                    mapped_row = mapping_func(row)
                    table.insert(**mapped_row)
                    inserted_count += 1
                except Exception as row_error:
                    print(f"Error processing row: {row}. Error: {row_error}")
            
            db.commit()
            if verbose:
                print(f"{table._tablename} table seeded successfully with {inserted_count} records.")
        except Exception as e:
            print(f"Error seeding {table._tablename} table: {e}")
            db.rollback()

def define_database_tables():
    """
    Define database tables with comprehensive fields
    
    This ensures each table has appropriate fields for bird tracking data
    """
    # Species table for bird species information
    if 'species' not in db.tables():
        db.define_table('species', 
            Field('COMMON_NAME', type='string', required=True, unique=True),
            Field('scientific_name', type='string'),
            Field('conservation_status', type='string')
        )

    # Sightings table for individual bird observations
    if 'sightings' not in db.tables():
        db.define_table('sightings', 
            Field('SAMPLING_EVENT_IDENTIFIER', type='string', required=True),
            Field('COMMON_NAME', type='string', required=True),
            Field('OBSERVATION_COUNT', type='integer', default=1),
            Field('observer_email', type='string', default=get_user_email),
            Field('observation_time', type='datetime', default=get_time)
        )

    # Main checklist table for entire observation events
    if 'checklist' not in db.tables():
        db.define_table('checklist', 
            Field('SAMPLING_EVENT_IDENTIFIER', type='string', required=True, unique=True),
            Field('LATITUDE', type='double', required=True),
            Field('LONGITUDE', type='double', required=True),
            Field('OBSERVATION_DATE', type='date', required=True),
            Field('TIME_OBSERVATIONS_STARTED', type='time', required=True),
            Field('OBSERVER_ID', type='string'),
            Field('DURATION_MINUTES', type='double', default=0),
            Field('notes', type='text')
        )

    # Personal checklist for user-specific tracking
    if 'my_checklist' not in db.tables():
        db.define_table('my_checklist', 
            Field('user_email', type='string', default=get_user_email),
            Field('SAMPLING_EVENT_IDENTIFIER', type='string'),
            Field('COMMON_NAME', type='string'),
            Field('LATITUDE', type='double', required=True),
            Field('LONGITUDE', type='double', required=True),
            Field('OBSERVATION_DATE', type='date', required=True),
            Field('TIME_OBSERVATIONS_STARTED', type='time', required=True),
            Field('DURATION_MINUTES', type='double', default=0)
        )

    # Hotspots for tracking notable bird observation locations
    if 'hotspots' not in db.tables():
        db.define_table('hotspots',
            Field('name', type='string', required=True),
            Field('description', type='text'),
            Field('latitude', type='double', required=True),
            Field('longitude', type='double', required=True),
            Field('popularity_score', type='integer', default=0)
        )

def seed_database(base_path=None):
    if base_path is None:
        base_path = os.path.join(os.getcwd(), "apps/birds/uploads")

    # Add more verbose logging
    print("Starting database seeding process...")

    # Seeding configurations with more robust mapping
    seeding_config = [
        {
            'table': db.species,
            'file': os.path.join(base_path, 'species.csv'),
            'mapper': lambda row: {
                'SAMPLING_EVENT_IDENTIFIER': row.get('SAMPLING EVENT IDENTIFIER', '').strip(),
                'COMMON_NAME': row.get('COMMON NAME', '').strip(),
                'OBSERVATION_COUNT': 1 if row.get('OBSERVATION COUNT', 'X') == 'X' else int(row.get('OBSERVATION COUNT', 1)),
                'observer_email': row.get('OBSERVER EMAIL', '').strip() or get_user_email(),
                'observation_time': get_time()
            }
        },
        {
            'table': db.checklist,
            'file': os.path.join(base_path, 'checklists.csv'),
            'mapper': lambda row: {
                'SAMPLING_EVENT_IDENTIFIER': row.get('SAMPLING EVENT IDENTIFIER', str(get_time())).strip(),
                'LATITUDE': float(row.get('LATITUDE', 0)),
                'LONGITUDE': float(row.get('LONGITUDE', 0)),
                'OBSERVATION_DATE': row.get('OBSERVATION DATE', datetime.date.today()),
                'TIME_OBSERVATIONS_STARTED': row.get('TIME OBSERVATIONS STARTED', datetime.time()),
                'OBSERVER_ID': row.get('OBSERVER ID', '').strip(),
                'DURATION_MINUTES': float(row.get('DURATION MINUTES', 0)) if row.get('DURATION MINUTES', '').strip() else 0.0
            }
        },
        {
            'table': db.sightings,
            'file': os.path.join(base_path, 'sightings.csv'),
            'mapper': lambda row: {
                'SAMPLING_EVENT_IDENTIFIER': row.get('SAMPLING EVENT IDENTIFIER', '').strip(),
                'COMMON_NAME': row.get('COMMON NAME', '').strip(),
                'OBSERVATION_COUNT': 1 if row.get('OBSERVATION COUNT', 'X') == 'X' else int(row.get('OBSERVATION COUNT', 1)),
                'observer_email': row.get('OBSERVER EMAIL', '').strip() or get_user_email(),
                'observation_time': get_time()
            }
        }
    ]

    # Seed tables with error handling and logging
    for config in seeding_config:
        try:
            print(f"Seeding {config['table']._tablename}...")
            DataSeeder.seed_table(
                config['table'], 
                config['file'], 
                config['mapper'],
                verbose=True
            )
        except Exception as e:
            print(f"Error seeding {config['table']._tablename}: {e}")

    print("Database seeding completed.")

# Initialize database tables and seed
define_database_tables()
seed_database()