# Token authentication

Users must be able to log into our application, and when a user is logged in, their user information must automatically be attached to any new notes they create.

We will now implement support for [token-based authentication](https://www.digitalocean.com/community/tutorials/the-ins-and-outs-of-token-based-authentication#how-token-based-works) to the backend.

The principles of token-based authentication are depicted in the following sequence diagram:

![Sequence diagram illustrating the token-based authentication flow. The diagram shows the interaction between four entities: Browser (React application), Server (Node.js), and Database. The flow begins with the user entering login credentials in the browser, which sends a POST request with username and password to the server's /api/login endpoint. The server queries the database to find the user, and the database returns the user record. The server then validates the password hash using bcrypt. Upon successful validation, the server generates a JWT token signed with a secret key and returns it to the browser. For subsequent authenticated requests (like creating a new note), the browser includes the token in the Authorization header using the Bearer scheme. The server verifies the token signature, extracts the user ID, and if valid, proceeds to process the request and interact with the database accordingly. The diagram uses arrows to show the direction of data flow and labels each step with descriptive text.](/static/259c9dce6b3d1d77bedb04e799ac7dd3/5a190/16new.png)

- User starts by logging in using a login form implemented with React
  - We will add the login form to the frontend in [part 5](/en/part5)
- This causes the React code to send the username and the password to the server address _/api/login_ as an HTTP POST request.
- If the username and the password are correct, the server generates a _token_ that somehow identifies the logged-in user.
  - The token is signed digitally, making it impossible to falsify (with cryptographic means)
- The backend responds with a status code indicating the operation was successful and returns the token with the response.
- The browser saves the token, for example to the state of a React application.
- When the user creates a new note (or does some other operation requiring identification), the React code sends the token to the server with the request.
- The server uses the token to identify the user

Let's first implement the functionality for logging in. Install the [jsonwebtoken](https://github.com/auth0/node-jsonwebtoken) library, which allows us to generate [JSON web tokens](https://jwt.io/).

```bash
npm install jsonwebtoken
```

The code for login functionality goes to the file _controllers/login.js_.

```js
const jwt = require('jsonwebtoken')
const bcrypt = require('bcrypt')
const loginRouter = require('express').Router()
const User = require('../models/user')

loginRouter.post('/', async (request, response) => {
  const { username, password } = request.body

  const user = await User.findOne({ username })
  const passwordCorrect = user === null
    ? false
    : await bcrypt.compare(password, user.passwordHash)

  if (!(user && passwordCorrect)) {
    return response.status(401).json({
      error: 'invalid username or password'
    })
  }

  const userForToken = {
    username: user.username,
    id: user._id,
  }

  const token = jwt.sign(userForToken, process.env.SECRET)

  response
    .status(200)
    .send({ token, username: user.username, name: user.name })
})

module.exports = loginRouter
```

The code starts by searching for the user from the database by the _username_ attached to the request.

```js
const user = await User.findOne({ username })
```

Next, it checks the _password_, also attached to the request.

```js
const passwordCorrect = user === null
  ? false
  : await bcrypt.compare(password, user.passwordHash)
```

Because the passwords themselves are not saved to the database, but _hashes_ calculated from the passwords, the *bcrypt.compare* method is used to check if the password is correct:

```js
await bcrypt.compare(password, user.passwordHash)
```

If the user is not found, or the password is incorrect, the request is responded with the status code [401 unauthorized](https://www.rfc-editor.org/rfc/rfc9110.html#name-401-unauthorized). The reason for the failure is explained in the response body.

```js
if (!(user && passwordCorrect)) {
  return response.status(401).json({
    error: 'invalid username or password'
  })
}
```

If the password is correct, a token is created with the method *jwt.sign*. The token contains the username and the user id in a digitally signed form.

```js
const userForToken = {
  username: user.username,
  id: user._id,
}

const token = jwt.sign(userForToken, process.env.SECRET)
```

The token has been digitally signed using a string from the environment variable _SECRET_ as the _secret_.
The digital signature ensures that only parties who know the secret can generate a valid token.
The value for the environment variable must be set in the _.env_ file.

A successful request is responded to with the status code _200 OK_. The generated token and the username of the user are sent back in the response body.

```js
response
  .status(200)
  .send({ token, username: user.username, name: user.name })
```

Now the code for login just has to be added to the application by adding the new router to _app.js_.

```js
const loginRouter = require('./controllers/login')

//...

app.use('/api/login', loginRouter)
```

Let's try logging in using VS Code REST-client:

![VS Code REST client extension showing a POST request to the login endpoint. The request is being sent to http://localhost:3001/api/login with a JSON body containing username and password fields. The request is formatted in the REST client syntax with POST followed by the URL, Content-Type header set to application/json, and a JSON object in the request body with username and password key-value pairs. This demonstrates how developers can test their login API directly within the VS Code editor using the REST client extension.](/static/5c4c0fb60e15ec9c753e541a05002c3f/5a190/17e.png)

It does not work. The following is printed to the console:

```bash
(node:32911) UnhandledPromiseRejectionWarning: Error: secretOrPrivateKey must have a value
    at Object.module.exports [as sign] (/Users/mluukkai/opetus/_2019fullstack-koodit/osa3/notes-backend/node_modules/jsonwebtoken/sign.js:101:20)
    at loginRouter.post (/Users/mluukkai/opetus/_2019fullstack-koodit/osa3/notes-backend/controllers/login.js:26:21)
(node:32911) UnhandledPromiseRejectionWarning: Unhandled promise rejection. This error originated either by throwing inside of an async function without a catch block, or by rejecting a promise which was not handled with .catch(). (rejection id: 2)
```

The command *jwt.sign(userForToken, process.env.SECRET)* fails. We forgot to set a value to the environment variable _SECRET_. It can be any string. When we set the value in file _.env_ (and restart the server), the login works.

A successful login returns the user details and the token:

![VS Code REST client showing a successful login response. The response has a 200 OK status code and contains a JSON body with three fields: a token (a long JWT string starting with eyJhbGciOiJIUzI1NiIs...), the username of the authenticated user, and the name of the user. This demonstrates what a successful authentication response looks like, where the server returns the JWT token that the client will use for subsequent authenticated requests along with basic user information for display purposes.](/static/2e2ddac76483e17fded8f6fcc43fd7d4/5a190/18ea.png)

A wrong username or password returns an error message and the proper status code:

![VS Code REST client showing a failed login attempt response. The response has a 401 Unauthorized status code and contains a JSON body with an error field that has the message "invalid username or password". This demonstrates the server's proper error handling when authentication fails, returning both the appropriate HTTP status code (401) and a descriptive error message to inform the client why the login attempt was rejected.](/static/49fe09c494b9e591fa8811b1772404d5/5a190/19ea.png)

## Limiting creating new notes to logged-in users

Let's change creating new notes so that it is only possible if the post request has a valid token attached. The note is then saved to the notes list of the user identified by the token.

There are several ways of sending the token from the browser to the server. We will use the [Authorization](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization) header. The header also tells which [authentication scheme](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#Authentication_schemes) is used. This can be necessary if the server offers multiple ways to authenticate.
Identifying the scheme tells the server how the attached credentials should be interpreted.

The _Bearer_ scheme is suitable for our needs.

In practice, this means that if the token is, for example, the string _eyJhbGciOiJIUzI1NiIsInR5c2VybmFtZSI6Im1sdXVra2FpIiwiaW_, the Authorization header will have the value:

```text
Bearer eyJhbGciOiJIUzI1NiIsInR5c2VybmFtZSI6Im1sdXVra2FpIiwiaW
```

Creating new notes will change like so (_controllers/notes.js_):

```js
const jwt = require('jsonwebtoken')
// ...
const getTokenFrom = request => {
  const authorization = request.get('authorization')
  if (authorization && authorization.startsWith('Bearer ')) {
    return authorization.replace('Bearer ', '')
  }
  return null
}
notesRouter.post('/', async (request, response) => {
  const body = request.body
  const decodedToken = jwt.verify(getTokenFrom(request), process.env.SECRET)
  if (!decodedToken.id) {
    return response.status(401).json({ error: 'token invalid' })
  }

  const user = await User.findById(decodedToken.id)
  if (!user) {
    return response.status(400).json({ error: 'UserId missing or not valid' })
  }

  const note = new Note({
    content: body.content,
    important: body.important || false,
    user: user._id
  })

  const savedNote = await note.save()
  user.notes = user.notes.concat(savedNote._id)
  await user.save()

  response.status(201).json(savedNote)
})
```

The helper function *getTokenFrom* isolates the token from the _authorization_ header. The validity of the token is checked with *jwt.verify*. The method also decodes the token, or returns the Object which the token was based on.

```js
const decodedToken = jwt.verify(token, process.env.SECRET)
```

If the token is missing or it is invalid, the exception _JsonWebTokenError_ is raised. We need to extend the error handling middleware to take care of this particular case:

```js
const errorHandler = (error, request, response, next) => {
  if (error.name === 'CastError') {
    return response.status(400).send({ error: 'malformatted id' })
  } else if (error.name === 'ValidationError') {
    return response.status(400).json({ error: error.message })
  } else if (error.name === 'MongoServerError' && error.message.includes('E11000 duplicate key error')) {
    return response.status(400).json({ error: 'expected `username` to be unique' })
  } else if (error.name ===  'JsonWebTokenError') {
    return response.status(401).json({ error: 'token invalid' })
  }

  next(error)
}
```

The object decoded from the token contains the _username_ and _id_ fields, which tell the server who made the request.

If the object decoded from the token does not contain the user's identity (*decodedToken.id* is undefined), error status code [401 unauthorized](https://www.rfc-editor.org/rfc/rfc9110.html#name-401-unauthorized) is returned and the reason for the failure is explained in the response body.

```js
if (!decodedToken.id) {
  return response.status(401).json({
    error: 'token invalid'
  })
}
```

When the identity of the maker of the request is resolved, the execution continues as before.

A new note can now be created using Postman if the _authorization_ header is given the correct value, the string _Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ_, where the second value is the token returned by the _login_ operation.

Using Postman this looks as follows:

![Postman application interface showing a POST request to create a new note. The request is being sent to the /api/notes endpoint. In the Headers tab, the Authorization header is visible with the value "Bearer" followed by a JWT token string. The request body (in JSON format) contains the note content and importance fields. This demonstrates how to include the JWT token in the Authorization header when making authenticated API requests using the Postman API testing tool. The Bearer scheme prefix is clearly visible before the token value.](/static/cda2d24404da6db8b2ff17ee522e5f4e/5a190/20new.png)

and with Visual Studio Code REST client

![VS Code REST client showing a POST request to create a new note with authentication. The request includes the Authorization header with "Bearer" followed by a JWT token string. The request body contains JSON data for creating a new note. This demonstrates how developers can test authenticated API endpoints within VS Code by including the JWT token obtained from the login endpoint in the Authorization header of subsequent requests. The format follows the standard Bearer token authentication scheme.](/static/9bfbed9aace2b65be18a5699c7150a16/5a190/21new.png)

Current application code can be found on [GitHub](https://github.com/fullstack-hy2020/part3-notes-backend/tree/part4-9), branch _part4-9_.

If the application has multiple interfaces requiring identification, JWT's validation should be separated into its own middleware. An existing library like [express-jwt](https://www.npmjs.com/package/express-jwt) could also be used.

## Problems of Token-based authentication

Token authentication is pretty easy to implement, but it contains one problem. Once the API user, eg. a React app gets a token, the API has a blind trust to the token holder. What if the access rights of the token holder should be revoked?

There are two solutions to the problem. The easier one is to limit the validity period of a token:

```js
loginRouter.post('/', async (request, response) => {
  const { username, password } = request.body

  const user = await User.findOne({ username })
  const passwordCorrect = user === null
    ? false
    : await bcrypt.compare(password, user.passwordHash)

  if (!(user && passwordCorrect)) {
    return response.status(401).json({
      error: 'invalid username or password'
    })
  }

  const userForToken = {
    username: user.username,
    id: user._id,
  }

  // token expires in 60*60 seconds, that is, in one hour
  const token = jwt.sign(
    userForToken, 
    process.env.SECRET,
    { expiresIn: 60*60 }
  )
  response
    .status(200)
    .send({ token, username: user.username, name: user.name })
})
```

Once the token expires, the client app needs to get a new token. Usually, this happens by forcing the user to re-login to the app.

The error handling middleware should be extended to give a proper error in the case of an expired token:

```js
const errorHandler = (error, request, response, next) => {
  logger.error(error.message)

  if (error.name === 'CastError') {
    return response.status(400).send({ error: 'malformatted id' })
  } else if (error.name === 'ValidationError') {
    return response.status(400).json({ error: error.message })
  } else if (error.name === 'MongoServerError' && error.message.includes('E11000 duplicate key error')) {
    return response.status(400).json({
      error: 'expected `username` to be unique'
    })
  } else if (error.name === 'JsonWebTokenError') {
    return response.status(401).json({
      error: 'invalid token'
    })
  } else if (error.name === 'TokenExpiredError') {
    return response.status(401).json({
      error: 'token expired'
    })
  }
  next(error)
}
```

The shorter the expiration time, the safer the solution is. If the token falls into the wrong hands or user access to the system needs to be revoked, the token is only usable for a limited amount of time. However, a short expiration time is a potential pain point for the user, as it requires them to log in more frequently.

The other solution is to save info about each token to the backend database and to check for each API request if the access rights corresponding to the tokens are still valid. With this scheme, access rights can be revoked at any time. This kind of solution is often called a _server-side session_.

The negative aspect of server-side sessions is the increased complexity in the backend and also the effect on performance since the token validity needs to be checked for each API request to the database. Database access is considerably slower compared to checking the validity of the token itself. That is why it is quite common to save the session corresponding to a token to a _key-value database_ such as [Redis](https://redis.io/), that is limited in functionality compared to eg. MongoDB or a relational database, but extremely fast in some usage scenarios.

When server-side sessions are used, the token is quite often just a random string, that does not include any information about the user as it is quite often the case when jwt-tokens are used. For each API request, the server fetches the relevant information about the identity of the user from the database. It is also quite usual that instead of using Authorization-header, _cookies_ are used as the mechanism for transferring the token between the client and the server.

## End notes

There have been many changes to the code which have caused a typical problem for a fast-paced software project: most of the tests have broken. Because this part of the course is already jammed with new information, we will leave fixing the tests to a non-compulsory exercise.

Usernames, passwords and applications using token authentication must always be used over [HTTPS](https://en.wikipedia.org/wiki/HTTPS). We could use a Node [HTTPS](https://nodejs.org/docs/latest-v18.x/api/https.html) server in our application instead of the [HTTP](https://nodejs.org/docs/latest-v18.x/api/http.html) server (it requires more configuration). On the other hand, the production version of our application is in Fly.io, so our application stays secure: Fly.io routes all traffic between a browser and the Fly.io server over HTTPS.

We will implement login to the frontend in the [next part](/en/part5).

---

## Exercises 4.15.-4.23.

In the next exercises, the basics of user management will be implemented for the Bloglist application. The safest way is to follow the course material from part 4 chapter [User administration](/en/part4/user_administration) to the chapter [Token authentication](/en/part4/token_authentication). You can of course also use your creativity.

**One more warning:** If you notice you are mixing async/await and *then* calls, it is 99% certain you are doing something wrong. Use either or, never both.

### 4.15: Blog List Expansion, step 3

Implement a way to create new users by doing an HTTP POST request to address _api/users_. Users have a _username, password and name_.

Do not save passwords to the database as clear text, but use the _bcrypt_ library like we did in part 4 chapter [Creating users](/en/part4/user_administration#creating-users).

**NB** Some Windows users have had problems with _bcrypt_. If you run into problems, remove the library with command

```bash
npm uninstall bcrypt 
```

and install [bcryptjs](https://www.npmjs.com/package/bcryptjs) instead.

Implement a way to see the details of all users by doing a suitable HTTP request.

The list of users can, for example, look as follows:

![Browser window showing JSON response from the /api/users endpoint. The response displays an array of user objects, each containing an _id, username, name, and a notes array. Two users are visible in the JSON output: one with username "mluukkai" and name "Matti Luukkainen" with an empty notes array and ID, and another with username "hellas" and name "Arto Hellas" also with an empty notes array. The JSON is formatted with proper indentation for readability in the browser.](/static/b59bda1bd7e5987a5c805332d509e516/5a190/22.png)

### 4.16*: Blog List Expansion, step 4

Add a feature which adds the following restrictions to creating new users: Both username and password must be given and both must be at least 3 characters long. The username must be unique.

The operation must respond with a suitable status code and some kind of an error message if an invalid user is created.

**NB** Do not test password restrictions with Mongoose validations. It is not a good idea because the password received by the backend and the password hash saved to the database are not the same thing. The password length should be validated in the controller as we did in [part 3](/en/part3/validation_and_es_lint) before using Mongoose validation.

Also, **implement tests** that ensure invalid users are not created and that an invalid add user operation returns a suitable status code and error message.

**NB** if you decide to define tests on multiple files, you should note that by default each test file is executed in its own process (see *Test execution model* in the [documentation](https://nodejs.org/api/test.html#test-runner-execution-model)). The consequence of this is that different test files are executed at the same time. Since the tests share the same database, simultaneous execution may cause problems, which can be avoided by executing the tests with the option *--test-concurrency=1*, i.e. defining them to be executed sequentially.

### 4.17: Blog List Expansion, step 5

Expand blogs so that each blog contains information on the creator of the blog.

Modify adding new blogs so that when a new blog is created, _any_ user from the database is designated as its creator (for example the one found first). Implement this according to part 4 chapter [populate](/en/part4/user_administration#populate).
Which user is designated as the creator does not matter just yet. The functionality is finished in exercise 4.19.

Modify listing all blogs so that the creator's user information is displayed with the blog:

![Browser window showing JSON response from the /api/blogs endpoint. The response displays an array of blog objects, each containing _id, title, author, url, likes, and a user object. The user object is populated with the creator's details including _id, username, and name. Two blog entries are visible: one titled "React patterns" by Michael Chan with the user info showing username "mluukkai" and name "Matti Luukkainen", and another titled "Go To Statement Considered Harmful" by Edsger W. Dijkstra with the same user information.](/static/199682ad74f50747c90997a967856ffa/5a190/23e.png)

and listing all users also displays the blogs created by each user:

![Browser window showing JSON response from the /api/users endpoint. The response displays an array of user objects, each containing _id, username, name, and a notes array that contains populated blog objects. One user is visible with username "mluukkai" and name "Matti Luukkainen", whose notes array contains multiple blog entries. Each blog entry in the notes array includes _id, title, author, url, and likes fields, showing the blogs that this user has created.](/static/ac9967c89785b33440e9b1b4e87c17e5/5a190/24e.png)

### 4.18: Blog List Expansion, step 6

Implement token-based authentication according to part 4 chapter [Token authentication](/en/part4/token_authentication).

### 4.19: Blog List Expansion, step 7

Modify adding new blogs so that it is only possible if a valid token is sent with the HTTP POST request. The user identified by the token is designated as the creator of the blog.

### 4.20*: Blog List Expansion, step 8

[This example](/en/part4/token_authentication#limiting-creating-new-notes-to-logged-in-users) from part 4 shows taking the token from the header with the *getTokenFrom* helper function in _controllers/blogs.js_.

If you used the same solution, refactor taking the token to a [middleware](/en/part3/node_js_and_express#middleware). The middleware should take the token from the _Authorization_ header and assign it to the _token_ field of the _request_ object.

In other words, if you register this middleware in the _app.js_ file before all routes

```js
app.use(middleware.tokenExtractor)
```

Routes can access the token with *request.token*:

```js
blogsRouter.post('/', async (request, response) => {
  // ..
  const decodedToken = jwt.verify(request.token, process.env.SECRET)
  // ..
})
```

Remember that a normal [middleware function](/en/part3/node_js_and_express#middleware) is a function with three parameters, that at the end calls the last parameter _next_ to move the control to the next middleware:

```js
const tokenExtractor = (request, response, next) => {
  // code that extracts the token

  next()
}
```

### 4.21*: Blog List Expansion, step 9

Change the delete blog operation so that a blog can be deleted only by the user who added it. Therefore, deleting a blog is possible only if the token sent with the request is the same as that of the blog's creator.

If deleting a blog is attempted without a token or by an invalid user, the operation should return a suitable status code.

Note that if you fetch a blog from the database,

```js
const blog = await Blog.findById(...)
```

the field _blog.user_ does not contain a string, but an object. So if you want to compare the ID of the object fetched from the database and a string ID, a normal comparison operation does not work. The ID fetched from the database must be parsed into a string first.

```js
if ( blog.user.toString() === userid.toString() ) ...
```

### 4.22*: Blog List Expansion, step 10

Both the new blog creation and blog deletion need to find out the identity of the user who is doing the operation. The middleware *tokenExtractor* that we did in exercise 4.20 helps but still both the handlers of _post_ and _delete_ operations need to find out who the user holding a specific token is.

Now create a new middleware called userExtractor that identifies the user related to the request and attaches it to the request object. After registering the middleware, the post and delete handlers should be able to access the user directly by referencing request.user:

```js
blogsRouter.post('/', userExtractor, async (request, response) => {
  // get user from request object
  const user = request.user
  // ..
})

blogsRouter.delete('/:id', userExtractor, async (request, response) => {
  // get user from request object
  const user = request.user
  // ..
})
```

Note that in this case, the userExtractor middleware has been registered with individual routes, so it is only executed in certain cases. So instead of using *userExtractor* with all the routes,

```js
// use the middleware in all routes
app.use(middleware.userExtractor)
app.use('/api/blogs', blogsRouter)  
app.use('/api/users', usersRouter)
app.use('/api/login', loginRouter)
```

we could register it to be only executed with path _/api/blogs_ routes:

```js
// use the middleware only in /api/blogs routes
app.use('/api/blogs', middleware.userExtractor, blogsRouter)
app.use('/api/users', usersRouter)
app.use('/api/login', loginRouter)
```

This is done by chaining multiple middleware functions as parameters to the _use_ function. In the same way, middleware can also be registered only for individual routes:

```js
router.post('/', userExtractor, async (request, response) => {
  // ...
})
```

Make sure that fetching all blogs with a GET request still works without a token.

### 4.23*: Blog List Expansion, step 11

After adding token-based authentication the tests for adding a new blog broke down. Fix them. Also, write a new test to ensure adding a blog fails with the proper status code _401 Unauthorized_ if a token is not provided.

[This](https://github.com/visionmedia/supertest/issues/398) is most likely useful when doing the fix.

This is the last exercise for this part of the course and it's time to push your code to GitHub and mark all of your finished exercises to the [exercise submission system](https://studies.cs.helsinki.fi/stats/courses/fullstackopen).
