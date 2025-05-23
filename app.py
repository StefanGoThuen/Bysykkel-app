from shiny import App, ui, render, reactive
import sqlite3
import pandas as pd
import re
from datetime import datetime

def get_db_connection():
    return sqlite3.connect("bysykkel.db")

def get_user_names():
    conn = get_db_connection()
    users = pd.read_sql("SELECT Name FROM User", conn)
    conn.close()
    return users["Name"].tolist()

def get_station_names():
    conn = get_db_connection()
    station = pd.read_sql("SELECT Name FROM Station", conn)
    conn.close()
    return station["Name"].tolist()

userNames = get_user_names()
station = get_station_names()

complaints_list = [
    "Flat tire",
    "Broken chain",
    "Handlebar loose",
    "Seat damaged",
    "Brakes not working",
    "Wheel misaligned",
    "Bell not working",
    "Gears not shifting",
    "Pedal broken",
    "Stand issue",
    "Frame cracked",
    "Other"
]


# UI Layout
app_ui = ui.page_fluid(
    ui.h1("Bergen Bysykkel Dashboard"),
    ui.br(),

    ui.h2("Register a New User"),
    ui.input_text("name", "Name"),
    ui.input_text("phone", "Phone Number"),
    ui.input_text("email", "Email"),
    ui.input_action_button("submit", "Submit"),
    ui.output_text("submission_result"),
    ui.br(),

    ui.h3("Filter Users by Name"),
    ui.input_text("user_filter", "Search by Name"),
    ui.h2("Users List"),
    ui.output_data_frame("users_table"),
    ui.br(),


    ui.h2("Bikes & Their Status"),
    ui.output_data_frame("bikes_table"),
    ui.br(),

    ui.h2("Trip Count per End Station"),
    ui.output_data_frame("trip_station_count"),
    ui.br(),

    ui.h2("Available Bikes by Station"),
    ui.input_text("station_filter", "Station Name Filter"),
    ui.input_text("bike_filter", "Bike Name Filter"),
    ui.output_data_frame("station_bikes_table"),
    ui.br(),

    ui.h2("Subscription Type Count"),
    ui.output_data_frame("subscription_count"),
    ui.br(),    

    ui.h2("CHECKOUT"),
    ui.input_select("checkout_user", "Select User", choices=userNames),
    ui.input_select("checkout_station", "Select Station", choices=station),
    ui.input_action_button("do_checkout", "Check Out Bike"),
    ui.output_text("checkout_status"),
    ui.br(),

    ui.h2("DROPOFF"),
    ui.input_select("dropoff_user", "Select User", choices=userNames),
    ui.input_select("dropoff_station", "Select Station", choices=station),
    ui.input_action_button("do_dropoff", "Drop Off Bike"),
    ui.output_text("dropoff_status"),
    ui.br(),

    ui.h4("Bike Condition"),
    ui.input_checkbox_group("bike_complaints", "Is there anything wrong with the bike?", complaints_list),
    ui.input_action_button("report_maintenance", "Submit Maintenance Report"),
    ui.output_text("maintenance_status"),

    ui.h2("Station Availability Map"),
    ui.input_selectize("selected_station", "Choose a Station", choices=station, multiple=False),
    ui.input_switch("trip_in_progress", "Trip in Progress", value=True),
    ui.output_table("availability_table")

)

# Validation
def is_valid_name(name):
    return bool(re.match(r'^[A-Za-zÆØÅæøå\s]+$', name))

def is_valid_email(email):
    return "@" in email

def is_valid_phone(phone):
    return phone.isdigit() and len(phone) == 8

