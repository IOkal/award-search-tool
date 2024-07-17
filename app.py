from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def extract_flight_details(container):
    flight_details = {
        'segments': [],
        'connections': [],
        'prices': {'eco': None, 'ecoPremium': None, 'business': None},
        'mixed_cabin_percentages': {'eco': None, 'ecoPremium': None, 'business': None}
    }

    try:
        # Ensure container is not None
        if container is None:
            raise ValueError("Container is None")

        # Parse the container using BeautifulSoup
        soup = BeautifulSoup(str(container), 'html.parser')
        
        # Extract the flight description to find segments and connections
        # flight_description = soup.select_one(".cdk-visually-hidden").text
        # print(f"Flight description: {flight_description}")
        
        # # Extract segments
        # segment_matches = re.findall(r"SEG-(\w+)-(\w+)-(\d{4}-\d{2}-\d{2}-\d{4})", flight_description)
        # print(f"Segment matches: {segment_matches}")

        # Find all instances of class "available-cabin"
        available_cabins = soup.find_all(class_="available-cabin")
        # print("available_cabins")
        # print(available_cabins)
        # print(available_cabins[0])
        # for cabin in available_cabins:

        for match in segment_matches:
            flight_number, route, flight_time = match
            departure, arrival = route.split('-')
            segment_info = {
                'flight_number': flight_number,
                'route': route,
                'departure_time': flight_time,
                'departure': departure,
                'arrival': arrival
            }
            flight_details['segments'].append(segment_info)
        
        # Extract layover information
        layover_matches = re.findall(r"Layover of (\d+h\d+m) in (\w+)", flight_description)
        print(f"Layover matches: {layover_matches}")
        
        for match in layover_matches:
            layover_time, layover_airport = match
            flight_details['connections'].append({
                'layover_time': layover_time,
                'layover_airport': layover_airport
            })
        
        # Extract departure and arrival times
        departure_time = soup.select_one('span.mat-h3.time.departure-time').text
        arrival_time = soup.select_one('span.mat-h3.time.arrival-time').text
        flight_details['departure_time'] = departure_time
        flight_details['arrival_time'] = arrival_time
        print(f"Departure Time: {departure_time}")
        print(f"Arrival Time: {arrival_time}")

        # Extract price and mixed cabin information
        cabin_classes = ['eco', 'ecoPremium', 'business']
        for cabin in cabin_classes:
            try:
                cabin_container = soup.select_one(f".available-cabin.flight-cabin-cell.{cabin}")
                if cabin_container:
                    price_points = cabin_container.select_one(".points-total").text
                    price_cash = cabin_container.select_one("kilo-price").text
                    mixed_cabin_percentage = cabin_container.select_one(".mixed-cabin-percentage").text if cabin_container.select_one(".mixed-cabin-percentage") else "100%"
                
                    flight_details['prices'][cabin] = f"{price_points} + {price_cash}"
                    flight_details['mixed_cabin_percentages'][cabin] = mixed_cabin_percentage
                else:
                    print(f"{cabin.capitalize()} class container not found.")
            except Exception as e:
                print(f"{cabin.capitalize()} class not available: {e}")

    except Exception as e:
        print(f"Error extracting flight details: {e}")

    return flight_details

def search_flight_live(origin, destination, date):
    url = f"https://www.aircanada.com/aeroplan/redeem/availability/outbound?org0={origin}&dest0={destination}&departureDate0={date}&ADT=1&YTH=0&CHD=0&INF=0&INS=0&lang=en-CA&tripType=O&marketCode=INT"
    
    options = webdriver.ChromeOptions()
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
        flight_details_list = []

        # Locate the main container for flight details
        flight_containers = driver.find_elements(By.CSS_SELECTOR, "kilo-upsell-row-cont")
        print(f"Found {len(flight_containers)} flight containers.")

        for index, container in enumerate(flight_containers):
            print(f"Inspecting container {index+1}/{len(flight_containers)}")
            flight_details = extract_flight_details(container)
            flight_details_list.append(flight_details)
            print(f"Flight details for container {index+1}: {flight_details}")

        print(f"Extracted flight details: {flight_details_list}")

        return flight_details_list
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Error"
    finally:
        driver.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    origin = request.form['origin']
    destination = request.form['destination']
    date = request.form['date']
    
    results = search_flight_live(origin, destination, date)
    
    if results == "Error":
        return jsonify({"error": "An error occurred while searching for flights."}), 500
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
