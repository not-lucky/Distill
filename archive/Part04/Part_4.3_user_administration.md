# c User administration

We want to add user authentication and authorization to our application. Users should be stored in the database and every note should be linked to the user who created it. Deleting and editing a note should only be allowed for the user who created it.

Let's start by adding information about users to the database. There is a one-to-many relationship between the user (*User*) and notes (*Note*):

![Diagram showing a one-to-many relationship between User and Note entities. The User entity (rectangle) has a connection line with a "1" multiplicity indicator on the User side and a "*" (many) indicator on the Note side, representing that one user can have many associated notes.](https://yuml.me/a187045b.png)

If we were working with a relational database the implementation would be straightforward. Both resources would have their separate database tables, and the id of the user who created a note would be stored in the notes table as a foreign key.

When working with document databases the situation is a bit different, as there are many different ways of modeling the situation.

The existing solution saves every note in the *notes collection* in the database. If we do not want to change this existing collection, then the natural choice is to save users in their own collection,  *users* for example.

Like with all document databases, we can use object IDs in Mongo to reference documents in other collections. This is similar to using foreign keys in relational databases.

Traditionally document databases like Mongo do not support *join queries* that are available in relational databases,  used for aggregating data from multiple tables. However, starting from version 3.2. Mongo has supported [lookup aggregation queries](https://docs.mongodb.com/manual/reference/operator/aggregation/lookup/). We will not be taking a look at this functionality in this course.

If we need functionality similar to join queries, we will implement it in our application code by making multiple queries. In certain situations, Mongoose can take care of joining and aggregating data, which gives the appearance of a join query. However, even in these situations, Mongoose makes multiple queries to the database in the background.

### References across collections

If we were using a relational database the note would contain a *reference key* to the user who created it. In document databases, we can do the same thing.

Let's assume that the *users* collection contains two users:

```js
[
  {
    username: 'mluukkai',
    _id: 123456,
  },
  {
    username: 'hellas',
    _id: 141414,
  },
]
```

The *notes* collection contains three notes that all have a *user* field that references a user in the *users* collection:

```js
[
  {
    content: 'HTML is easy',
    important: false,
    _id: 221212,
    user: 123456,
  },
  {
    content: 'The most important operations of HTTP protocol are GET and POST',
    important: true,
    _id: 221255,
    user: 123456,
  },
  {
    content: 'A proper dinosaur codes with Java',
    important: false,
    _id: 221244,
    user: 141414,
  },
]
```

Document databases do not demand the foreign key to be stored in the note resources, it could *also* be stored in the users collection, or even both:

```js
[
  {
    username: 'mluukkai',
    _id: 123456,
    notes: [221212, 221255],
  },
  {
    username: 'hellas',
    _id: 141414,
    notes: [221244],
  },
]
```

Since users can have many notes, the related ids are stored in an array in the *notes* field.

Document databases also offer a radically different way of organizing the data: In some situations, it might be beneficial to nest the entire notes array as a part of the documents in the users collection:

```js
[
  {
    username: 'mluukkai',
    _id: 123456,
    notes: [
      {
        content: 'HTML is easy',
        important: false,
      },
      {
        content: 'The most important operations of HTTP protocol are GET and POST',
        important: true,
      },
    ],
  },
  {
    username: 'hellas',
    _id: 141414,
    notes: [
      {
        content:
          'A proper dinosaur codes with Java',
        important: false,
      },
    ],
  },
]
```

In this schema, notes would be tightly nested under users and the database would not generate ids for them.

The structure and schema of the database are not as self-evident as it was with relational databases. The chosen schema must support the use cases of the application the best. This is not a simple design decision to make, as all use cases of the applications are not known when the design decision is made.

Paradoxically, schema-less databases like Mongo require developers to make far more radical design decisions about data organization at the beginning of the project than relational databases with schemas. On average, relational databases offer a more or less suitable way of organizing data for many applications.

### Mongoose schema for users

In this case, we decide to store the ids of the notes created by the user in the user document. Let's define the model for representing a user in the *models/user.js* file:

```js
const mongoose = require('mongoose')

const userSchema = new mongoose.Schema({
  username: String,
  name: String,
  passwordHash: String,
  notes: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Note'
    }
  ],
})

userSchema.set('toJSON', {
  transform: (document, returnedObject) => {
    returnedObject.id = returnedObject._id.toString()
    delete returnedObject._id
    delete returnedObject.__v
    // the passwordHash should not be revealed
    delete returnedObject.passwordHash
  }
})

const User = mongoose.model('User', userSchema)

module.exports = User
```

The ids of the notes are stored within the user document as an array of Mongo ids. The definition is as follows:

```js
{
  type: mongoose.Schema.Types.ObjectId,
  ref: 'Note'
}
```

The field type is *ObjectId*, meaning it refers to another document. The *ref* field specifies the name of the model being referenced. Mongo does not inherently know that this is a field that references notes, the syntax is purely related to and defined by Mongoose.

Let's expand the schema of the note defined in the *models/note.js* file so that the note contains information about the user who created it:

```js
const noteSchema = new mongoose.Schema({
  content: {
    type: String,
    required: true,
    minlength: 5
  },
  important: Boolean,
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  }
})
```

In stark contrast to the conventions of relational databases, *references are now stored in both documents*: the note references the user who created it, and the user has an array of references to all of the notes created by them.

### Creating users

Let's implement a route for creating new users. Users have a unique *username*, a *name* and something called a *passwordHash*. The password hash is the output of a [one-way hash function](https://en.wikipedia.org/wiki/Cryptographic_hash_function) applied to the user's password. It is never wise to store unencrypted plain text passwords in the database!

Let's install the [bcrypt](https://github.com/kelektiv/node.bcrypt.js) package for generating the password hashes:

```bash
npm install bcrypt
```

Creating new users happens in compliance with the RESTful conventions discussed in [part 3](/en/part3/node_js_and_express#rest), by making an HTTP POST request to the *users* path.

Let's define a separate *router* for dealing with users in a new *controllers/users.js* file. Let's take the router into use in our application in the *app.js* file, so that it handles requests made to the */api/users* url:

```js
// ...
const notesRouter = require('./controllers/notes')
const usersRouter = require('./controllers/users')
// ...

app.use('/api/notes', notesRouter)
app.use('/api/users', usersRouter)
// ...
```

The contents of the file, *controllers/users.js*, that defines the router is as follows:

```js
const bcrypt = require('bcrypt')
const usersRouter = require('express').Router()
const User = require('../models/user')

usersRouter.post('/', async (request, response) => {
  const { username, name, password } = request.body

  const saltRounds = 10
  const passwordHash = await bcrypt.hash(password, saltRounds)

  const user = new User({
    username,
    name,
    passwordHash,
  })

  const savedUser = await user.save()

  response.status(201).json(savedUser)
})

module.exports = usersRouter
```

The password sent in the request is *not* stored in the database. We store the *hash* of the password that is generated with the *bcrypt.hash* function.

The fundamentals of [storing passwords](https://bytebytego.com/guides/how-to-store-passwords-in-the-database/) are outside the scope of this course material. We will not discuss what the magic number 10 assigned to the [saltRounds](https://github.com/kelektiv/node.bcrypt.js/#a-note-on-rounds) variable means, but you can read more about it in the linked material.

Our current code does not contain any error handling or input validation for verifying that the username and password are in the desired format.

The new feature can and should initially be tested manually with a tool like Postman. However testing things manually will quickly become too cumbersome, especially once we implement functionality that enforces usernames to be unique.

It takes much less effort to write automated tests, and it will make the development of our application much easier.

Our initial tests could look like this:

```js
const bcrypt = require('bcrypt')
const User = require('../models/user')

//...

describe('when there is initially one user in db', () => {
  beforeEach(async () => {
    await User.deleteMany({})

    const passwordHash = await bcrypt.hash('sekret', 10)
    const user = new User({ username: 'root', passwordHash })

    await user.save()
  })

  test('creation succeeds with a fresh username', async () => {
    const usersAtStart = await helper.usersInDb()

    const newUser = {
      username: 'mluukkai',
      name: 'Matti Luukkainen',
      password: 'salainen',
    }

    await api
      .post('/api/users')
      .send(newUser)
      .expect(201)
      .expect('Content-Type', /application\/json/)

    const usersAtEnd = await helper.usersInDb()
    assert.strictEqual(usersAtEnd.length, usersAtStart.length + 1)

    const usernames = usersAtEnd.map(u => u.username)
    assert(usernames.includes(newUser.username))
  })
})
```

The tests use the *usersInDb()* helper function that we implemented in the *tests/test_helper.js* file. The function is used to help us verify the state of the database after a user is created:

```js
const User = require('../models/user')

// ...

const usersInDb = async () => {
  const users = await User.find({})
  return users.map(u => u.toJSON())
}

module.exports = {
  initialNotes,
  nonExistingId,
  notesInDb,
  usersInDb,
}
```

The *beforeEach* block adds a user with the username *root* to the database. We can write a new test that verifies that a new user with the same username can not be created:

```js
describe('when there is initially one user in db', () => {
  // ...

  test('creation fails with proper statuscode and message if username already taken', async () => {
    const usersAtStart = await helper.usersInDb()

    const newUser = {
      username: 'root',
      name: 'Superuser',
      password: 'salainen',
    }

    const result = await api
      .post('/api/users')
      .send(newUser)
      .expect(400)
      .expect('Content-Type', /application\/json/)

    const usersAtEnd = await helper.usersInDb()
    assert(result.body.error.includes('expected `username` to be unique'))

    assert.strictEqual(usersAtEnd.length, usersAtStart.length)
  })
})
```

The test case obviously will not pass at this point. We are essentially practicing [test-driven development (TDD)](https://en.wikipedia.org/wiki/Test-driven_development), where tests for new functionality are written before the functionality is implemented.

Mongoose validations do not provide a direct way to check the uniqueness of a field value. However, it is possible to achieve uniqueness by defining [uniqueness index](https://mongoosejs.com/docs/schematypes.html) for a field. The definition is done as follows:

```js
const mongoose = require('mongoose')

const userSchema = mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true // this ensures the uniqueness of username
  },
  name: String,
  passwordHash: String,
  notes: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Note'
    }
  ],
})

// ...
```

However, we want to be careful when using the uniqueness index. If there are already documents in the database that violate the uniqueness condition, [no index will be created](https://dev.to/akshatsinghania/mongoose-unique-not-working-16bf). So when adding a uniqueness index, make sure that the database is in a healthy state! The test above added the user with username *root* to the database twice, and these must be removed for the index to be formed and the code to work.

Mongoose validations do not detect the index violation, and instead of *ValidationError* they return an error of type *MongoServerError*. We therefore need to extend the error handler for that case:

```js
const errorHandler = (error, request, response, next) => {
  if (error.name === 'CastError') {
    return response.status(400).send({ error: 'malformatted id' })
  } else if (error.name === 'ValidationError') {
    return response.status(400).json({ error: error.message })
  } else if (error.name === 'MongoServerError' && error.message.includes('E11000 duplicate key error')) {
    return response.status(400).json({ error: 'expected `username` to be unique' })
  }
  next(error)
}
```

After these changes, the tests will pass.

We could also implement other validations into the user creation. We could check that the username is long enough, that the username only consists of permitted characters, or that the password is strong enough. Implementing these functionalities is left as an optional exercise.

Before we move onward, let's add an initial implementation of a route handler that returns all of the users in the database:

```js
usersRouter.get('/', async (request, response) => {
  const users = await User.find({})
  response.json(users)
})
```

For making new users in a production or development environment, you may send a POST request to `/api/users/` via Postman or REST Client in the following format:

```js
{
    "username": "root",
    "name": "Superuser",
    "password": "salainen"
}
```

The list looks like this:

![Screenshot of a web browser displaying JSON data at the api/users endpoint. The response shows an array containing a single user object with fields: username "root", name "Superuser", id "6543d637d6727f45c8f9a6e1", and an empty notes array []. The browser has a dark theme and the JSON is formatted with syntax highlighting.](/static/485f61a7db35371fea0db42b2bcc1cda/5a190/9.png)

You can find the code for our current application in its entirety in the *part4-7* branch of [this GitHub repository](https://github.com/fullstack-hy2020/part3-notes-backend/tree/part4-7).

### Creating a new note

The code for creating a new note has to be updated so that the note is assigned to the user who created it.

Let's expand our current implementation in *controllers/notes.js* so that the information about the user who created a note is sent in the *userId* field of the request body:

```js
const notesRouter = require('express').Router()
const Note = require('../models/note')
const User = require('../models/user')
//...

notesRouter.post('/', async (request, response) => {
  const body = request.body

  const user = await User.findById(body.userId)
  if (!user) {
    return response.status(400).json({ error: 'userId missing or not valid' })
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

// ...
```

The database is first queried for a user using the *userId* provided in the request. If the user is not found, the response is sent with a status code of 400 (*Bad Request*) and an error message: *"userId missing or not valid"*.

It's worth noting that the *user* object also changes. The *id* of the note is stored in the *notes* field of the *user* object:

```js
const user = await User.findById(body.userId)

// ...

user.notes = user.notes.concat(savedNote._id)
await user.save()
```

Let's try to create a new note

![Screenshot of Postman application showing a POST request to create a new note. The request is sent to localhost:3001/api/notes with JSON body containing content "nice note", important set to true, and userId field. The response shows 201 Created status with the saved note object including its generated id and user reference.](/static/a562436685978cc842c89a5d157a2938/5a190/10e.png)

The operation appears to work. Let's add one more note and then visit the route for fetching all users:

![Screenshot of browser showing JSON response from api/users endpoint. The response displays a user object with username "root", name "Superuser", an id, and a notes array containing two note objects - each with their own content, important flag, and id fields populated.](/static/c60c79686add78ebf57de1711c47fb47/5a190/11e.png)

We can see that the user has two notes.

Likewise, the ids of the users who created the notes can be seen when we visit the route for fetching all notes:

![Screenshot of browser showing JSON response from api/notes endpoint. The response displays an array of note objects, each containing content, important boolean flag, id, and a user field containing the ObjectId reference to the user who created the note.](/static/6798064b6620269dd272d7ee515aa4a9/5a190/12e.png)

Due to the changes we made, the tests no longer pass, but we leave fixing the tests as an optional exercise. The changes we made have also not been accounted for in the frontend, so the note creation functionality no longer works. We will fix the frontend in part 5 of the course.

### Populate

We would like our API to work in such a way, that when an HTTP GET request is made to the */api/users* route, the user objects would also contain the contents of the user's notes and not just their id. In a relational database, this functionality would be implemented with a *join query*.

As previously mentioned, document databases do not properly support join queries between collections, but the Mongoose library can do some of these joins for us. Mongoose accomplishes the join by doing multiple queries, which is different from join queries in relational databases which are *transactional*, meaning that the state of the database does not change during the time that the query is made. With join queries in Mongoose, nothing can guarantee that the state between the collections being joined is consistent, meaning that if we make a query that joins the user and notes collections, the state of the collections may change during the query.

The Mongoose join is done with the [populate](http://mongoosejs.com/docs/populate.html) method. Let's update the route that returns all users first in *controllers/users.js* file:

```js
usersRouter.get('/', async (request, response) => {
  const users = await User
    .find({}).populate('notes')
  response.json(users)
})
```

The [populate](http://mongoosejs.com/docs/populate.html) method is chained after the *find* method making the initial query. The argument given to the populate method defines that the *ids* referencing *note* objects in the *notes* field of the *user* document will be replaced by the referenced *note* documents. Mongoose first queries the *users* collection for the list of users, and then queries the collection corresponding to the model object specified by the *ref* property in the users schema for data with the given object id.

The result is almost exactly what we wanted:

![Screenshot of browser showing JSON response with populated user data. The response shows a user object with username "root", name "Superuser", an id, and a notes array. Each note in the array is fully populated with its own _id, content, important flag, and user id fields - showing the complete note objects instead of just references.](/static/ca7c3b6c859225179712112462a7c2b7/5a190/13new.png)

We can use the populate method for choosing the fields we want to include from the documents. In addition to the field *id* we are now only interested in *content* and *important*.

The selection of fields is done with the Mongo [syntax](https://www.mongodb.com/docs/manual/tutorial/project-fields-from-query-results/#return-the-specified-fields-and-the-_id-field-only):

```js
usersRouter.get('/', async (request, response) => {
  const users = await User
    .find({}).populate('notes', { content: 1, important: 1 })

  response.json(users)
})
```

The result is now exactly like we want it to be:

![Screenshot of browser showing clean JSON response from api/users endpoint. The response displays a user object with username "root", name "Superuser", id, and a notes array. Each note in the array contains only the selected fields: _id, content, and important - demonstrating the field selection in the populate method.](/static/e526a27a1953221b1f00ef911436eb8b/5a190/14new.png)

Let's also add a suitable population of user information to notes in the *controllers/notes.js* file:

```js
notesRouter.get('/', async (request, response) => {
  const notes = await Note
    .find({}).populate('user', { username: 1, name: 1 })

  response.json(notes)
})
```

Now the user's information is added to the *user* field of note objects.

![Screenshot of browser showing JSON response from api/notes endpoint. The response displays an array of note objects, each containing content, important flag, id, and a populated user object with username and name fields instead of just an ObjectId reference.](/static/6f9441d387d1a6e6e90ec2c42aa88813/5a190/15new.png)

It's important to understand that the database does not know that the ids stored in the *user* field of the notes collection reference documents in the user collection.

The functionality of the *populate* method of Mongoose is based on the fact that we have defined "types" to the references in the Mongoose schema with the *ref* option:

```js
const noteSchema = new mongoose.Schema({
  content: {
    type: String,
    required: true,
    minlength: 5
  },
  important: Boolean,
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  }
})
```

You can find the code for our current application in its entirety in the *part4-8* branch of [this GitHub repository](https://github.com/fullstack-hy2020/part3-notes-backend/tree/part4-8).
