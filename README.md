### The GitHub Page

- gh-pages branch is for the git-pages code 
- The main branch has the code for the data work

---
## The Data
**I need to start figuring out documentation. But it's hard jugling all the hats so it will be slow and clunky at first.**

- Where is the data coming from?
- What?
- Why?
- When?

### utah_bills_2025
This script scrape_numbered_bills.py scrapes the [Bills and Resolutions for the 2025 General Session](https://le.utah.gov/billlist.jsp?session=2025GS) website creating a csv and json file with the following info

```commandline
[
  {
    "Category":"House Bills",
    "Bill Number":"HB. 1",
    "Bill Title":"Higher Education Base Budget",
    "Bill Sponsor Raw":"(Rep. Peterson, K.)",
    "Bill Sponsor":"Peterson, K.",
    "Bill Date Raw":"Mon, 20 Jan 2025 15:49 -0700",
    "Bill Date (utc_iso)":"2025-01-20T22:49:00+00:00",
    "Bill URL":"https:\/\/le.utah.gov\/~2025\/bills\/static\/HB0001.html",
    "Scrape Timestamp":"2025-09-19T04:10:12.049183+00:00"
  }, 
  ...
  ]
```


| Key                 | Example Value                                            | Description                                                                                                                                                                                                                            |
|---------------------|----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Category            | House Bills                                              | The website has sections that group the bills. The category is the title of the section.                                                                                                                                               |
| Bill Number         | H.B. 1                                                   | The is the bill number HB for House Bill, SB for Senate Bill and there are a few other prefixes as well                                                                                                                                |
| Bill Title          | Higher Education Base Budget                             | This is the title of the bill                                                                                                                                                                                                          |
| Bill Sponsor Raw    | (Rep. Peterson, K.)                                      | The name is formatted weird on the website with the () so I fix it and add a column this is the og value from the website                                                                                                              |
| Bill Sponsor        | Peterson, K.                                             | This is the cleaned up bill sponsor name                                                                                                                                                                                               |
| Bill Date Raw       | Mon, 20 Jan 2025 15:49 -0700                             | There's a date for each bill. I don't know what it is, the data the bill was numbered, the date it was updated, the data something happened with it. idk i figured i'd grab it with the rest of it. This is the og value from the site |
| Bill Date (utc_iso) | 2025-01-20T22:49:00+00:00                                | This is the date changed into a date format                                                                                                                                                                                            |
| Bill URL            | https:\/\/le.utah.gov\/~2025\/bills\/static\/HB0001.html | The url to the bill text on the state website                                                                                                                                                                                          |
| Scrape Timestamp    | m2025-09-19T03:49:26.120647+00:00                        | This is the date and time the data was gathered                                                                                                                                                                                        |



