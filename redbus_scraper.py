import streamlit as st
from streamlit_shadcn_ui import table
import pandas as pd
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
from datetime import datetime
import re
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


def init_db():
    conn = sqlite3.connect('new_redbus_bus_data.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bus_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Corporation_Name TEXT,
            Route_Name TEXT,
            Route_Link TEXT,
            Bus_Name TEXT,
            Bus_Type TEXT,
            Departing_Time TEXT,
            Duration TEXT,
            Reaching_Time TEXT,
            Star_Rating FLOAT,
            Price DECIMAL,
            Seat_Availability INT,
            Scrape_Timestamp DATETIME,
            UNIQUE(Corporation_Name, Route_Name, Bus_Name, Departing_Time)
        )
    ''')
    conn.commit()
    return conn

def format_route_for_url(route_name):
    """
    Convert route name to URL format, removing text within brackets and special characters
    Example: "Mumbai (Maharashtra) to Delhi (NCR)" -> "mumbai-to-delhi"
    """
    # Convert to lowercase
    route = route_name.lower()
    
    # Remove text within brackets (both round and square) and the brackets themselves
    route = re.sub(r'\([^)]*\)', '', route)  # Remove (text)
    route = re.sub(r'\[[^\]]*\]', '', route)  # Remove [text] if present
    
    # Replace "to" with "-to-" and handle variations
    route = re.sub(r'\s+to\s+', '-to-', route)
    
    # Remove special characters and extra spaces
    route = re.sub(r'\s+', '-', route)  # Replace multiple spaces with single dash
    route = re.sub(r'[^a-z0-9-]', '', route)  # Remove any remaining special characters
    
    # Remove any multiple dashes that might have been created
    route = re.sub(r'-+', '-', route)
    
    # Remove leading and trailing dashes
    route = route.strip('-')
    
    return route

def create_search_url(route_name):
    formatted_route = format_route_for_url(route_name)
    return f"https://www.redbus.in/bus-tickets/{formatted_route}"

def load_page(driver, url):
    driver.get(url)
    time.sleep(5)

def log_error(url, route_name, corporation_name, error_details):
    with open('error_log.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), url, route_name, corporation_name, error_details])

def scrape_rtc_directory(driver):
    rtc_directory_url = "https://www.redbus.in/online-booking/rtc-directory"
    load_page(driver, rtc_directory_url)
    corporation_elements = driver.find_elements(By.XPATH, "//li[@class='D113_item_rtc']")
    corporation_links = [element.find_element(By.TAG_NAME, 'a').get_attribute('href') for element in corporation_elements]
    corporation_names = [element.text for element in corporation_elements]
    return list(zip(corporation_names, corporation_links))

def scrape_bus_routes(driver):
    route_elements = driver.find_elements(By.CLASS_NAME, 'route')
    bus_routes_link = [route.get_attribute('href') for route in route_elements]
    bus_routes_name = [route.text.strip() for route in route_elements]
    return bus_routes_link, bus_routes_name

def initialize_driver():
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.page_load_strategy = 'eager'
    
    service = Service(r"D:\Downloads\Compressed\chromedriver-win64\chromedriver-win64\chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def wait_and_find_elements(driver, by, selector, timeout=10, retries=3):
    for attempt in range(retries):
        try:
            elements = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by, selector))
            )
            return elements
        except (TimeoutException, StaleElementReferenceException) as e:
            if attempt == retries - 1:
                raise e
            time.sleep(2)
    return []

def scrape_bus_details(driver, url, route_name, corporation_name, conn, is_private=False):
    try:
        driver.get(url)
        time.sleep(5)  # Initial load wait
        
        # For RTC pages, handle the view buses button
        if not is_private:
            try:
                view_buses_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "button"))
                )
                driver.execute_script("arguments[0].click();", view_buses_button)
                time.sleep(3)
            except TimeoutException:
                st.warning(f"No 'View Buses' button found for {route_name}")
                return

        # Initialize set to track unique buses (avoid duplicates across pages)
        processed_buses = set()
        page = 1
        
        while True:
            # Scroll to load all content on current page
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            while scroll_attempts < 5:  # Multiple scroll attempts to ensure all content loads
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_height = new_height

            # Get all bus elements on current page
            bus_elements = {
                'bus_name': wait_and_find_elements(driver, By.CLASS_NAME, "travels.lh-24.f-bold.d-color"),
                'bus_type': wait_and_find_elements(driver, By.CLASS_NAME, "bus-type.f-12.m-top-16.l-color.evBus"),
                'departing_time': wait_and_find_elements(driver, By.CLASS_NAME, "dp-time.f-19.d-color.f-bold"),
                'duration': wait_and_find_elements(driver, By.CLASS_NAME, "dur.l-color.lh-24"),
                'reaching_time': wait_and_find_elements(driver, By.CLASS_NAME, "bp-time.f-19.d-color.disp-Inline"),
                'star_rating': wait_and_find_elements(driver, By.XPATH, "//div[@class='rating-sec lh-24']"),
                'price': wait_and_find_elements(driver, By.CLASS_NAME, "fare.d-block"),
                'seat_availability': wait_and_find_elements(driver, By.XPATH, "//div[contains(@class, 'seat-left m-top-30') or contains(@class, 'seat-left m-top-16')]")
            }

            min_length = min(len(elements) for elements in bus_elements.values())
            
            if min_length == 0:
                if page == 1:
                    st.warning(f"No bus details found for route: {route_name}")
                break

            cursor = conn.cursor()
            new_buses_found = 0
            
            for i in range(min_length):
                try:
                    bus_name = bus_elements['bus_name'][i].text
                    departure_time = bus_elements['departing_time'][i].text
                    
                    # Create unique identifier for bus
                    bus_identifier = f"{bus_name}_{departure_time}"
                    
                    # Skip if we've already processed this bus
                    if bus_identifier in processed_buses:
                        continue
                        
                    processed_buses.add(bus_identifier)
                    new_buses_found += 1

                    star_rating_text = bus_elements['star_rating'][i].text if i < len(bus_elements['star_rating']) else "0.0"
                    star_rating = float(star_rating_text.split()[0]) if star_rating_text else 0.0
                    
                    price_text = bus_elements['price'][i].text if i < len(bus_elements['price']) else "0"
                    price = float(re.sub(r'[^\d.]', '', price_text)) if price_text else 0.0
                    
                    seat_text = bus_elements['seat_availability'][i].text if i < len(bus_elements['seat_availability']) else "0"
                    seats = int(re.sub(r'[^0-9]', '', seat_text)) if seat_text else 0

                    current_corporation = "Private Vehicle" if is_private else corporation_name

                    bus_detail = {
                        "Corporation_Name": current_corporation,
                        "Route_Name": route_name,
                        "Route_Link": url,
                        "Bus_Name": bus_name,
                        "Bus_Type": bus_elements['bus_type'][i].text,
                        "Departing_Time": departure_time,
                        "Duration": bus_elements['duration'][i].text,
                        "Reaching_Time": bus_elements['reaching_time'][i].text,
                        "Star_Rating": star_rating,
                        "Price": price,
                        "Seat_Availability": seats,
                        "Scrape_Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    cursor.execute("""
                        INSERT OR REPLACE INTO bus_details 
                        (Corporation_Name, Route_Name, Route_Link, Bus_Name, Bus_Type, 
                         Departing_Time, Duration, Reaching_Time, Star_Rating, Price, 
                         Seat_Availability, Scrape_Timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(bus_detail.values()))
                    
                    conn.commit()

                except Exception as e:
                    st.error(f"Error processing bus {i} on route {route_name} (page {page}): {str(e)}")
                    log_error(url, route_name, current_corporation, f"Error processing bus {i} on page {page}: {str(e)}")
                    continue

            st.write(f"Processed page {page} for {route_name} - Found {new_buses_found} new buses")
            
            # Check if there's a next page button and it's clickable
            try:
                next_page_element = driver.find_elements(By.XPATH, "//button[contains(@class, 'next-btn')]")
                if not next_page_element or 'disabled' in next_page_element[0].get_attribute('class'):
                    break
                    
                # Click next page and wait for content to load
                driver.execute_script("arguments[0].click();", next_page_element[0])
                time.sleep(5)  # Wait for new page to load
                page += 1
                
            except Exception as e:
                st.write(f"No more pages available for {route_name}")
                break

        st.write(f"Completed scraping {route_name} - Total unique buses found: {len(processed_buses)}")

    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        log_error(url, route_name, corporation_name, str(e))

def scrape_all_pages(url, corporation_name, conn):
    driver = initialize_driver()
    load_page(driver, url)
    all_bus_routes_link, all_bus_routes_name = scrape_bus_routes(driver)

    for link, name in zip(all_bus_routes_link, all_bus_routes_name):
        for attempt in range(3):
            try:
                # Scrape RTC buses
                scrape_bus_details(driver, link, name, corporation_name, conn, is_private=False)
                
                # Create and scrape private vehicle search URL
                search_url = create_search_url(name)
                scrape_bus_details(driver, search_url, name, corporation_name, conn, is_private=True)
                
                # Refresh the DataFrame and display it
                df = pd.read_sql_query("SELECT * FROM bus_details WHERE Route_Name = ?", 
                                     conn, 
                                     params=(name,))
                st.dataframe(df)
                break
            except Exception as e:
                st.warning(f"Attempt {attempt + 1} failed for {name}: {str(e)}")
                time.sleep(5)
        else:
            st.error(f"Failed to scrape details for {name} after 3 attempts")

    driver.quit()
    
def get_unique_values(conn, column_name):
    query = f"SELECT DISTINCT {column_name} FROM bus_details"
    cursor = conn.cursor()
    cursor.execute(query)
    return [row[0] for row in cursor.fetchall()]

def main():
    st.set_page_config(page_title="Redbus Scrapper",
                       page_icon=":bus:",
                       layout="wide",
                       initial_sidebar_state="expanded",)
    st.title("RedBus Scraper - RTC and Private Vehicles data")
    
    st.markdown("""
    <div style="background-color: #d8e2dc; padding: 20px; border-radius: 10px;">
        <p style="font-size: 18px; color: #005b96;">
            <strong>This application</strong> scrapes bus details from RedBus, including information about RTC and private vehicles. The data is extracted using Selenium and stored in a SQLite database. Users can filter and view the scraped data based on various criteria such as route name, corporation name, star rating, and price range.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #d8e2dc; padding: 20px; border-radius: 10px;">
        <p style="font-size: 18px; color: #005b96;">
            <strong>Filtering Options:</strong> Users can filter the data using the sidebar options. These include filtering by route name, corporation name, minimum star rating, and price range. The filtering options are dynamically populated with unique values from the database to provide an intuitive user experience.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Radio buttons for selecting query type
    selected_option = st.radio(
        "Select the option",
        ["Extract Data", "View the Data"],
        captions=["To Scrape the data from Redbus.", "To check the data in the database and filter the data."],
        horizontal=True,
        index=1  # Default selection index
    )
    
    if selected_option == "Extract Data":
        if st.button("Start Scraping"):
            conn = init_db()
            driver = None
            try:
                driver = initialize_driver()
                corporation_links = scrape_rtc_directory(driver)
                
                progress_bar = st.progress(0)
                total_corporations = len(corporation_links)
                
                for idx, (corporation_name, corporation_link) in enumerate(reversed(corporation_links)):
                    st.write(f"Scraping: {corporation_name}")
                    
                    try:
                        scrape_all_pages(corporation_link, corporation_name, conn)
                    except Exception as e:
                        st.error(f"Failed to scrape {corporation_name}: {str(e)}")
                        continue
                    finally:
                        progress_bar.progress((idx + 1) / total_corporations)
                        
                    # Display current results
                    df = pd.read_sql_query(
                        "SELECT * FROM bus_details WHERE Corporation_Name IN (?, 'Private Vehicle')", 
                        conn, 
                        params=(corporation_name,)
                    )
                    st.write(f"Found {len(df)} buses for {corporation_name} (including private vehicles)")
                    st.dataframe(df)
                    
            except Exception as e:
                st.error(f"Main scraping error: {str(e)}")
            finally:
                if driver:
                    driver.quit()
                conn.close()
    
    elif selected_option == "View the Data":
        
        conn = init_db()
        df = pd.read_sql_query("SELECT * FROM bus_details", conn)
        
        # Filtering options with auto-suggestion
        st.sidebar.header("Filter Options")
             
        # Auto-suggest for Route Name
        route_names = get_unique_values(conn, 'Route_Name')
        route_name = st.sidebar.selectbox("Filter by Route Name", [None] + route_names)
        
        # Auto-suggest for Corporation Name
        corporation_names = get_unique_values(conn, 'Corporation_Name')
        corporation_name = st.sidebar.selectbox("Filter by Corporation Name", [None] + corporation_names)
        
        # Auto-suggest for Bus Type
        bus_types = get_unique_values(conn, 'Bus_Type')
        bus_type = st.sidebar.selectbox("Filter by Bus Type", [None] + bus_types)
        
        # Auto-suggest for Departing Time
        departing_times = get_unique_values(conn, 'Departing_Time')
        departing_time = st.sidebar.selectbox("Filter by Departing Time", [None] + sorted(departing_times))
        
        # Slider for Minimum Rating
        min_rating = st.sidebar.slider("Filter by Minimum Rating", 0.0, 5.0, 0.0)
        
        # Number inputs for Price Range
        min_price = st.sidebar.number_input("Filter by Minimum Price", min_value=0.0)
        max_price = st.sidebar.number_input("Filter by Maximum Price", min_value=0.0)
            
        
        # Apply filters
        filtered_df = df
        if route_name:
            filtered_df = filtered_df[filtered_df['Route_Name'] == route_name]
        if corporation_name:
            filtered_df = filtered_df[filtered_df['Corporation_Name'] == corporation_name]
        if bus_type:
            filtered_df = filtered_df[filtered_df['Bus_Type'] == bus_type]
        if departing_time:
            filtered_df = filtered_df[filtered_df['Departing_Time'] >= departing_time]
        if min_rating:
            filtered_df = filtered_df[filtered_df['Star_Rating'] >= min_rating]
        if min_price:
            filtered_df = filtered_df[filtered_df['Price'] >= min_price]
        if max_price:
            filtered_df = filtered_df[filtered_df['Price'] <= max_price]
            
        if st.sidebar.button("Show Data"):
            display_main = st.container(border=True)
            with display_main:
                table(data=filtered_df.head(), maxHeight=500, key="filter_result")
                with st.expander(f"Show full data"):
                    st.dataframe(filtered_df)

            conn.close()

if __name__ == "__main__":
    main()