import datetime
import json
import logging
import re

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rec_scraper')

# Constants
HOURS_URL = "https://www.tntech.edu/recreation/hours.php"
CLASSES_URL = "https://www.tntech.edu/recreation/group-classes.php"
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CLASS_NAMES = ["HIIT", "Pilates", "Spin", "Power Lunch", "Water Aerobics", "Dance Aerobics"]

class TimeConverter:
    @staticmethod
    def convert_to_24h(time_str):
        """
        Converts a time string from 12-hour format to 24-hour format.
        
        Args:
            time_str (str): The time string in 12-hour format (e.g., '6:00 PM', '6 PM').
            
        Returns:
            int: The time as an integer in 24-hour format (e.g., 1800 for 6:00 PM).
        """
        # Normalize the time string
        time_str = re.sub(r'[^\w\s:APMapm-]', '', time_str)  # Remove unexpected characters
        time_str = re.sub(r'\s+', ' ', time_str).strip()
        
        # Match the time string with a regular expression
        match = re.match(r'(?i)(\d{1,2}):?(\d{2})?\s*([APM]+)', time_str)
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")

        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3).upper()

        # Convert to 24-hour format
        if period == 'AM':
            if hour == 12:
                hour = 0  # Midnight case
        elif period == 'PM':
            if hour != 12:
                hour += 12  # PM case (1 PM to 11 PM)

        return hour * 100 + minute

    @staticmethod
    def format_hours_to_int(hours):
        """
        Formats hours from 12-hour format to 24-hour format integers.
        
        Args:
            hours (str): The hours string in 12-hour format.
            
        Returns:
            list: A list of time ranges with times converted to 24-hour format.
        """
        # Handle 'CLOSED' directly
        if hours.upper() == "CLOSED":
            return []

        # Ensure proper spacing if times are concatenated (e.g., "6 AM - 11 AM3 PM - 9 PM")
        hours = re.sub(r'(?<=[APM])(?=\d)', ' ', hours)
        
        # Normalize multiple time ranges separated by '/' or newlines
        time_ranges = re.split(r'[\n/]+', hours)
        normalized_ranges = []

        for time_range in time_ranges:
            # Ensure valid format before splitting
            times = re.findall(r'\d{1,2} (?:AM|PM) - \d{1,2} (?:AM|PM)', time_range)
            
            for time in times:
                try:
                    start, end = time.split('-')
                    start_time = TimeConverter.convert_to_24h(start.strip())
                    end_time = TimeConverter.convert_to_24h(end.strip())
                    normalized_ranges.append(f"{start_time:04d} - {end_time:04d}")
                except ValueError:
                    logger.warning(f"Skipping invalid time range: {time}")
                    continue

        return normalized_ranges