# Server Logic
def server(input, output, session):

    @output
    @render.text
    def submission_result():
        if input.submit() == 0:
            return ""

        name = input.name()
        phone = input.phone()
        email = input.email()

        name_valid = is_valid_name(name)
        phone_valid = is_valid_phone(phone)
        email_valid = is_valid_email(email)

        result = f"{name} - {'Valid' if name_valid else 'Not valid'}\n"
        result += f"{email} - {'Valid' if email_valid else 'Not valid'}\n"
        result += f"{phone} - {'Valid' if phone_valid else 'Not valid'}\n"

        if name_valid and phone_valid and email_valid:
            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("ALTER TABLE User ADD COLUMN Email TEXT")
            except sqlite3.OperationalError:
                pass 

            try:
                cursor.execute("INSERT INTO User (Name, PhoneNumber, Email) VALUES (?, ?, ?)", (name, phone, email))
                conn.commit()
                result += "\nUser successfully added to the database."
            except Exception as e:
                result += f"\nDatabase error: {e}"
            finally:
                conn.close()
        else:
            result += "\nUser NOT added due to invalid input."

        return result

    @output
    @render.data_frame
    def users_table():
        conn = get_db_connection()
        query = "SELECT UserID, Name, PhoneNumber FROM User"
        df = pd.read_sql(query, conn)
        conn.close()

        if input.user_filter():
            keyword = input.user_filter().lower()
            df = df[df["Name"].str.lower().str.contains(keyword)]

        return df

    @output
    @render.data_frame
    def bikes_table():
        conn = get_db_connection()
        df = pd.read_sql("SELECT Name, Status FROM Bike", conn)
        conn.close()
        return df
    
    @output
    @render.data_frame
    def trip_station_count():
        conn = get_db_connection()
        query = """
            SELECT s.StationID, s.Name, COUNT(t.TripID) AS NumberOfTrips
            FROM Trip t
            JOIN Station s ON t.EndStationID = s.StationID
            GROUP BY s.StationID, s.Name
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    @output
    @render.data_frame
    def station_bikes_table():
        conn = get_db_connection()
        query = """
            SELECT s.Name as Station, b.Name as Bike, b.Status
            FROM Bike b
            JOIN Station s ON b.StationID = s.StationID
            WHERE b.Status = 'Parked'
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if input.station_filter():
            df = df[df["Station"].str.lower().str.contains(input.station_filter().lower())]
        if input.bike_filter():
            df = df[df["Bike"].str.lower().str.contains(input.bike_filter().lower())]

        return df

    @output
    @render.data_frame
    def subscription_count():
        conn = get_db_connection()
        df = pd.read_sql("SELECT Type, COUNT(*) as Purchased FROM Subscription GROUP BY Type", conn)
        conn.close()
        return df
    

    @output
    @render.text
    def checkout_status():
        if input.do_checkout() == 0:
            return ""

        user_name = input.checkout_user()
        station_name = input.checkout_station()

        if not user_name or not station_name:
            return "Please select both a user and a station."

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT BikeID FROM Bike
            WHERE StationID = (SELECT StationID FROM Station WHERE Name = ?) AND Status = 'Parked'
            LIMIT 1
        """, (station_name,))
        bike = cursor.fetchone()

        if not bike:
            conn.close()
            return "No available bikes at this station."

        bike_id = bike[0]
        now = datetime.now().isoformat()

        try:
            cursor.execute("""
                INSERT INTO Trip (UserID, BikeID, StartTime, StartStationID)
                VALUES ((SELECT UserID FROM User WHERE Name = ?), ?, ?, (SELECT StationID FROM Station WHERE Name = ?))
            """, (user_name, bike_id, now, station_name))

            cursor.execute("""
                UPDATE Bike SET Status = 'Active', StationID = NULL WHERE BikeID = ?
            """, (bike_id,))

            conn.commit()
            return f"User {user_name} successfully checked out Bike {bike_id}."
        except Exception as e:
            return f"Error: {e}"
        finally:
            conn.close()

    @output
    @render.text
    def dropoff_status():
        if input.do_dropoff() == 0:
            return ""

        user_name = input.dropoff_user()
        station_name = input.dropoff_station()

        if not user_name or not station_name:
            return "Please select both a user and a station."

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT UserID FROM User WHERE Name = ?", (user_name,))
        user_row = cursor.fetchone()

        cursor.execute("SELECT StationID FROM Station WHERE Name = ?", (station_name,))
        station_row = cursor.fetchone()

        if not user_row or not station_row:
            conn.close()
            return "User or Station not found."

        user_id = user_row[0]
        station_id = station_row[0]

        cursor.execute("""
            SELECT TripID, BikeID FROM Trip
            WHERE UserID = ? AND EndTime IS NULL
            ORDER BY StartTime DESC LIMIT 1
        """, (user_id,))
        trip = cursor.fetchone()

        if not trip:
            conn.close()
            return f"{user_name} does not have any active trip."

        trip_id, bike_id = trip
        now = datetime.now().isoformat()

        try:
            cursor.execute("""
                UPDATE Trip
                SET EndTime = ?, EndStationID = ?
                WHERE TripID = ?
            """, (now, station_id, trip_id))

            cursor.execute("""
                UPDATE Bike
                SET Status = 'Parked', StationID = ?
                WHERE BikeID = ?
            """, (station_id, bike_id))

            conn.commit()

            return f"{user_name} returned Bike {bike_id} to {station_name}."
        except Exception as e:
            return f"Error during drop-off: {e}"
        finally:
            conn.close()

    @output
    @render.text
    def maintenance_status():
        if input.report_maintenance() == 0:
            return ""

        conn = get_db_connection()
        cursor = conn.cursor()

        user_name = input.dropoff_user()
        cursor.execute("SELECT UserID FROM User WHERE Name = ?", (user_name,))
        user_id = cursor.fetchone()
        if not user_id:
            return "User not found."
        
        user_id = user_id[0]
        cursor.execute("""
            SELECT BikeID FROM Trip
            WHERE UserID = ? AND EndTime IS NOT NULL
            ORDER BY EndTime DESC LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return "No recent dropoff found."

        bike_id = row[0]
        reported_at = pd.Timestamp.now().isoformat()
        complaints = input.bike_complaints()

        try:
            for complaint in complaints:
                cursor.execute("""
                    INSERT INTO Maintenance (BikeID, ReportedAt, Complaint)
                    VALUES (?, ?, ?)
                """, (bike_id, reported_at, complaint))

            conn.commit()
            return "Maintenance issues reported successfully."
        except Exception as e:
            return f"Error saving maintenance: {e}"
        finally:
            conn.close()


    @output
    @render.table(render_links=True, escape=False)
    def availability_table():
        selected_name = input.selected_station()
        in_progress = input.trip_in_progress()

        if not selected_name:
            return pd.DataFrame(columns=["Name", "Availability", "Location"])

        conn = get_db_connection()
        query = """
            SELECT Name, Latitude, Longitude, MaxSpots, AvailableSpots
            FROM Station
            WHERE Name = ?
        """
        station = pd.read_sql(query, conn, params=(selected_name,))
        conn.close()

        if station.empty:
            return pd.DataFrame(columns=["Name", "Availability", "Location"])

        row = station.iloc[0]
        max_spots = row["MaxSpots"]
        available = row["AvailableSpots"]

        if max_spots == 0:
            availability_pct = 0
        elif in_progress:
            availability_pct = (available / max_spots) * 100
        else:
            availability_pct = ((max_spots - available) / max_spots) * 100

        link = f'<a href="https://www.openstreetmap.org/#map=17/{row["Latitude"]}/{row["Longitude"]}" target="_blank">Map</a>'

        return pd.DataFrame([{
            "Name": row["Name"],
            "Availability": f"{availability_pct:.0f}%",
            "Location": link
        }])

app = App(app_ui, server)
