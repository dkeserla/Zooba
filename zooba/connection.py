import requests
import bs4 as bs

#function that connects to Home Access Center and gets a beautiful soup representation of the page
def connect(user_name, pass_word):
    header = {
        'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36'
    }   

    #login data for the post request to pass and get data to parse
    login_data = {
        '__RequestVerificationToken' : "",
        'SCKTY00328510CustomEnabled' : 'False',
        'SCKTY00436568CustomEnabled' : 'False',
        'Database' : '10',
        'VerificationOption': 'UsernamePassword',
        'tempUN': "",
        'tempPW': "",
        'LogOnDetails.UserName' : user_name,
        'LogOnDetails.Password' : pass_word
    }

    #makes a session from the requests library to get the specific page
    with requests.Session() as c:
        url = 'https://lis-hac.eschoolplus.powerschool.com/HomeAccess/Account/LogOn?ReturnUrl=%2fHomeAccess%2f'
        p = c.get(url)
        login_data['__RequestVerificationToken'] = request_token(p)
        c.post(url, data = login_data, headers = header)
        assignments_page = c.get('https://lis-hac.eschoolplus.powerschool.com/HomeAccess/Content/Student/Assignments.aspx')
        return assignments_page

#gets the request token to be able to pass the post request to the page
def request_token(page):
    p = bs.BeautifulSoup(page.content, 'html5lib')
    return p.find_all(attrs={'name': '__RequestVerificationToken'})[0]['value']