import requests
from bs4 import BeautifulSoup
import json
import datetime
import re  # Make sure to import the re module

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
                schedule["Building Hours"][current_day] = format_hours(columns[1].text.strip())
                schedule["Climbing Wall Hours"][current_day] = format_hours(columns[2].text.strip())
                schedule["Pool and Sauna Hours"][current_day] = format_hours(columns[3].text.strip())
            else:
                day_index += 1

        # Loop through <p> elements to find when times were last updated
        targetText = 'Updated'
        for p in soup.find_all('p'):
            if targetText in p.text:
                schedule["Updated Time"] = p.text.strip()
                break

        # datetime to confirm correctly timed and pushed json
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
        # Make a GET request to the URL
        response = requests.get(group_url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        classes = []  # Initialize an empty list to hold class information
        class_names = ["HIIT", "Pilates", "Spin", "Power Lunch", "Water Aerobics"]  # List of class names to search for

        # Find the specified <div> and get all content within it
        container = soup.find('div', class_='grid-container twoThirdsContainer')
        if container:
            headings = container.find_all('h4')  # Find all <h4> tags within the container

            for h4 in headings:
                strong_tag = h4.find('strong')  # Find the <strong> tag within each <h4>
                if strong_tag:
                    class_name = strong_tag.text.replace('›', '').strip()
                    # Extract and clean the class name
                    if class_name in class_names:
                        
                        p_tag = h4.find_next_sibling('p')
                        if p_tag:
                            # Extract and clean the data
                            strong_tags = p_tag.find_all('strong')
                            print(strong_tags)  # Debugging output to see the structure

                            if len(strong_tags) >= 3:
                                time_and_day = strong_tags[0].get_text().strip() 
                                instructor = strong_tags[1].get_text().strip().replace('Instructor: ', '')  # Extract and clean instructor
                                location = strong_tags[2].get_text().strip().replace('Location: ', '')  # Extract and clean location
                            elif len(strong_tags) == 1:
                                full_details = strong_tags[0].get_text().strip()
                                time_and_day, instructor, location = None, None, None

                                if 'Instructor:' in full_details and 'Location:' in full_details:
                                    time_and_day, instructor_part = full_details.split('Instructor:', 1)
                                    instructor, location_part = instructor_part.split('Location:', 1)
                                    location = location_part.split('<br/>')[0].strip()

                                    time_and_day = time_and_day.strip()
                                    instructor = instructor.strip()
                                    location = location.strip()
                            else:
                                continue

                            # Handle descriptions
                            description = ""
                            for sibling in p_tag.stripped_strings:
                                if sibling not in time_and_day and sibling not in instructor and sibling not in location:
                                    description += f"{sibling} "

                            description = ' '.join(description.split())  # Clean up the description by replacing multiple spaces with a single space

                            # Clean all fields from redundant information
                            time_and_day = clean_field(time_and_day)
                            instructor = clean_field(instructor)
                            location = clean_field(location)
                            description = clean_description(description, time_and_day, instructor, location)

                            # Split time_and_day into separate day and time
                            if ',' in time_and_day:
                                day, time = time_and_day.split(',', 1)  # Split day and time
                                day = day.strip()
                                time = time.strip()
                            else:
                                day = time_and_day
                                time = ""

                            # Create a dictionary for the class information
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

        # Convert the schedule dictionary to JSON and save it to a file
        with open('group_classes.json', 'w') as json_file:
            json.dump(schedule, json_file, indent=4)

        print("Scraping and JSON conversion completed.")

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")  # Print the request error if it occurs
    except Exception as e:
        print(f"An error occurred: {e}")

def clean_field(field):
    if field:
        field = field.replace('\u2014', '').strip()
    return field

def clean_description(description, time_and_day, instructor, location):
    if time_and_day:
        description = description.replace(time_and_day, '').strip()
    if instructor:
        description = description.replace(f"Instructor: {instructor}", '').strip()
    if location:
        description = description.replace(f"Location: {location}", '').strip()
    # Remove any leading or trailing special characters like em dash (\u2014)
    description = description.replace('\u2014', '').strip()
    return description

def format_hours(hours):
    # Handle 'CLOSED' directly
    if hours.upper() == "CLOSED":
        return hours

    # Normalize multiple time ranges separated by '/'
    time_ranges = hours.split('/')
    normalized_ranges = []

    for time_range in time_ranges:
        times = time_range.split('-')
        start_time = normalize_time(times[0].strip())
        end_time = normalize_time(times[1].strip())
        normalized_ranges.append(f"{start_time} - {end_time}")

    return ' / '.join(normalized_ranges)

def normalize_time(time):
    # Remove any extra spaces and periods
    time = re.sub(r'\s+', ' ', time).strip()
    time = re.sub(r'\.\s*', '.', time)

    time_pattern = re.compile(r'(\d+)\s*([AaPp]\.?[Mm]\.?)')
    match = time_pattern.search(time)
    if match:
        hour = match.group(1)
        period = match.group(2).replace('.', '').upper()
        return f'{hour}:00 {period}'
    else:
        raise ValueError(f"Error normalizing time: {time}")

if __name__ == "__main__":
    scrape()
    scrape_classes()
