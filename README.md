# CS50 Finance++
[CS50 Finance](https://cs50.harvard.edu/x/2021/psets/9/finance/) is one of the last assignments of CS50x, the online introductory computer science course from Harvard. It is a virtual stock trading app, written in Python and Flask. I finished the original assignment, but then started playing around with it and added some extra features for fun and learning :)

You can view the [live demo here](https://cs50-finance-plus.fly.dev/) (it may take a few seconds to load!)

### Added User Features:
- Users can view additional data in the home page: day change, cost basis, and gain/loss info for each stock as well as for the portfolio as a whole
- Users can deposit more cash, so they can trade like a billionaire 🤑🤑
- Added a running cash balance to the History page
- Green and red colors to highlight positive/negative amounts
- Users can change their password, as well as delete their profile and data

### Code/nerdy improvements
- Replaced raw SQL and SQLite in the original assignment with SQLAlchemy ORM and Postgres DB for database reads and writes, with models under `application/models.py`
- Created a clearer project structure and followed Flask recommendations, by splitting up route controllers into different files under `application/routes`, and creating a dedicated `config.py` file for Flask's config variables