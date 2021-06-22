from velogames.scrapper import scrap, CSV

def main():
    if not CSV.exists():
        scrap()
