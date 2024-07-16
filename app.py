from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import itertools
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    origin = request.form['origin'].split(',')
    destination = request.form['destination'].split(',')
    date_input = request.form['date']
    
    if ':' in date_input:
        start_date, end_date = date_input.split(':')
        dates = pd.date_range(start_date, end_date).strftime('%Y-%m-%d').tolist()
    else:
        dates = date_input.split(',')

    permutations = list(itertools.product(origin, destination, dates))
    results = []

    for org, dest, date in permutations:
        result = search_flight_live(org.strip(), dest.strip(), date.strip())
        results.append((org, dest, date, result))
    
    return render_template('results.html', results=results, permutations=len(permutations))

def search_flight_live(origin, destination, date):
    url = f"https://www.aircanada.com/aeroplan/redeem/availability/outbound?org0={origin}&dest0={destination}&departureDate0={date}&ADT=1&YTH=0&CHD=0&INF=0&INS=0&lang=en-CA&tripType=O&marketCode=INT"
    
    options = webdriver.ChromeOptions()
    # Remove headless option to see the browser live
    # options.add_argument('--headless')
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

        # Extract flight details
        print("Extracting flight details...")
        flight_details = []

        # Locate the main container for flight details
        flight_containers = driver.find_elements(By.CSS_SELECTOR, "kilo-upsell-row-cont")
        print(f"Found {len(flight_containers)} flight containers.")

        for container in flight_containers:
            flight_info = {}
            flight_info['segments'] = []

            # Extract flight segments
            segments = container.find_elements(By.CSS_SELECTOR, "kilo-flight-block-card-pres")
            print(f"Found {len(segments)} segments in current container.")
            for segment in segments:
                segment_info = {}
                try:
                    segment_info['departure_time'] = segment.find_element(By.CSS_SELECTOR, ".departure-time").text
                    segment_info['arrival_time'] = segment.find_element(By.CSS_SELECTOR, ".arrival-time").text
                    segment_info['duration'] = segment.find_element(By.CSS_SELECTOR, ".flight-summary").text
                    segment_info['route'] = segment.find_element(By.CSS_SELECTOR, ".destination-row").text
                    segment_info['flight_number'] = segment.find_element(By.CSS_SELECTOR, ".operating-airline").text
                    segment_info['cabin'] = segment.find_element(By.CSS_SELECTOR, ".mat-body-2").text
                    segment_info['mixed_cabin_percentage'] = segment.find_element(By.CSS_SELECTOR, ".mixed-cabin-percentage").text if segment.find_elements(By.CSS_SELECTOR, ".mixed-cabin-percentage") else "N/A"
                    segment_info['aircraft'] = segment.find_element(By.CSS_SELECTOR, ".operating-airline-icon").get_attribute("alt")
                    segment_info['connection_time'] = segment.find_element(By.CSS_SELECTOR, ".connection-time").text if segment.find_elements(By.CSS_SELECTOR, ".connection-time") else "N/A"
                    flight_info['segments'].append(segment_info)
                except Exception as e:
                    print(f"Error extracting segment info: {e}")

            # Extract total flight duration and cost
            try:
                flight_info['total_duration'] = container.find_element(By.CSS_SELECTOR, ".total-duration").text
                flight_info['total_cost'] = container.find_element(By.CSS_SELECTOR, ".total-cost").text
            except Exception as e:
                print(f"Error extracting total flight info: {e}")

            flight_details.append(flight_info)

        print(f"Extracted flight details: {flight_details}")

        return flight_details
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Error"
    finally:
        driver.quit()

if __name__ == '__main__':
    app.run(debug=True)