class RecreationScraper:
    def __init__(self):
        self.time_converter = TimeConverter()
    
    def _save_to_json(self, data, filename):
        """Save data dictionary to a JSON file"""
        try:
            with open(filename, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            logger.info(f"Successfully saved data to {filename}")
        except Exception as e:
            logger.error(f"Failed to save JSON file {filename}: {e}")
    
    def _make_request(self, url):
        """Make HTTP request and return BeautifulSoup object"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def _get_current_timestamp(self):
        """Return current timestamp in the standard format"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def scrape_hours(self):
        """Scrape recreation center hours and save to JSON file"""
        soup = self._make_request(HOURS_URL)
        if not soup:
            return False
        
        schedule = {
            "Building Hours": {},
            "Climbing Wall Hours": {},
            "Pool and Sauna Hours": {}
        }

        try:
            # Find and process the schedule table
            rows = soup.find_all('tr')
            for row in rows:
                columns = row.find_all('td')
                if len(columns) == 0:
                    continue

                # Extract and clean data
                if columns[0].text.strip() in DAYS_OF_WEEK:
                    current_day = columns[0].text.strip()
                    
                    def process_time_column(column_text):
                        times = [time.strip() for time in column_text.split('\n') if time.strip()]
                        formatted_times = []
                        for time in times:
                            try:
                                formatted_times.append(TimeConverter.format_hours_to_int(time))
                            except ValueError:
                                logger.warning(f"Unexpected time range format: {time}")
                                continue
                        return formatted_times  # Store as a list
                    
                    schedule["Building Hours"][current_day] = process_time_column(columns[1].text)
                    schedule["Climbing Wall Hours"][current_day] = process_time_column(columns[2].text)
                    schedule["Pool and Sauna Hours"][current_day] = process_time_column(columns[3].text)

            # Find update time information
            for p in soup.find_all('p'):
                if 'Updated' in p.text:
                    schedule["Updated Time"] = p.text.strip()
                    break

            # Add current timestamp
            schedule["Current Time"] = self._get_current_timestamp()
            
            # Save results to JSON
            self._save_to_json(schedule, 'schedule.json')
            return True
            
        except Exception as e:
            logger.error(f"Error scraping hours: {e}")
            return False

    
    def _clean_text(self, text):
        """Clean text by removing special characters and extra spaces"""
        if text:
            text = text.replace('\u2014', '').strip()
        return text
    
    def _extract_class_details(self, p_tag):
        """Extract class details from paragraph tag"""
        strong_tags = p_tag.find_all('strong')

        time_and_day = strong_tags[0].get_text(strip=True) if len(strong_tags) >= 1 else ""
        instructor = strong_tags[1].get_text(strip=True).replace('Instructor: ', '').strip() if len(strong_tags) >= 2 else ""
        location = strong_tags[2].get_text(strip=True).replace('Location: ', '').strip() if len(strong_tags) >= 3 else ""
        
        # Ensure time is correctly separated from instructor and location
        if "Instructor:" in time_and_day:
            time_and_day, instructor = time_and_day.split("Instructor:", 1)
            instructor = instructor.strip()
        if "Location:" in instructor:
            instructor, location = instructor.split("Location:", 1)
            location = location.strip()
        
        # Remove any lingering dashes or unwanted characters
        time_and_day = re.sub(r'\s*\u2014\s*', '', time_and_day).strip()
        instructor = re.sub(r'\s*\u2014\s*', '', instructor).strip()
        location = re.sub(r'\s*\u2014\s*', '', location).strip()
        
        # Extract description (remaining text in <p>)
        description = p_tag.get_text(" ", strip=True)
        description = description.replace(time_and_day, '').replace(instructor, '').replace(location, '').strip()
        description = description.replace("Instructor:", '').replace("Location:", '').strip()
        description = re.sub(r'\s*\u2014\s*', '', description).strip()
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Split time_and_day into separate day and time
        if "," in time_and_day:
            day, time = map(str.strip, time_and_day.split(",", 1))
        else:
            day, time = time_and_day, ""

        return {
            'Day': day,
            'Time': time,
            'Instructor': instructor,
            'Location': location,
            'Description': description
        }


    def scrape_classes(self):
        """Scrape group fitness classes dynamically from structured HTML and save to JSON file."""
        soup = self._make_request(CLASSES_URL)
        if not soup:
            return False

        classes = []
        try:
            # Locate the correct container by finding the one that contains <h4> tags
            correct_container = None
            for container in soup.find_all('div', class_='eagleContent'):
                if container.find('h4'):
                    correct_container = container
                    break

            if not correct_container:
                logger.warning("Could not find the correct container for group classes")
                return False

            # Find all class headings (h4)
            for h4 in correct_container.find_all('h4'):
                strong_tag = h4.find('strong')
                if not strong_tag:
                    continue

                # Extract class name and clean it
                class_name = strong_tag.text.replace('›', '').strip()
                
                # Find the next <p> tag containing details
                p_tag = h4.find_next_sibling('p')
                if not p_tag:
                    continue

                # Extract class details using the helper function
                class_details = self._extract_class_details(p_tag)
                class_details['Class Name'] = class_name  # Add class name to the extracted details

                classes.append(class_details)

            # Save to JSON
            schedule = {
                'Classes': classes,
                'Current Time': self._get_current_timestamp()
            }
            self._save_to_json(schedule, 'group_classes.json')
            return True

        except Exception as e:
            logger.error(f"Error scraping classes: {e}")
            return False








def main():
    """Main function to run the scraper"""
    scraper = RecreationScraper()
    
    logger.info("Starting to scrape recreation center hours...")
    if scraper.scrape_hours():
        logger.info("Successfully scraped recreation center hours")
    else:
        logger.error("Failed to scrape recreation center hours")
    
    logger.info("Starting to scrape group fitness classes...")
    if scraper.scrape_classes():
        logger.info("Successfully scraped group fitness classes")
    else:
        logger.error("Failed to scrape group fitness classes")


if __name__ == "__main__":
    main()
