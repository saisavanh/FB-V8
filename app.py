import requests
from bs4 import BeautifulSoup

URL = "https://goal7.co/wp-admin/admin-ajax.php"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": "_ga=GA1.1.1678684984.1773394526; cf_clearance=I8PJe_o89gNJDcmCzlrHLqCrrNPsEPa1yfy648QLg_E-1776959614-1.2.1.1-pi2NS7o6EfGdCKYk3wImoROWmlM8d7lMjdH1gqn0U2aGOnDBrBM7dsad78uGTXPf5CoWvZEDFaWQBLyVwreD5o3013jQ9waJ02eFGAKJFfmD3W1v5ZKB4j8ef7KWbIYILvu0dTRH_jpcWfeK2m2KKqmPCAUWaB1gQy5dmSGUauHSlL6D.cgG6NAXuULKBFqFW9Eit.fTzBYaFnrWhGx1LdUAck8x4OwZA7LAatmZ1hGk5Q9f6sZntcmLC9C6xnEHvwJQr9JIQ.uXFREhUoSBiPjpONXzZHnuwOJNcJnqxPUufdNunZxIFm7ujsjR90fwt6x5lxcm_jQIz3CmqOBxdg; PHPSESSID=48a20665379584235bc2d8f8197678fc"
}

data = {
    "action": "load_matches",
    "date": "2026-04-25"
}

res = requests.post(URL, headers=headers, data=data)

soup = BeautifulSoup(res.text, "html.parser")

matches = []

for row in soup.select("tr"):
    cols = row.find_all("td")
    if len(cols) > 5:
        try:
            team = cols[1].text.strip()
            price = cols[2].text.strip()
            odds = cols[3].text.strip()

            matches.append({
                "team": team,
                "price": price,
                "odds": odds
            })
        except:
            pass

print(matches)
