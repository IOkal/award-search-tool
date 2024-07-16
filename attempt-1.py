from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def search_award_seats(origin, destination, date):
    # Set up the Chrome WebDriver with options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')  # Ignore SSL certificate errors
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open the Air Canada website
        driver.get("https://www.aircanada.com/")
        print("Website loaded.")

        # Accept cookies if the prompt appears
        try:
            accept_cookies_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_cookies_button.click()
            print("Cookies accepted.")
        except Exception as e:
            print("Cookies acceptance prompt did not appear or could not be clicked:", e)

        # Click on "Book with points" to enable the point search
        try:
            book_with_points_checkbox = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "bkmgFlights_searchTypeToggle"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", book_with_points_checkbox)
            driver.execute_script("arguments[0].click();", book_with_points_checkbox)
            print("Book with points selected.")
        except Exception as e:
            print("Book with points checkbox could not be found or clicked:", e)
            driver.quit()
            return

        # Enter origin
        origin_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "origin_R_1"))
        )
        origin_input.clear()
        origin_input.send_keys(origin)
        origin_input.send_keys(Keys.TAB)
        print(f"Origin {origin} entered.")

        # Enter destination
        destination_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "destination_R_1"))
        )
        destination_input.clear()
        destination_input.send_keys(destination)
        destination_input.send_keys(Keys.TAB)
        print(f"Destination {destination} entered.")

        # Enter date
        date_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "departureDate_R_1"))
        )
        date_input.clear()
        date_input.send_keys(date)
        date_input.send_keys(Keys.TAB)
        print(f"Date {date} entered.")

        # Click the search button
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "search-booking-button"))
        )
        search_button.click()
        print("Search initiated.")

        # Wait for search results to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "flight-search-results"))
        )
        print("Search results loaded.")

        # Scrape the search results (example of getting flight details)
        results = driver.find_elements(By.CLASS_NAME, "flight-search-result")
        for result in results:
            flight_info = result.text
            print(flight_info)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the WebDriver
        driver.quit()

# Example usage
search_award_seats("YYZ", "AMM", "2024-08-10")

