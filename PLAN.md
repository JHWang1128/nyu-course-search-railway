this repository implements NYU course search based on course name and description.

all courses at NYU are available at https://bulletins.nyu.edu/courses/. the first step is to scrape all courses and store them in a database.

each course must be embedded in an euclidean space using nomic embedding from huggingface mobdel hub. this allows us to perform vector similarity search based on the semantics. this search must be implemented using a web UI.

unfortunately, this course listing has only the course code, name and description. in order to get the detail, we must use the course search tool (beta) at https://bulletins.nyu.edu/class-search/. this course search tool returns more details about the course. instead of scraping this page, we should be able to use this search page (everything is passed as query parameters) and display details in the web UI. some course do not open in all semesters, and we should try all semesters within the same year to get the details. if the course is not found, we should try going back in time one semester at a time.

the whole thing should be doable from the web UI. the web UI must be professional and modern. furthermore, this web UI should support multiple users, as we want the users to save the courses they searched for so that they can plan out their future courses. for each retrieved course, we need to also have a thumb-up feature, so that we track the relevance of each course to the query. this will help us evaluate the quality of the search results. 

because we may want to deploy this app to railway, we should probably use postgre database and redis for caching. we also need to use a web framework that is easy to deploy to railway and easy to debug and maintain. for users, we should only allow those with @nyu.edu email addresses to use this app.