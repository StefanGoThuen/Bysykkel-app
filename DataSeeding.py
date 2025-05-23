from shiny import App, ui, render
import sqlite3
import pandas as pd

df = pd.read_csv("bysykkel.csv")

conn = sqlite3.connect("bysykkel.db")
cursor = conn.cursor()

# Create User table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS User (
        UserID INTEGER PRIMARY KEY,
        Name TEXT,
        PhoneNumber TEXT
    )
""")

# Create Subscription table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Subscription (
        SubscriptionID INTEGER PRIMARY KEY,
        UserID INTEGER,
        Type TEXT,
        Start DATETIME,
        FOREIGN KEY (UserID) REFERENCES User(UserID)
    )
""")

# Create Station table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Station (
        StationID INTEGER PRIMARY KEY,
        Name TEXT,
        Latitude REAL,
        Longitude REAL,
        MaxSpots INTEGER,
        AvailableSpots INTEGER
    )
""")

# Create Bike table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Bike (
        BikeID INTEGER PRIMARY KEY,
        Name TEXT,
        Status TEXT,
        StationID INTEGER,
        FOREIGN KEY (StationID) REFERENCES Station(StationID)
    )
""")

# Create Trip table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS Trip (
        TripID INTEGER PRIMARY KEY,
        UserID INTEGER,
        BikeID INTEGER,
        StartTime DATETIME,
        EndTime DATETIME,
        StartStationID INTEGER,
        EndStationID INTEGER,
        FOREIGN KEY (UserID) REFERENCES User(UserID),
        FOREIGN KEY (BikeID) REFERENCES Bike(BikeID),
        FOREIGN KEY (StartStationID) REFERENCES Station(StationID),
        FOREIGN KEY (EndStationID) REFERENCES Station(StationID)
    )
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Maintenance (
    MaintenanceID INTEGER PRIMARY KEY AUTOINCREMENT,
    BikeID INTEGER,
    ReportedAt DATETIME,
    Complaint TEXT,
    FOREIGN KEY (BikeID) REFERENCES Bike(BikeID)
)
""")
conn.commit()


conn.commit()

# Users
df_users = df[['user_id', 'user_name', 'user_phone_number']].drop_duplicates().dropna()
df_users.columns = ['UserID', 'Name', 'PhoneNumber']
df_users.to_sql("User", conn, if_exists="append", index=False)

# Subscriptions
df_subscriptions = df[['subscription_id', 'user_id', 'subscription_type', 'subscription_start_time']].drop_duplicates().dropna()
df_subscriptions.columns = ['SubscriptionID', 'UserID', 'Type', 'Start']
df_subscriptions.to_sql("Subscription", conn, if_exists="append", index=False)

# Stations
df_stations = df[['start_station_id', 'start_station_name', 'end_station_latitude', 'end_station_longitude', 'end_station_max_spots', 'end_station_available_spots']].drop_duplicates().dropna()
df_stations.columns = ['StationID', 'Name', 'Latitude', 'Longitude', 'MaxSpots', 'AvailableSpots']
df_stations.to_sql("Station", conn, if_exists="append", index=False)

# Bikes
df_bikes = df[['bike_id', 'bike_name', 'bike_status', 'bike_station_id']].drop_duplicates().dropna()
df_bikes.columns = ['BikeID', 'Name', 'Status', 'StationID']
df_bikes.to_sql("Bike", conn, if_exists="append", index=False)

# Trips
df_trips = df[['trip_id', 'user_id', 'bike_id', 'trip_start_time', 'trip_end_time', 'start_station_id', 'end_station_id']].drop_duplicates().dropna()
df_trips.columns = ['TripID', 'UserID', 'BikeID', 'StartTime', 'EndTime', 'StartStationID', 'EndStationID']
df_trips.to_sql("Trip", conn, if_exists="append", index=False)

conn.commit()
conn.close()