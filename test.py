import re

def convert_to_24h(time_str):
    """
    Converts a time string from 12-hour format to 24-hour format.
    
    Args:
        time_str (str): The time string in 12-hour format (e.g., '6:00 PM').
        
    Returns:
        int: The time as an integer in 24-hour format (e.g., 1800 for 6:00 PM).
    """
    # Normalize the time string
    time_str = re.sub(r'\s+', ' ', time_str).strip()
    time_str = re.sub(r'\.\s*', '.', time_str)
    
    # Match the time string with a regular expression
    match = re.match(r'(\d{1,2}):?(\d{2})?\s*([AaPp]\.?[Mm]\.?)', time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    period = match.group(3).replace('.', '').upper()

    # Convert to 24-hour format
    if period == 'AM':
        if hour == 12:
            hour = 0  # Midnight case
    elif period == 'PM':
        if hour != 12:
            hour += 12  # PM case (1 PM to 11 PM)

    return hour * 100 + minute

# Example usage
time_12h = "8:00 PM"
time_24h = convert_to_24h(time_12h)
print(f"Converted time: {time_24h}")
