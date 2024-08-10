import streamlit as st
import pandas as pd
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
from datetime import datetime
import re

# Function to initialize the SQLite connection and create the table if it doesn't exist
def init_db():
    conn = sqlite3.connect('redbus_bus_details.db')
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
            Seat_Availability INT
        )
    ''')
    conn.commit()
    return conn

def initialize_driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    return driver

def load_page(driver, url):
    driver.get(url)
    time.sleep(5)  # Wait for the page to load

def scrape_rtc_directory(driver):
    rtc_directory_url = "https://www.redbus.in/online-booking/rtc-directory"
    load_page(driver, rtc_directory_url)
    
    # Locate the elements using the provided XPath
    corporation_elements = driver.find_elements(By.XPATH, "//li[@class='D113_item_rtc']")
    
    # Extract the href attribute from the child <a> tag of each element
    corporation_links = [element.find_element(By.TAG_NAME, 'a').get_attribute('href') for element in corporation_elements]
    
    # Extract the text of each element to use as corporation names
    corporation_names = [element.text for element in corporation_elements]
    
    return list(zip(corporation_names, corporation_links))

def scrape_bus_routes(driver):
    route_elements = driver.find_elements(By.CLASS_NAME, 'route')
    bus_routes_link = [route.get_attribute('href') for route in route_elements]
    bus_routes_name = [route.text.strip() for route in route_elements]
    return bus_routes_link, bus_routes_name

def log_error(url, route_name, corporation_name, error_details):
    with open('error_log.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), url, route_name, corporation_name, error_details])
        
def scrape_bus_details(driver, url, route_name, corporation_name, conn):
    try:
        driver.get(url)
        time.sleep(5)  # Allow the page to load
        
        # Click the "View Buses" button if it exists
        try:
            view_buses_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "button"))
            )
            driver.execute_script("arguments[0].click();", view_buses_button)
            time.sleep(5)  # Wait for buses to load
            
            # Scroll down to load all bus items
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)  # Wait for the page to load more content

            # Find bus item details
            bus_name_elements = driver.find_elements(By.CLASS_NAME, "travels.lh-24.f-bold.d-color")
            bus_type_elements = driver.find_elements(By.CLASS_NAME, "bus-type.f-12.m-top-16.l-color.evBus")
            departing_time_elements = driver.find_elements(By.CLASS_NAME, "dp-time.f-19.d-color.f-bold")
            duration_elements = driver.find_elements(By.CLASS_NAME, "dur.l-color.lh-24")
            reaching_time_elements = driver.find_elements(By.CLASS_NAME, "bp-time.f-19.d-color.disp-Inline")
            star_rating_elements = driver.find_elements(By.XPATH, "//div[@class='rating-sec lh-24']")
            price_elements = driver.find_elements(By.CLASS_NAME, "fare.d-block")

            # Use XPath to handle both seat availability classes
            seat_availability_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'seat-left m-top-30') or contains(@class, 'seat-left m-top-16')]")

            cursor = conn.cursor()
            for i in range(len(bus_name_elements)):
                try:
                    bus_detail = {
                    "Corporation_Name": corporation_name,
                    "Route_Name": route_name,
                    "Route_Link": url,
                    "Bus_Name": bus_name_elements[i].text,
                    "Bus_Type": bus_type_elements[i].text,
                    "Departing_Time": departing_time_elements[i].text,
                    "Duration": duration_elements[i].text,
                    "Reaching_Time": reaching_time_elements[i].text,
                    "Star_Rating": float(star_rating_elements[i].text.split()[0]) if i < len(star_rating_elements) and star_rating_elements[i].text else 0.0,
                    "Price": float(re.sub(r'[^\d.]', '', price_elements[i].text)) if i < len(price_elements) else 0.0,
                    "Seat_Availability": int(re.sub(r'[^0-9]', '', seat_availability_elements[i].text)) if i < len(seat_availability_elements) else 0
                    }

                    cursor.execute("""
                        INSERT INTO bus_details (Corporation_Name, Route_Name, Route_Link, Bus_Name, Bus_Type, Departing_Time, Duration, Reaching_Time, Star_Rating, Price, Seat_Availability)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        bus_detail["Corporation_Name"],
                        bus_detail["Route_Name"],
                        bus_detail["Route_Link"],
                        bus_detail["Bus_Name"],
                        bus_detail["Bus_Type"],
                        bus_detail["Departing_Time"],
                        bus_detail["Duration"],
                        bus_detail["Reaching_Time"],
                        bus_detail["Star_Rating"],
                        bus_detail["Price"],
                        bus_detail["Seat_Availability"]
                    ))

                    conn.commit()


                except Exception as e:
                    st.error(f"Error inserting data for bus {i} on route {route_name}: {str(e)}")
                    log_error(url, route_name, corporation_name, f"Error inserting data for bus {i}: {str(e)}")

        except Exception as e:
            error_message = f"Error occurred while scraping bus details for {url}: {str(e)}"
            st.error(error_message)
            log_error(url, route_name, corporation_name, error_message)

    except Exception as e:
        error_message = f"Error occurred while accessing {url}: {str(e)}"
        st.error(error_message)
        log_error(url, route_name, corporation_name, error_message)

def scrape_all_pages(url, corporation_name, conn):
    driver = initialize_driver()
    load_page(driver, url)
    all_bus_routes_link, all_bus_routes_name = scrape_bus_routes(driver)

    for link, name in zip(all_bus_routes_link, all_bus_routes_name):
        for attempt in range(3):  # Retry up to 3 times
            try:
                scrape_bus_details(driver, link, name, corporation_name, conn)
                # Refresh the DataFrame and display it in Streamlit
                df = pd.read_sql_query("SELECT * FROM bus_details", conn)
                st.dataframe(df)
                break  # If successful, break out of the retry loop
            except Exception as e:
                st.warning(f"Attempt {attempt + 1} failed for {name} on {link}: {str(e)}")
                time.sleep(5)  # Wait before retrying
        else:
            st.error(f"Failed to scrape details for {name} on {link} after 3 attempts")

    driver.quit()

def main():
    conn = init_db()
    driver = initialize_driver()
    corporation_links = scrape_rtc_directory(driver)
    driver.quit()

    for corporation_name, corporation_link in corporation_links:
        st.write(f"Scraping buses for: {corporation_name} - {corporation_link}")
        for attempt in range(3):  # Retry up to 3 times
            try:
                scrape_all_pages(corporation_link, corporation_name, conn)
                break  # If successful, break out of the retry loop
            except Exception as e:
                st.warning(f"Attempt {attempt + 1} failed for {corporation_name}: {str(e)}")
                time.sleep(10)  # Wait before retrying
        else:
            st.error(f"Failed to scrape details for {corporation_name} after 3 attempts")

    conn.close()

# Streamlit UI
st.title("Bus Details Scraper")

if st.button("Start Scraping"):
    main()

# Read the data for display in the Streamlit app
conn = init_db()
st.write("### Scraped Bus Details")
df = pd.read_sql_query("SELECT * FROM bus_details", conn)
st.dataframe(df)
conn.close()