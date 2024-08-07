from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import itertools
import pandas as pd

def search_flight_live(origin, destination, date):
    url = f"https://www.aircanada.com/aeroplan/redeem/availability/outbound?org0={origin}&dest0={destination}&departureDate0={date}&ADT=1&YTH=0&CHD=0&INF=0&INS=0&lang=en-CA&tripType=O&marketCode=INT"
    
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Commented out to see the browser live
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--ignore-certificate-errors')
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    

    options.add_argument("window-size=1920,1080")
    options.add_argument("start-maximized")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # self.driver = webdriver.Chrome(options=options)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        print(f"Searching: {origin} to {destination} on {date}")
        
        # Wait for the loading spinner to disappear
        print("Waiting for loading spinner to disappear...")
        WebDriverWait(driver, 60).until(
            EC.invisibility_of_element((By.CSS_SELECTOR, "kilo-loading-spinner-pres"))
        )
        print("Loading spinner disappeared.")

        # Wait for the flights count element to be present
        print("Waiting for flights count element to be present...")
        flights_count_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.flights-count"))
        )
        flights_count = flights_count_element.text
        print(f"Flights count text: {flights_count}")

        # Extract number of flights found from the text
        print("Extracting flights found text...")
        flights_found_element = driver.find_element(By.CSS_SELECTOR, "span.flights-count + span")
        flights_found = flights_found_element.text
        print(f"Flights found: {flights_found}")

        return flights_found
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Error"
    finally:
        driver.quit()

if __name__ == "__main__":
    # Example usage
    origin = "YYZ"
    destination = "AMM"
    date = "2024-08-10"
    search_flight_live(origin, destination, date)
