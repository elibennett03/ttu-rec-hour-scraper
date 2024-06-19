import requests
from bs4 import BeautifulSoup
import json
import datetime


def scrape():
    hour_url = "https://www.tntech.edu/recreation/hours.php"
    group_url = 'https://www.tntech.edu/recreation/group-classes.php'
    
    
    try:
        # Make a GET request
        response = requests.get(hour_url)
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
        
def scrape_classes():
    group_url = 'https://www.tntech.edu/recreation/group-classes.php'
    
    try:
        # Make a GET request
        response = requests.get(group_url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        classes = []
        class_names = ["HIIT", "Pilates", "Spin", "Power Lunch", "Water Aerobics"]
        
        # Find the specified <div> and get all content within it
        container = soup.find('div', class_='grid-container twoThirdsContainer')
        if container:
            headings = container.find_all('h4')
            
            for h4 in headings:
                strong_tag = h4.find('strong')
                if strong_tag:
                    class_name = strong_tag.text.replace('›', '').strip()
                    if class_name in class_names:
                        p_tag = h4.find_next_sibling('p')
                        if p_tag:
                            # Extract and clean the data
                            strong_tags = p_tag.find_all('strong')
                            if len(strong_tags) >= 3:
                                time_and_day = strong_tags[0].get_text().strip()
                                instructor = strong_tags[1].get_text().strip().replace('Instructor: ', '')
                                location = strong_tags[2].get_text().strip().replace('Location: ', '')

                                # Get the description as everything that comes after the last <strong> tag
                                last_strong_tag = strong_tags[-1]
                                description = ""
                                for sibling in last_strong_tag.next_siblings:
                                    if sibling.name is None:  # Text node
                                        description += sibling.strip()
                                    else:
                                        description += sibling.get_text(strip=True)
                                
                                description = ' '.join(description.split())

                                # Split time_and_day into separate day and time
                                if ',' in time_and_day:
                                    day, time = time_and_day.split(',', 1)
                                    day = day.strip()
                                    time = time.strip()
                                else:
                                    day = time_and_day
                                    time = ""

                                class_info = {
                                    'Class Name': class_name,
                                    'Day': day,
                                    'Time': time,
                                    'Instructor': instructor,
                                    'Location': location,
                                    'Description': description
                                }
                                classes.append(class_info)
        
        # Get the current time for confirmation
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a schedule dictionary
        schedule = {
            'Classes': classes,
            'Current Time': current_time
        }
        
        # Convert to JSON and save to a file
        with open('group_classes.json', 'w') as json_file:
            json.dump(schedule, json_file, indent=4)
        
        print("Scraping and JSON conversion completed.")
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    scrape()
    scrape_classes()
