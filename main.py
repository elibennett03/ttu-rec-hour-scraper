import requests
from bs4 import BeautifulSoup
import json
import datetime


def scrape():
    url = "https://www.tntech.edu/recreation/hours.php"
    
    try:
        # Make a GET request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract data
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule = {
            "Building Hours": {},
            "Climbing Wall Hours": {},
            "Pool and Sauna Hours": {}
        }
        
        rows = soup.find_all('tr')
        day_index = 0
        for row in rows:
            columns = row.find_all('td')
            if len(columns) == 0:
                continue
            
            # Extract and clean data
            if columns[0].text.strip() in days:
                current_day = columns[0].text.strip()
                schedule["Building Hours"][current_day] = columns[1].text.strip()
                schedule["Climbing Wall Hours"][current_day] = columns[2].text.strip()
                schedule["Pool and Sauna Hours"][current_day] = columns[3].text.strip()
            else:
                day_index += 1
                
        #Loop through <p> elements to find when times where last updated
        targetText = 'Updated'
        for p in soup.find_all('p'):
            if targetText in p.text:
                schedule["Updated Time"] = p.text.strip()
                break
            
        #datetime to  confirm correctly timed and pushed json
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        schedule["Current Time"] = current_time
        
                
        # Convert to JSON and save to a file
        with open('schedule.json', 'w') as json_file:
            json.dump(schedule, json_file, indent=4)
        
        print("Scraping and JSON conversion completed.")
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    

if __name__ == "__main__":
    scrape()
